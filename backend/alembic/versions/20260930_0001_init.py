"""initial schema

Revision ID: 20260930_0001
Revises:
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260930_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    processing_status = sa.Enum("UPLOADED", "PROCESSING", "COMPLETED", "FAILED", "REVIEWED", name="processing_status")
    ocr_processing_status = sa.Enum("UPLOADED", "PROCESSING", "COMPLETED", "FAILED", "REVIEWED", name="ocr_processing_status")

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=True),
        sa.Column("processing_status", processing_status, nullable=False),
        sa.Column("upload_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_documents_status", "documents", ["processing_status"])
    op.create_index("idx_documents_upload_date", "documents", ["upload_date"])
    op.create_index("idx_documents_type", "documents", ["document_type"])

    op.create_table(
        "ocr_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("processing_status", ocr_processing_status, nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ocr_results_document_id", "ocr_results", ["document_id"])

    op.create_table(
        "extracted_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_number_original", sa.String(length=100), nullable=True),
        sa.Column("document_number_corrected", sa.String(length=100), nullable=True),
        sa.Column("vendor_original", sa.String(length=255), nullable=True),
        sa.Column("vendor_corrected", sa.String(length=255), nullable=True),
        sa.Column("document_date_original", sa.String(length=20), nullable=True),
        sa.Column("document_date_corrected", sa.String(length=20), nullable=True),
        sa.Column("total_amount_original", sa.Float(), nullable=True),
        sa.Column("total_amount_corrected", sa.Float(), nullable=True),
        sa.Column("tax_amount_original", sa.Float(), nullable=True),
        sa.Column("tax_amount_corrected", sa.Float(), nullable=True),
        sa.Column("currency_original", sa.String(length=20), nullable=True),
        sa.Column("currency_corrected", sa.String(length=20), nullable=True),
        sa.Column("confidence_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extracted_data_document_id", "extracted_data", ["document_id"])
    op.create_index("idx_extracted_vendor_original", "extracted_data", ["vendor_original"])
    op.create_index("idx_extracted_document_number_original", "extracted_data", ["document_number_original"])

    op.create_table(
        "summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_summaries_document_id", "summaries", ["document_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_summaries_document_id", table_name="summaries")
    op.drop_table("summaries")

    op.drop_index("idx_extracted_document_number_original", table_name="extracted_data")
    op.drop_index("idx_extracted_vendor_original", table_name="extracted_data")
    op.drop_index("ix_extracted_data_document_id", table_name="extracted_data")
    op.drop_table("extracted_data")

    op.drop_index("ix_ocr_results_document_id", table_name="ocr_results")
    op.drop_table("ocr_results")

    op.drop_index("idx_documents_type", table_name="documents")
    op.drop_index("idx_documents_upload_date", table_name="documents")
    op.drop_index("idx_documents_status", table_name="documents")
    op.drop_table("documents")

    sa.Enum(name="ocr_processing_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="processing_status").drop(op.get_bind(), checkfirst=True)
