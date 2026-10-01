import queue
import threading
import logging
from uuid import UUID

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings

from app.api.errors import NotFoundError, ServiceUnavailableError, SummaryNotReadyError
from app.db.database import SessionLocal, get_db
from app.schemas.document import DocumentListResponse, DocumentOut
from app.schemas.extraction import CorrectionInput
from app.schemas.summary import GenerateSummaryResponse, SummaryResponse
from app.services.service_registry import document_service, summary_service

router = APIRouter(prefix="/documents", tags=["documents"])
PROCESSING_QUEUE: queue.Queue[UUID] = queue.Queue()
_PROCESSING_WORKERS = 2
logger = logging.getLogger(__name__)


def _process_queue_worker() -> None:
    while True:
        document_id = PROCESSING_QUEUE.get()
        try:
            _process_document_sync(document_id)
        finally:
            PROCESSING_QUEUE.task_done()


for _ in range(_PROCESSING_WORKERS):
    worker = threading.Thread(target=_process_queue_worker, daemon=True)
    worker.start()


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentOut:
    logger.info(
        "Document upload received",
        extra={"event": "document_upload_received", "file_name": file.filename, "content_type": file.content_type},
    )
    file_bytes = await file.read()
    created = document_service.create_document(db, file, file_bytes)

    PROCESSING_QUEUE.put(created.id)
    logger.info(
        "Document queued for processing",
        extra={"event": "document_queued", "document_id": str(created.id), "queue_size": PROCESSING_QUEUE.qsize()},
    )
    return DocumentOut.model_validate(created)


@router.get("", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)) -> DocumentListResponse:
    docs = document_service.list_documents(db)
    return DocumentListResponse(items=[DocumentOut.model_validate(doc) for doc in docs])


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentOut:
    doc = document_service.get_document(db, document_id)
    return DocumentOut.model_validate(doc)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: UUID, db: Session = Depends(get_db)) -> None:
    document_service.delete_document(db, document_id)


@router.put("/{document_id}/extracted-data", response_model=DocumentOut)
def correct_extracted_data(
    document_id: UUID,
    payload: CorrectionInput,
    db: Session = Depends(get_db),
) -> DocumentOut:
    updated = document_service.update_extracted_data(db, document_id, payload)
    return DocumentOut.model_validate(updated)


@router.post("/{document_id}/summary", response_model=GenerateSummaryResponse)
def generate_summary(document_id: UUID, db: Session = Depends(get_db)) -> GenerateSummaryResponse:
    logger.info("Summary generation requested", extra={"event": "summary_generation_requested", "document_id": str(document_id)})
    document = document_service.get_document(db, document_id)
    try:
        summary = summary_service.generate_for_document(db, document)
        db.commit()
        db.refresh(summary)
    except ValueError as exc:
        raise SummaryNotReadyError(str(exc)) from exc
    except RuntimeError as exc:
        raise ServiceUnavailableError("LLM service unavailable") from exc
    logger.info("Summary generated", extra={"event": "summary_generated", "document_id": str(document_id)})
    return GenerateSummaryResponse(summary=SummaryResponse.model_validate(summary))


@router.get("/{document_id}/file")
def get_document_file(document_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    document = document_service.get_document(db, document_id)

    file_path = Path(document.file_path)
    if not file_path.exists() and not file_path.is_absolute():
        candidate = (get_settings().upload_path / file_path.name).resolve()
        if candidate.exists():
            file_path = candidate

    if not file_path.exists():
        raise NotFoundError()

    response = FileResponse(path=str(file_path), media_type=document.mime_type, filename=document.file_name)
    response.headers["Content-Disposition"] = f'inline; filename="{document.file_name}"'
    return response


def _process_document_sync(document_id: UUID) -> None:
    db = SessionLocal()
    try:
        logger.info("Background processing started", extra={"event": "document_processing_started", "document_id": str(document_id)})
        document_service.process_document(db, document_id)
        logger.info("Background processing finished", extra={"event": "document_processing_finished", "document_id": str(document_id)})
    except Exception:
        logger.exception("Document processing failed", extra={"event": "document_processing_failed", "document_id": str(document_id)})
    finally:
        db.close()
