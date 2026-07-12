"""Persist natal readings and rendered PDFs.

Revision ID: 023_natal_pdf_cache
Revises: 022_content_version
"""

import sqlalchemy as sa
from alembic import op

revision = "023_natal_pdf_cache"
down_revision = "022_content_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("natal_charts", sa.Column("reading_text", sa.Text(), nullable=True))
    op.add_column(
        "natal_charts", sa.Column("reading_gender", sa.String(length=16), nullable=True)
    )
    op.add_column("natal_charts", sa.Column("reading_version", sa.Integer(), nullable=True))
    op.add_column(
        "natal_charts", sa.Column("reading_status", sa.String(length=16), nullable=True)
    )
    op.create_table(
        "natal_pdf_cache",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_natal_pdf_cache")),
    )


def downgrade() -> None:
    op.drop_table("natal_pdf_cache")
    op.drop_column("natal_charts", "reading_status")
    op.drop_column("natal_charts", "reading_version")
    op.drop_column("natal_charts", "reading_gender")
    op.drop_column("natal_charts", "reading_text")
