"""Add MAC cards tables

Revision ID: 002_mac_cards
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_mac_cards'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

mac_category_enum = postgresql.ENUM(
    'emotions', 'relationships', 'self', 'shadow', 'resources',
    name='maccategory', create_type=False
)


def upgrade() -> None:
    op.execute("CREATE TYPE IF NOT EXISTS maccategory AS ENUM ('emotions','relationships','self','shadow','resources')")

    op.create_table(
        'mac_cards',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name_ru', sa.String(100), nullable=False),
        sa.Column('category', mac_category_enum, nullable=False),
        sa.Column('emoji', sa.String(8), nullable=False),
        sa.Column('description_ru', sa.Text(), nullable=False),
        sa.Column('question_ru', sa.Text(), nullable=False),
        sa.Column('affirmation_ru', sa.Text(), nullable=False),
        sa.Column('image_key', sa.String(128), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name_ru'),
    )

    op.create_table(
        'mac_readings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('card_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['card_id'], ['mac_cards.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('mac_readings')
    op.drop_table('mac_cards')
    op.execute("DROP TYPE IF EXISTS maccategory")
