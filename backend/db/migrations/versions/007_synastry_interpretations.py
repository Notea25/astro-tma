"""Cache table for LLM-generated synastry aspect interpretations.

Revision ID: 007_synastry_interpretations
Create Date: 2026-05-03

Stores Russian-language interpretation text for each (p1, p2, aspect) triple,
where p1 is the alphabetically-smaller planet name. Keeps LLM cost down by
serving the same text to every pair that hits the same aspect combination.
"""

import sqlalchemy as sa
from alembic import op

revision = "007_synastry_interpretations"
down_revision = "006_mac_picks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "synastry_interpretations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("p1", sa.String(length=20), nullable=False),
        sa.Column("p2", sa.String(length=20), nullable=False),
        sa.Column("aspect", sa.String(length=20), nullable=False),
        sa.Column("text_ru", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("p1", "p2", "aspect", name="uq_synastry_interp_triple"),
    )


def downgrade() -> None:
    op.drop_table("synastry_interpretations")
