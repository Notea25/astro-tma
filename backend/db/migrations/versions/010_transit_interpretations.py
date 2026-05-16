"""Cache table for LLM-generated transit interpretations.

Revision ID: 010_transit_interpretations
Create Date: 2026-05-16

Keyed by (transit_planet, natal_planet, aspect) — order matters here
(transit Sun on natal Moon ≠ transit Moon on natal Sun), unlike synastry
which is symmetric. Filled on demand by services/astro/transit_interpreter.
"""

import sqlalchemy as sa
from alembic import op

revision = "010_transit_interpretations"
down_revision = "009_synastry_pair_summaries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transit_interpretations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transit_planet", sa.String(length=20), nullable=False),
        sa.Column("natal_planet", sa.String(length=20), nullable=False),
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
        sa.UniqueConstraint(
            "transit_planet",
            "natal_planet",
            "aspect",
            name="uq_transit_interp_triple",
        ),
    )


def downgrade() -> None:
    op.drop_table("transit_interpretations")
