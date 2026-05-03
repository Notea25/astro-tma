"""Soft-delete flags for synastry requests so each side can hide a row
from their own history without affecting the other partner's view.

Revision ID: 008_synastry_hidden_flags
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op

revision = "008_synastry_hidden_flags"
down_revision = "007_synastry_interpretations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "synastry_requests",
        sa.Column(
            "hidden_by_initiator",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "synastry_requests",
        sa.Column(
            "hidden_by_partner",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("synastry_requests", "hidden_by_partner")
    op.drop_column("synastry_requests", "hidden_by_initiator")
