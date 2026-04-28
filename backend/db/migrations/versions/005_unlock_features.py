"""Unlock features: synastry, notifications, glossary, news

Revision ID: 005_unlock_features
Create Date: 2026-04-20
"""

import sqlalchemy as sa
from alembic import op

revision = '005_unlock_features'
down_revision = '004_interpretation_sign_nullable'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'synastry_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('initiator_user_id', sa.BigInteger(), nullable=False),
        sa.Column('partner_user_id', sa.BigInteger(), nullable=True),
        sa.Column('token', sa.String(length=32), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'completed', 'expired', name='synastryrequeststatus'),
            nullable=False,
        ),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['initiator_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['partner_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )

    op.create_table(
        'notification_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column(
            'type',
            sa.Enum('daily_horoscope', 'transit_alert', 'news', name='notificationtype'),
            nullable=False,
        ),
        sa.Column(
            'status',
            sa.Enum('sent', 'failed', 'skipped', name='notificationstatus'),
            nullable=False,
        ),
        sa.Column('tg_message_id', sa.BigInteger(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'glossary_terms',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('title_ru', sa.String(length=128), nullable=False),
        sa.Column(
            'category',
            sa.Enum('planet', 'sign', 'house', 'aspect', 'concept', name='glossarycategory'),
            nullable=False,
        ),
        sa.Column('short_ru', sa.String(length=200), nullable=False),
        sa.Column('full_ru', sa.Text(), nullable=False),
        sa.Column('related_slugs', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    op.create_table(
        'astro_news',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('title_ru', sa.String(length=200), nullable=False),
        sa.Column('body_md', sa.Text(), nullable=False),
        sa.Column(
            'category',
            sa.Enum('aspect', 'ingress', 'moon', 'event', name='newscategory'),
            nullable=False,
        ),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('source_data', sa.JSON(), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('astro_news')
    op.drop_table('glossary_terms')
    op.drop_table('notification_logs')
    op.drop_table('synastry_requests')
    op.execute('DROP TYPE IF EXISTS newscategory')
    op.execute('DROP TYPE IF EXISTS glossarycategory')
    op.execute('DROP TYPE IF EXISTS notificationstatus')
    op.execute('DROP TYPE IF EXISTS notificationtype')
    op.execute('DROP TYPE IF EXISTS synastryrequeststatus')
