from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models import ProcessingStatus


class ErrorPayload(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorPayload


class OCRResultOut(BaseModel):
    id: UUID
    raw_text: str | None
    processing_status: ProcessingStatus
    processing_time_ms: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExtractedDataOut(BaseModel):
    id: UUID
    document_number_original: str | None
    document_number_corrected: str | None
    vendor_original: str | None
    vendor_corrected: str | None
    document_date_original: str | None
    document_date_corrected: str | None
    total_amount_original: float | None
    total_amount_corrected: float | None
    tax_amount_original: float | None
    tax_amount_corrected: float | None
    currency_original: str | None
    currency_corrected: str | None
    confidence_data: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SummaryOut(BaseModel):
    id: UUID
    summary_text: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: UUID
    file_name: str
    mime_type: str
    file_size: int
    document_type: str | None
    processing_status: ProcessingStatus
    upload_date: datetime
    created_at: datetime
    updated_at: datetime
    ocr_result: OCRResultOut | None = None
    extracted_data: ExtractedDataOut | None = None
    summary: SummaryOut | None = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
