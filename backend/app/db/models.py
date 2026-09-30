import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ProcessingStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEWED = "REVIEWED"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status"),
        default=ProcessingStatus.UPLOADED,
        nullable=False,
    )

    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    ocr_result = relationship("OCRResult", back_populates="document", uselist=False, cascade="all, delete-orphan")
    extracted_data = relationship(
        "ExtractedData", back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    summary = relationship("Summary", back_populates="document", uselist=False, cascade="all, delete-orphan")


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="ocr_processing_status"),
        default=ProcessingStatus.PROCESSING,
        nullable=False,
    )
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document = relationship("Document", back_populates="ocr_result")


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    document_number_original: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_number_corrected: Mapped[str | None] = mapped_column(String(100), nullable=True)

    vendor_original: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor_corrected: Mapped[str | None] = mapped_column(String(255), nullable=True)

    document_date_original: Mapped[str | None] = mapped_column(String(20), nullable=True)
    document_date_corrected: Mapped[str | None] = mapped_column(String(20), nullable=True)

    total_amount_original: Mapped[float | None] = mapped_column(nullable=True)
    total_amount_corrected: Mapped[float | None] = mapped_column(nullable=True)

    tax_amount_original: Mapped[float | None] = mapped_column(nullable=True)
    tax_amount_corrected: Mapped[float | None] = mapped_column(nullable=True)

    currency_original: Mapped[str | None] = mapped_column(String(20), nullable=True)
    currency_corrected: Mapped[str | None] = mapped_column(String(20), nullable=True)

    confidence_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document = relationship("Document", back_populates="extracted_data")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document = relationship("Document", back_populates="summary")


Index("idx_documents_status", Document.processing_status)
Index("idx_documents_upload_date", Document.upload_date)
Index("idx_documents_type", Document.document_type)
Index("idx_extracted_vendor_original", ExtractedData.vendor_original)
Index("idx_extracted_document_number_original", ExtractedData.document_number_original)
