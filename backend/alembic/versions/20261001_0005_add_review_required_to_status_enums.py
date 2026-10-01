"""add REVIEW_REQUIRED to status enums

Revision ID: 20261001_0005
Revises: 20261001_0004
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20261001_0005"
down_revision: Union[str, None] = "20261001_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE processing_status ADD VALUE IF NOT EXISTS 'REVIEW_REQUIRED';")
    op.execute("ALTER TYPE ocr_processing_status ADD VALUE IF NOT EXISTS 'REVIEW_REQUIRED';")


def downgrade() -> None:
    # Enum value removal is intentionally omitted for PostgreSQL compatibility.
    pass
