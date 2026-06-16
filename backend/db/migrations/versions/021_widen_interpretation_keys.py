"""Widen p1/p2/aspect (and transit equivalents) to VARCHAR(40).

`true_north_lunar_node` is 21 chars and overflowed the old VARCHAR(20)
on `synastry_interpretations` and `transit_interpretations`, blowing up
POST /api/synastry/manual with StringDataRightTruncationError → 500.
Bump to 40 to fit every kerykeion planet name comfortably.

Revision ID: 021_widen_interpretation_keys
Create Date: 2026-06-16
"""

import sqlalchemy as sa  # noqa: I001
from alembic import op

revision = "021_widen_interpretation_keys"
down_revision = "020_support_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for col in ("p1", "p2", "aspect"):
        op.alter_column(
            "synastry_interpretations",
            col,
            type_=sa.String(40),
            existing_type=sa.String(20),
            existing_nullable=False,
        )
    for col in ("transit_planet", "natal_planet", "aspect"):
        op.alter_column(
            "transit_interpretations",
            col,
            type_=sa.String(40),
            existing_type=sa.String(20),
            existing_nullable=False,
        )


def downgrade() -> None:
    for col in ("p1", "p2", "aspect"):
        op.alter_column(
            "synastry_interpretations",
            col,
            type_=sa.String(20),
            existing_type=sa.String(40),
            existing_nullable=False,
        )
    for col in ("transit_planet", "natal_planet", "aspect"):
        op.alter_column(
            "transit_interpretations",
            col,
            type_=sa.String(20),
            existing_type=sa.String(40),
            existing_nullable=False,
        )
