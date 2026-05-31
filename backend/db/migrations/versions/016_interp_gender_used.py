"""Add `gender_used` to destiny_matrix_interpretations.

Each cached LLM narrative records which gender it was generated for.
The route treats NULL or mismatched values as stale and triggers a
regeneration — fixes the bug where a user who set their gender after
the first /interpretation call kept seeing the original tone.

Existing rows get NULL (treated as stale by the route's freshness check).

Revision ID: 016_interp_gender_used
Revises: 015_arcana_v2_gender
Create Date: 2026-05-31
"""

import sqlalchemy as sa
from alembic import op

revision = "016_interp_gender_used"
down_revision = "015_arcana_v2_gender"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destiny_matrix_interpretations",
        sa.Column("gender_used", sa.String(8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("destiny_matrix_interpretations", "gender_used")
