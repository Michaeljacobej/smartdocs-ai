import logging
import re
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.api.errors import NotFoundError, ServiceUnavailableError, UnsupportedFileError
from app.core.config import get_settings
from app.db.models import Document, ExtractedData, OCRResult, ProcessingStatus
from app.db.repositories.document_repository import DocumentRepository
from app.schemas.extraction import CorrectionInput
from app.services.classification_service import ClassificationService
from app.services.extraction_service import ExtractionError, ExtractionService
from app.services.llm.ollama import OllamaProvider
from app.services.ocr_service import OCRService
from app.services.validation_service import ValidationService
from app.utils.file_validation import FileValidationError, validate_upload_file

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self) -> None:
        settings = get_settings()
        settings.upload_path.mkdir(parents=True, exist_ok=True)
        llm_provider = OllamaProvider()
        self.repo_class = DocumentRepository
        self.ocr_service = OCRService()
        self.classification_service = ClassificationService(llm_provider=llm_provider)
        self.extraction_service = ExtractionService(llm_provider=llm_provider)
        self.validation_service = ValidationService()

    def create_document(self, db: Session, file: UploadFile, file_bytes: bytes) -> Document:
        settings = get_settings()
        try:
            validate_upload_file(file, len(file_bytes), settings)
        except FileValidationError as exc:
            raise UnsupportedFileError(str(exc)) from exc

        extension = Path(file.filename or "").suffix.lower()
        safe_name = f"{uuid.uuid4().hex}{extension}"
        target_path = (settings.upload_path / safe_name).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with target_path.open("wb") as out:
            shutil.copyfileobj(self._to_stream(file_bytes), out)

        document = Document(
            file_name=file.filename or "uploaded-file",
            file_path=str(target_path),
            mime_type=file.content_type or "application/octet-stream",
            file_size=len(file_bytes),
            processing_status=ProcessingStatus.UPLOADED,
        )

        repo = self.repo_class(db)
        created = repo.create(document)
        created.processing_status = ProcessingStatus.PROCESSING
        db.add(created)
        db.commit()
        db.refresh(created)
        logger.info(
            "Document created",
            extra={
                "event": "document_created",
                "document_id": str(created.id),
                "file_name": created.file_name,
                "file_size": created.file_size,
                "mime_type": created.mime_type,
            },
        )
        return created

    def process_document(self, db: Session, document_id: UUID) -> None:
        repo = self.repo_class(db)
        document = repo.get(document_id)
        if not document:
            logger.warning(
                "Document not found during processing",
                extra={"event": "document_not_found_for_processing", "document_id": str(document_id)},
            )
            return

        document.processing_status = ProcessingStatus.PROCESSING
        db.add(document)
        db.commit()
        document_id_str = str(document.id)

        try:
            ocr = self.ocr_service.extract_text(Path(document.file_path))
            ocr_result = document.ocr_result
            if ocr_result is None:
                ocr_result = OCRResult(document=document)
            ocr_result.raw_text = ocr.raw_text
            ocr_result.processing_status = ProcessingStatus.COMPLETED
            ocr_result.processing_time_ms = ocr.processing_time_ms
            ocr_result.error_message = None
            db.add(ocr_result)

            doc_type = self.classification_service.classify(ocr.raw_text)
            document.document_type = doc_type

            extracted, confidence_payload = self.extraction_service.extract(ocr.raw_text, doc_type)
            validation = self.validation_service.validate(extracted)
            confidence_payload["anomalies"] = [item.model_dump() for item in validation.anomalies]
            confidence_payload["ocr_lines"] = [
                {"text": line.text, "confidence": line.confidence} for line in ocr.lines
            ]
            field_confidences = self._build_field_confidences(extracted, ocr.lines)
            confidence_payload["field_confidences"] = field_confidences
            confidence_payload["evaluation"] = self._evaluate_confidence(
                extracted=extracted,
                field_confidences=field_confidences,
                anomaly_count=len(validation.anomalies),
                accept_threshold=get_settings().confidence_accept_threshold,
            )

            extracted_data = document.extracted_data or ExtractedData(document_id=document.id)
            extracted_data.document_number_original = extracted.document_number
            extracted_data.vendor_original = extracted.vendor
            extracted_data.document_date_original = extracted.document_date
            extracted_data.total_amount_original = extracted.total_amount
            extracted_data.tax_amount_original = extracted.tax_amount
            extracted_data.currency_original = extracted.currency
            extracted_data.confidence_data = confidence_payload
            db.add(extracted_data)

            decision = confidence_payload["evaluation"]["decision"]
            if decision == "REVIEW":
                document.processing_status = ProcessingStatus.REVIEW_REQUIRED
            else:
                document.processing_status = ProcessingStatus.COMPLETED
            db.add(document)
            db.commit()
            logger.info(
                "Document processed",
                extra={
                    "event": "document_processed",
                    "document_id": str(document.id),
                    "document_type": document.document_type,
                    "ocr_processing_time_ms": ocr.processing_time_ms,
                },
            )
        except RuntimeError as exc:
            db.rollback()
            logger.exception(
                "Document processing dependency failure",
                extra={"event": "document_processing_dependency_failure", "document_id": document_id_str},
            )
            self._mark_failed(db, document, str(exc))
            raise ServiceUnavailableError("OCR or LLM service unavailable") from exc
        except ExtractionError as exc:
            db.rollback()
            logger.warning(
                "Document extraction failed",
                extra={"event": "document_extraction_failed", "document_id": document_id_str, "reason": str(exc)},
            )
            self._mark_failed(db, document, str(exc))
        except Exception:
            db.rollback()
            logger.exception("Document processing failed", extra={"event": "document_processing_failed", "document_id": document_id_str})
            self._mark_failed(db, document, "Unexpected processing error")

    def list_documents(self, db: Session) -> list[Document]:
        repo = self.repo_class(db)
        return repo.list()

    def get_document(self, db: Session, document_id: UUID) -> Document:
        repo = self.repo_class(db)
        document = repo.get(document_id)
        if not document:
            raise NotFoundError()
        return document

    def delete_document(self, db: Session, document_id: UUID) -> None:
        document = self.get_document(db, document_id)
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()

        repo = self.repo_class(db)
        repo.delete(document)
        db.commit()
        logger.info("Document deleted", extra={"event": "document_deleted", "document_id": str(document_id)})

    def update_extracted_data(self, db: Session, document_id: UUID, payload: CorrectionInput) -> Document:
        document = self.get_document(db, document_id)
        if not document.extracted_data:
            document.extracted_data = ExtractedData(document_id=document.id)

        extracted = document.extracted_data
        extracted.document_number_corrected = payload.document_number
        extracted.vendor_corrected = payload.vendor
        extracted.document_date_corrected = payload.document_date
        extracted.total_amount_corrected = payload.total_amount
        extracted.tax_amount_corrected = payload.tax_amount
        extracted.currency_corrected = payload.currency

        document.processing_status = ProcessingStatus.REVIEWED
        db.add(extracted)
        db.add(document)
        db.commit()
        db.refresh(document)
        logger.info("Extracted data corrected", extra={"event": "document_corrected", "document_id": str(document_id)})
        return document

    def _mark_failed(self, db: Session, document: Document, message: str) -> None:
        ocr_result = document.ocr_result
        if ocr_result is None:
            ocr_result = (
                db.query(OCRResult)
                .filter(OCRResult.document_id == document.id)
                .order_by(OCRResult.created_at.desc())
                .first()
            )
        if ocr_result is None:
            ocr_result = OCRResult(document=document)
        ocr_result.processing_status = ProcessingStatus.FAILED
        ocr_result.error_message = message[:500]
        db.add(ocr_result)

        document.processing_status = ProcessingStatus.FAILED
        db.add(document)
        db.commit()
        logger.error(
            "Document marked as failed",
            extra={"event": "document_marked_failed", "document_id": str(document.id), "reason": message[:200]},
        )

    @staticmethod
    def _to_stream(file_bytes: bytes) -> BinaryIO:
        from io import BytesIO

        return BytesIO(file_bytes)

    @staticmethod
    def _normalize_for_match(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    @staticmethod
    def _format_amount(value: float) -> str:
        number = f"{value:.2f}".rstrip("0").rstrip(".")
        return number.replace(".", "") if "." not in number else number

    def _build_field_confidences(self, extracted, ocr_lines) -> dict[str, float]:
        line_payload = [(line.text, float(line.confidence) if line.confidence is not None else None) for line in ocr_lines]
        return {
            "document_number": self._score_text_field(extracted.document_number, line_payload, hints=("invoice", "inv", "bill", "no", "number")),
            "vendor": self._score_text_field(extracted.vendor, line_payload, hints=("vendor", "supplier", "merchant", "pt", "cv", "ltd", "inc")),
            "document_date": self._score_date_field(extracted.document_date, line_payload),
            "total_amount": self._score_amount_field(extracted.total_amount, line_payload, hints=("total", "amount", "grand total", "subtotal")),
            "tax_amount": self._score_amount_field(extracted.tax_amount, line_payload, hints=("tax", "ppn", "vat")),
            "currency": self._score_text_field(extracted.currency, line_payload, hints=("idr", "usd", "eur", "sgd", "jpy", "myr", "thb", "php", "rp")),
        }

    @staticmethod
    def _evaluate_confidence(
        *,
        extracted,
        field_confidences: dict[str, float],
        anomaly_count: int,
        accept_threshold: float,
    ) -> dict:
        critical_fields = (
            "document_number",
            "vendor",
            "document_date",
            "total_amount",
            "currency",
        )

        missing_critical_fields = []
        for field_name in critical_fields:
            value = getattr(extracted, field_name, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_critical_fields.append(field_name)

        scored_values = [
            max(0.0, min(1.0, float(value)))
            for value in field_confidences.values()
            if isinstance(value, (float, int))
        ]
        base_score = sum(scored_values) / len(scored_values) if scored_values else 0.0

        anomaly_penalty = min(anomaly_count * 0.08, 0.30)
        missing_penalty = min(len(missing_critical_fields) * 0.10, 0.40)
        overall_score = max(0.0, min(1.0, base_score - anomaly_penalty - missing_penalty))

        review_reasons = []
        if anomaly_count:
            review_reasons.append("validation_anomalies")
        if missing_critical_fields:
            review_reasons.append("missing_critical_fields")
        if overall_score < accept_threshold:
            review_reasons.append("overall_confidence_below_threshold")

        decision = "REVIEW" if review_reasons else "ACCEPT"

        return {
            "decision": decision,
            "overall_score": round(overall_score, 2),
            "threshold": accept_threshold,
            "anomaly_count": anomaly_count,
            "missing_critical_fields": missing_critical_fields,
            "reasons": review_reasons,
        }

    def _score_text_field(
        self,
        value: str | None,
        ocr_lines: list[tuple[str, float | None]],
        *,
        hints: tuple[str, ...] = (),
    ) -> float:
        if not value:
            return 0.0

        target = self._normalize_for_match(value)
        if not target:
            return 0.0

        best = 0.65
        for text, confidence in ocr_lines:
            normalized = self._normalize_for_match(text)
            if target in normalized:
                score = confidence if confidence is not None else 0.75
                if any(hint in normalized for hint in hints):
                    score += 0.05
                best = max(best, min(score, 1.0))

        return round(best, 2)

    def _score_amount_field(
        self,
        value: float | None,
        ocr_lines: list[tuple[str, float | None]],
        *,
        hints: tuple[str, ...] = (),
    ) -> float:
        if value is None:
            return 0.0

        target = self._normalize_for_match(self._format_amount(value))
        best = 0.6
        for text, confidence in ocr_lines:
            normalized = self._normalize_for_match(text)
            if target and target in normalized:
                score = confidence if confidence is not None else 0.78
                if any(hint in normalized for hint in hints):
                    score += 0.06
                best = max(best, min(score, 1.0))

        return round(best, 2)

    def _score_date_field(self, value: str | None, ocr_lines: list[tuple[str, float | None]]) -> float:
        if not value:
            return 0.0

        normalized_target = self._normalize_for_match(value)
        best = 0.6
        for text, confidence in ocr_lines:
            normalized = self._normalize_for_match(text)
            if normalized_target in normalized:
                score = confidence if confidence is not None else 0.75
                best = max(best, min(score + 0.03, 1.0))
            elif any(token in normalized for token in ("date", "tgl", "tanggal")) and any(ch.isdigit() for ch in normalized):
                best = max(best, (confidence if confidence is not None else 0.7))

        return round(best, 2)


document_service = DocumentService()
