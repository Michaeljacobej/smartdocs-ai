"""dedupe ocr_results and add unique document_id

Revision ID: 20261001_0004
Revises: 20261001_0003
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20261001_0004"
down_revision: Union[str, None] = "20261001_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the newest OCR row per document before adding unique constraint.
    op.execute(
        """
        DELETE FROM ocr_results older
        USING ocr_results newer
        WHERE older.document_id = newer.document_id
          AND (
            older.created_at < newer.created_at
            OR (older.created_at = newer.created_at AND older.id::text < newer.id::text)
          );
        """
    )

    op.execute(
      """
      DO $$
      BEGIN
        IF NOT EXISTS (
          SELECT 1
          FROM pg_constraint
          WHERE conname = 'uq_ocr_results_document_id'
        ) THEN
          ALTER TABLE ocr_results
          ADD CONSTRAINT uq_ocr_results_document_id UNIQUE (document_id);
        END IF;
      END
      $$;
      """
    )


def downgrade() -> None:
    op.execute(
      """
      DO $$
      BEGIN
        IF EXISTS (
          SELECT 1
          FROM pg_constraint
          WHERE conname = 'uq_ocr_results_document_id'
        ) THEN
          ALTER TABLE ocr_results
          DROP CONSTRAINT uq_ocr_results_document_id;
        END IF;
      END
      $$;
      """
    )
