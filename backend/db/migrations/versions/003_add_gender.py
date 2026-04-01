"""Add gender column to users

Revision ID: 003_add_gender
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa

revision = '003_add_gender'
down_revision = '002_mac_cards'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE gender AS ENUM ('male','female');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.add_column('users', sa.Column('gender', sa.Enum('male', 'female', name='gender'), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'gender')
    op.execute("DROP TYPE IF EXISTS gender")
