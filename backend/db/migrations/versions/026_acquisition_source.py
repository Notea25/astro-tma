"""Acquisition source for ad attribution (first-touch).

Revision ID: 026_acquisition_source
Revises: 025_user_analytics
"""

import sqlalchemy as sa
from alembic import op

revision = "026_acquisition_source"
down_revision = "025_user_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("acquisition_source", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("acquisition_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_users_acquisition_source",
        "users",
        ["acquisition_source"],
    )


def downgrade() -> None:
    op.drop_index("ix_users_acquisition_source", table_name="users")
    op.drop_column("users", "acquisition_at")
    op.drop_column("users", "acquisition_source")
