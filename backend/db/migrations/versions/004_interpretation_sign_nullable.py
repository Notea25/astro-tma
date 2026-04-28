"""Make interpretation.sign nullable

Revision ID: 004_interpretation_sign_nullable
Create Date: 2026-04-02
"""

import sqlalchemy as sa
from alembic import op

revision = '004_interpretation_sign_nullable'
down_revision = '003_add_gender'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('interpretations', 'sign', existing_type=sa.String(32), nullable=True)


def downgrade() -> None:
    op.alter_column('interpretations', 'sign', existing_type=sa.String(32), nullable=False)
