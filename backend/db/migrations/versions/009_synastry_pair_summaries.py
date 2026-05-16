"""Cache table for LLM-generated synastry pair portraits.

Revision ID: 009_synastry_pair_summaries
Create Date: 2026-05-16

Keyed by sha256 of (aspects + scores + names) so the same pair gets the
same summary text on every recalculation (eg. via invite link AND via
manual input), instead of two slightly different LLM rolls.
"""

import sqlalchemy as sa
from alembic import op

revision = "009_synastry_pair_summaries"
down_revision = "008_synastry_hidden_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "synastry_pair_summaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("summary_ru", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", name="uq_synastry_pair_summary_key"),
    )


def downgrade() -> None:
    op.drop_table("synastry_pair_summaries")
