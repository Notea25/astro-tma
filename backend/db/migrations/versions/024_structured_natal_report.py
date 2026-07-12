"""Persist the canonical structured natal report.

Revision ID: 024_structured_natal_report
Revises: 023_natal_pdf_cache
"""

import sqlalchemy as sa
from alembic import op

revision = "024_structured_natal_report"
down_revision = "023_natal_pdf_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "natal_charts",
        "reading_status",
        existing_type=sa.String(length=16),
        type_=sa.String(length=24),
        existing_nullable=True,
    )
    op.add_column("natal_charts", sa.Column("reading_payload", sa.JSON(), nullable=True))
    op.add_column(
        "natal_charts", sa.Column("reading_input_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "natal_charts",
        sa.Column("reading_content_version", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("natal_charts", "reading_content_version")
    op.drop_column("natal_charts", "reading_input_hash")
    op.drop_column("natal_charts", "reading_payload")
    op.alter_column(
        "natal_charts",
        "reading_status",
        existing_type=sa.String(length=24),
        type_=sa.String(length=16),
        existing_nullable=True,
    )
