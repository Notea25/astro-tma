"""Add mac_picks table for the new client-driven MAC flow

Revision ID: 006_mac_picks
Create Date: 2026-04-24

New table tracks picks from the 48-card client deck (components/mac/macData.ts)
without relying on the legacy mac_cards table. Stores card_number (1..48) and
category slug; content stays in the frontend deck file.
"""

import sqlalchemy as sa
from alembic import op

revision = "006_mac_picks"
down_revision = "005_unlock_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mac_picks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("card_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mac_picks_user_created",
        "mac_picks",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_mac_picks_user_created", table_name="mac_picks")
    op.drop_table("mac_picks")
