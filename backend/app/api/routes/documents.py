from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.errors import NotFoundError, ServiceUnavailableError, SummaryNotReadyError
from app.db.database import SessionLocal, get_db
from app.schemas.document import DocumentListResponse, DocumentOut
from app.schemas.extraction import CorrectionInput
from app.schemas.summary import GenerateSummaryResponse, SummaryResponse
from app.services.service_registry import document_service, summary_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentOut:
    file_bytes = file.file.read()
    created = document_service.create_document(db, file, file_bytes)

    background_tasks.add_task(_process_document_task, created.id)
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
    document = document_service.get_document(db, document_id)
    try:
        summary = summary_service.generate_for_document(db, document)
        db.commit()
        db.refresh(summary)
    except ValueError as exc:
        raise SummaryNotReadyError(str(exc)) from exc
    except RuntimeError as exc:
        raise ServiceUnavailableError("LLM service unavailable") from exc
    return GenerateSummaryResponse(summary=SummaryResponse.model_validate(summary))


@router.get("/{document_id}/file")
def get_document_file(document_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    document = document_service.get_document(db, document_id)
    return FileResponse(path=document.file_path, media_type=document.mime_type, filename=document.file_name)


def _process_document_task(document_id: UUID) -> None:
    db = SessionLocal()
    try:
        document_service.process_document(db, document_id)
    except Exception:
        pass
    finally:
        db.close()
