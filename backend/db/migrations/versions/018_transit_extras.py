"""Extend transit_interpretations with affirmation / ritual / risk_warning.

011_transit_advice gave us advice_do + advice_avoid. The deep-dive UI
now also surfaces:
  * affirmation   — one-line first-person sentence the reader can say
                    aloud (Venus trine: «Я открыт принимать любовь»).
  * ritual        — one practical action for today (Mercury square:
                    «Запиши 3 вещи, которые хочешь сказать, до ответа»).
  * risk_warning  — present only on hard aspects (square / opposition,
                    or a conjunction with Mars / Saturn / Pluto / outer
                    planets). Names the specific scenario where this
                    energy is most likely to escalate.

All three are nullable — existing cached rows just don't show those UI
blocks. Background fill regenerates them on the next stale-cache hit.

Revision ID: 018_transit_extras
Create Date: 2026-06-03
"""

import sqlalchemy as sa
from alembic import op

revision = "018_transit_extras"
down_revision = "017_destiny_matrix_v3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transit_interpretations",
        sa.Column("affirmation", sa.Text(), nullable=True),
    )
    op.add_column(
        "transit_interpretations",
        sa.Column("ritual", sa.Text(), nullable=True),
    )
    op.add_column(
        "transit_interpretations",
        sa.Column("risk_warning", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transit_interpretations", "risk_warning")
    op.drop_column("transit_interpretations", "ritual")
    op.drop_column("transit_interpretations", "affirmation")
