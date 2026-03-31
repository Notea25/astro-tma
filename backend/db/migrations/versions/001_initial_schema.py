"""Initial schema — all tables

Revision ID: 001_initial_schema
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

# ── Enum references for column types (create_type=False — created manually below)
zodiac_enum = postgresql.ENUM(
    'aries','taurus','gemini','cancer','leo','virgo',
    'libra','scorpio','sagittarius','capricorn','aquarius','pisces',
    name='zodiacsign', create_type=False
)

sub_plan_enum = postgresql.ENUM(
    'free','premium_month','premium_year',
    name='subscriptionplan', create_type=False
)

sub_status_enum = postgresql.ENUM(
    'active','expired','cancelled',
    name='subscriptionstatus', create_type=False
)

purchase_status_enum = postgresql.ENUM(
    'pending','completed','refunded','failed',
    name='purchasestatus', create_type=False
)

tarot_arcana_enum = postgresql.ENUM(
    'major','wands','cups','swords','pentacles',
    name='tarotarcana', create_type=False
)

horoscope_period_enum = postgresql.ENUM(
    'today','tomorrow','week','month','year',
    name='horoscopeperiod', create_type=False
)


def upgrade() -> None:
    # ── Enums via raw SQL — fully idempotent (DO/EXCEPTION block) ─────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE zodiacsign AS ENUM (
                'aries','taurus','gemini','cancer','leo','virgo',
                'libra','scorpio','sagittarius','capricorn','aquarius','pisces'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE subscriptionplan AS ENUM ('free','premium_month','premium_year');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE subscriptionstatus AS ENUM ('active','expired','cancelled');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE purchasestatus AS ENUM ('pending','completed','refunded','failed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE tarotarcana AS ENUM ('major','wands','cups','swords','pentacles');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE horoscopeperiod AS ENUM ('today','tomorrow','week','month','year');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table('users',
        sa.Column('id',               sa.BigInteger(),   primary_key=True),
        sa.Column('tg_username',      sa.String(64),     nullable=True),
        sa.Column('tg_first_name',    sa.String(128),    nullable=False),
        sa.Column('tg_last_name',     sa.String(128),    nullable=True),
        sa.Column('tg_language_code', sa.String(8),      nullable=False, server_default='ru'),
        sa.Column('tg_is_premium',    sa.Boolean(),      nullable=False, server_default='false'),
        sa.Column('birth_date',       sa.DateTime(),     nullable=True),
        sa.Column('birth_time_known', sa.Boolean(),      nullable=False, server_default='false'),
        sa.Column('birth_city',       sa.String(128),    nullable=True),
        sa.Column('birth_lat',        sa.Float(),        nullable=True),
        sa.Column('birth_lng',        sa.Float(),        nullable=True),
        sa.Column('birth_tz',         sa.String(64),     nullable=True),
        sa.Column('sun_sign',         zodiac_enum,       nullable=True),
        sa.Column('push_enabled',     sa.Boolean(),      nullable=False, server_default='true'),
        sa.Column('created_at',       sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',       sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ── natal_charts ───────────────────────────────────────────────────────────
    op.create_table('natal_charts',
        sa.Column('id',              sa.Integer(),   primary_key=True, autoincrement=True),
        sa.Column('user_id',         sa.BigInteger(),nullable=False),
        sa.Column('sun_sign',        sa.String(32),  nullable=False),
        sa.Column('moon_sign',       sa.String(32),  nullable=False),
        sa.Column('ascendant_sign',  sa.String(32),  nullable=True),
        sa.Column('chart_data',      postgresql.JSON(),nullable=False),
        sa.Column('chart_svg_url',   sa.Text(),      nullable=True),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',      sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE',
                                name='fk_natal_charts_user_id_users'),
        sa.UniqueConstraint('user_id', name='uq_natal_charts_user_id'),
    )

    # ── interpretations ────────────────────────────────────────────────────────
    op.create_table('interpretations',
        sa.Column('id',       sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('planet',   sa.String(32), nullable=False),
        sa.Column('sign',     sa.String(32), nullable=False),
        sa.Column('house',    sa.Integer(),  nullable=True),
        sa.Column('aspect',   sa.String(32), nullable=True),
        sa.Column('text_ru',  sa.Text(),     nullable=False),
        sa.Column('text_en',  sa.Text(),     nullable=True),
        sa.UniqueConstraint('planet','sign','house','aspect', name='uq_interpretation'),
    )

    # ── daily_horoscopes ───────────────────────────────────────────────────────
    op.create_table('daily_horoscopes',
        sa.Column('id',            sa.Integer(),         primary_key=True, autoincrement=True),
        sa.Column('sign',          zodiac_enum,          nullable=False),
        sa.Column('date',          sa.DateTime(),        nullable=False),
        sa.Column('period',        horoscope_period_enum,nullable=False),
        sa.Column('text_ru',       sa.Text(),            nullable=False),
        sa.Column('love_score',    sa.Integer(),         nullable=False, server_default='50'),
        sa.Column('career_score',  sa.Integer(),         nullable=False, server_default='50'),
        sa.Column('health_score',  sa.Integer(),         nullable=False, server_default='50'),
        sa.Column('luck_score',    sa.Integer(),         nullable=False, server_default='50'),
        sa.Column('aspects_json',  postgresql.JSON(),    nullable=True),
        sa.Column('created_at',    sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',    sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('sign','date','period', name='uq_horoscope'),
    )

    # ── tarot_cards ────────────────────────────────────────────────────────────
    op.create_table('tarot_cards',
        sa.Column('id',          sa.Integer(),       primary_key=True, autoincrement=True),
        sa.Column('name_ru',     sa.String(100),     nullable=False),
        sa.Column('name_en',     sa.String(100),     nullable=False),
        sa.Column('arcana',      tarot_arcana_enum,  nullable=False),
        sa.Column('number',      sa.Integer(),       nullable=False),
        sa.Column('emoji',       sa.String(8),       nullable=False),
        sa.Column('upright_ru',  sa.Text(),          nullable=False),
        sa.Column('reversed_ru', sa.Text(),          nullable=False),
        sa.Column('keywords_ru', postgresql.JSON(),  nullable=False),
        sa.Column('element',     sa.String(20),      nullable=True),
        sa.Column('image_key',   sa.String(128),     nullable=True),
        sa.UniqueConstraint('name_ru', name='uq_tarot_cards_name_ru'),
        sa.UniqueConstraint('name_en', name='uq_tarot_cards_name_en'),
    )

    # ── tarot_position_meanings ────────────────────────────────────────────────
    op.create_table('tarot_position_meanings',
        sa.Column('id',               sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('card_id',          sa.Integer(),  nullable=False),
        sa.Column('spread_type',      sa.String(32), nullable=False),
        sa.Column('position',         sa.Integer(),  nullable=False),
        sa.Column('position_name_ru', sa.String(64), nullable=False),
        sa.Column('meaning_ru',       sa.Text(),     nullable=False),
        sa.ForeignKeyConstraint(['card_id'], ['tarot_cards.id'], ondelete='CASCADE',
                                name='fk_tarot_position_meanings_card_id_tarot_cards'),
        sa.UniqueConstraint('card_id','spread_type','position',
                            name='uq_position_meaning'),
    )

    # ── tarot_readings ─────────────────────────────────────────────────────────
    op.create_table('tarot_readings',
        sa.Column('id',          sa.Integer(),       primary_key=True, autoincrement=True),
        sa.Column('user_id',     sa.BigInteger(),    nullable=False),
        sa.Column('spread_type', sa.String(32),      nullable=False),
        sa.Column('cards_json',  postgresql.JSON(),  nullable=False),
        sa.Column('created_at',  sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',  sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE',
                                name='fk_tarot_readings_user_id_users'),
    )

    # ── subscriptions ──────────────────────────────────────────────────────────
    op.create_table('subscriptions',
        sa.Column('id',                      sa.Integer(),       primary_key=True, autoincrement=True),
        sa.Column('user_id',                 sa.BigInteger(),    nullable=False),
        sa.Column('plan',                    sub_plan_enum,      nullable=False),
        sa.Column('status',                  sub_status_enum,    nullable=False),
        sa.Column('stars_paid',              sa.Integer(),       nullable=False),
        sa.Column('tg_payment_charge_id',    sa.String(256),     nullable=False),
        sa.Column('starts_at',               sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at',              sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at',              sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',              sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE',
                                name='fk_subscriptions_user_id_users'),
        sa.UniqueConstraint('tg_payment_charge_id', name='uq_subscriptions_tg_payment_charge_id'),
    )

    # ── purchases ──────────────────────────────────────────────────────────────
    op.create_table('purchases',
        sa.Column('id',                   sa.Integer(),         primary_key=True, autoincrement=True),
        sa.Column('user_id',              sa.BigInteger(),      nullable=False),
        sa.Column('product_id',           sa.String(64),        nullable=False),
        sa.Column('status',               purchase_status_enum, nullable=False),
        sa.Column('stars_amount',         sa.Integer(),         nullable=False),
        sa.Column('tg_payment_charge_id', sa.String(256),       nullable=True),
        sa.Column('payload',              sa.String(512),       nullable=False),
        sa.Column('created_at',           sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',           sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE',
                                name='fk_purchases_user_id_users'),
        sa.UniqueConstraint('tg_payment_charge_id', name='uq_purchases_tg_payment_charge_id'),
    )

    # ── Indexes ────────────────────────────────────────────────────────────────
    op.create_index('ix_users_sun_sign',           'users',           ['sun_sign'])
    op.create_index('ix_daily_horoscopes_sign_date','daily_horoscopes',['sign','date'])
    op.create_index('ix_subscriptions_user_status', 'subscriptions',   ['user_id','status','expires_at'])
    op.create_index('ix_purchases_user_product',    'purchases',       ['user_id','product_id','status'])
    op.create_index('ix_tarot_readings_user',       'tarot_readings',  ['user_id'])
    op.create_index('ix_interpretations_lookup',    'interpretations', ['planet','sign'])


def downgrade() -> None:
    op.drop_table('purchases')
    op.drop_table('subscriptions')
    op.drop_table('tarot_readings')
    op.drop_table('tarot_position_meanings')
    op.drop_table('tarot_cards')
    op.drop_table('daily_horoscopes')
    op.drop_table('interpretations')
    op.drop_table('natal_charts')
    op.drop_table('users')
    for enum_name in ['zodiacsign','subscriptionplan','subscriptionstatus',
                      'purchasestatus','tarotarcana','horoscopeperiod']:
        op.execute(f'DROP TYPE IF EXISTS {enum_name}')
