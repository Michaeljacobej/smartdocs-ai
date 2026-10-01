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
        return created

    def process_document(self, db: Session, document_id: UUID) -> None:
        repo = self.repo_class(db)
        document = repo.get(document_id)
        if not document:
            return

        document.processing_status = ProcessingStatus.PROCESSING
        db.add(document)
        db.commit()

        try:
            ocr = self.ocr_service.extract_text(Path(document.file_path))
            ocr_result = document.ocr_result or OCRResult(document_id=document.id)
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
            confidence_payload["field_confidences"] = self._build_field_confidences(extracted, ocr.lines)

            extracted_data = document.extracted_data or ExtractedData(document_id=document.id)
            extracted_data.document_number_original = extracted.document_number
            extracted_data.vendor_original = extracted.vendor
            extracted_data.document_date_original = extracted.document_date
            extracted_data.total_amount_original = extracted.total_amount
            extracted_data.tax_amount_original = extracted.tax_amount
            extracted_data.currency_original = extracted.currency
            extracted_data.confidence_data = confidence_payload
            db.add(extracted_data)

            document.processing_status = ProcessingStatus.COMPLETED
            db.add(document)
            db.commit()
        except RuntimeError as exc:
            self._mark_failed(db, document, str(exc))
            raise ServiceUnavailableError("OCR or LLM service unavailable") from exc
        except ExtractionError as exc:
            self._mark_failed(db, document, str(exc))
        except Exception:
            logger.exception("Document processing failed")
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
        return document

    def _mark_failed(self, db: Session, document: Document, message: str) -> None:
        ocr_result = document.ocr_result or OCRResult(document_id=document.id)
        ocr_result.processing_status = ProcessingStatus.FAILED
        ocr_result.error_message = message[:500]
        db.add(ocr_result)

        document.processing_status = ProcessingStatus.FAILED
        db.add(document)
        db.commit()

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
