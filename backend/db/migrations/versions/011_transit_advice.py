"""Add advice_do / advice_avoid columns to transit_interpretations.

Revision ID: 011_transit_advice
Create Date: 2026-05-21

Used by the "What does this mean for me" deep-dive on the Transits hero card.
"""

import sqlalchemy as sa
from alembic import op

revision = "011_transit_advice"
down_revision = "010_transit_interpretations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transit_interpretations",
        sa.Column("advice_do", sa.Text(), nullable=True),
    )
    op.add_column(
        "transit_interpretations",
        sa.Column("advice_avoid", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transit_interpretations", "advice_avoid")
    op.drop_column("transit_interpretations", "advice_do")
