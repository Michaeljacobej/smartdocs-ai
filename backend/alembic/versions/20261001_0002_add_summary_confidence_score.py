"""add confidence score to summaries

Revision ID: 20261001_0002
Revises: 20260930_0001
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20261001_0002"
down_revision: Union[str, None] = "20260930_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "summaries",
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("summaries", "confidence_score")
