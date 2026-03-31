"""Initial schema — all tables (idempotent raw-SQL version)

Revision ID: 001_initial_schema
Create Date: 2026-04-01
"""

from alembic import op

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def _create_enum_safe(name: str, values: list[str]) -> None:
    """Create a PostgreSQL ENUM type only if it doesn't exist."""
    vals = ", ".join(f"'{v}'" for v in values)
    op.execute(f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({vals});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)


def upgrade() -> None:
    # ── Enums (idempotent) ─────────────────────────────────────────────────────
    _create_enum_safe('zodiacsign', [
        'aries','taurus','gemini','cancer','leo','virgo',
        'libra','scorpio','sagittarius','capricorn','aquarius','pisces',
    ])
    _create_enum_safe('subscriptionplan', [
        'free','premium_month','premium_year',
    ])
    _create_enum_safe('subscriptionstatus', [
        'active','expired','cancelled',
    ])
    _create_enum_safe('purchasestatus', [
        'pending','completed','refunded','failed',
    ])
    _create_enum_safe('tarotarcana', [
        'major','wands','cups','swords','pentacles',
    ])
    _create_enum_safe('horoscopeperiod', [
        'today','tomorrow','week','month','year',
    ])

    # ── users ──────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              BIGINT       PRIMARY KEY,
            tg_username     VARCHAR(64),
            tg_first_name   VARCHAR(128) NOT NULL,
            tg_last_name    VARCHAR(128),
            tg_language_code VARCHAR(8)  NOT NULL DEFAULT 'ru',
            tg_is_premium   BOOLEAN      NOT NULL DEFAULT FALSE,
            birth_date      TIMESTAMP,
            birth_time_known BOOLEAN     NOT NULL DEFAULT FALSE,
            birth_city      VARCHAR(128),
            birth_lat       DOUBLE PRECISION,
            birth_lng       DOUBLE PRECISION,
            birth_tz        VARCHAR(64),
            sun_sign        zodiacsign,
            push_enabled    BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
        );
    """)

    # ── natal_charts ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS natal_charts (
            id              SERIAL       PRIMARY KEY,
            user_id         BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            sun_sign        VARCHAR(32)  NOT NULL,
            moon_sign       VARCHAR(32)  NOT NULL,
            ascendant_sign  VARCHAR(32),
            chart_data      JSON         NOT NULL,
            chart_svg_url   TEXT,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT uq_natal_charts_user_id UNIQUE (user_id)
        );
    """)

    # ── interpretations ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS interpretations (
            id       SERIAL       PRIMARY KEY,
            planet   VARCHAR(32)  NOT NULL,
            sign     VARCHAR(32)  NOT NULL,
            house    INTEGER,
            aspect   VARCHAR(32),
            text_ru  TEXT         NOT NULL,
            text_en  TEXT,
            CONSTRAINT uq_interpretation UNIQUE (planet, sign, house, aspect)
        );
    """)

    # ── daily_horoscopes ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_horoscopes (
            id            SERIAL          PRIMARY KEY,
            sign          zodiacsign      NOT NULL,
            date          TIMESTAMP       NOT NULL,
            period        horoscopeperiod NOT NULL,
            text_ru       TEXT            NOT NULL,
            love_score    INTEGER         NOT NULL DEFAULT 50,
            career_score  INTEGER         NOT NULL DEFAULT 50,
            health_score  INTEGER         NOT NULL DEFAULT 50,
            luck_score    INTEGER         NOT NULL DEFAULT 50,
            aspects_json  JSON,
            created_at    TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ     NOT NULL DEFAULT now(),
            CONSTRAINT uq_horoscope UNIQUE (sign, date, period)
        );
    """)

    # ── tarot_cards ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS tarot_cards (
            id          SERIAL        PRIMARY KEY,
            name_ru     VARCHAR(100)  NOT NULL,
            name_en     VARCHAR(100)  NOT NULL,
            arcana      tarotarcana   NOT NULL,
            number      INTEGER       NOT NULL,
            emoji       VARCHAR(8)    NOT NULL,
            upright_ru  TEXT          NOT NULL,
            reversed_ru TEXT          NOT NULL,
            keywords_ru JSON          NOT NULL,
            element     VARCHAR(20),
            image_key   VARCHAR(128),
            CONSTRAINT uq_tarot_cards_name_ru UNIQUE (name_ru),
            CONSTRAINT uq_tarot_cards_name_en UNIQUE (name_en)
        );
    """)

    # ── tarot_position_meanings ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS tarot_position_meanings (
            id               SERIAL       PRIMARY KEY,
            card_id          INTEGER      NOT NULL REFERENCES tarot_cards(id) ON DELETE CASCADE,
            spread_type      VARCHAR(32)  NOT NULL,
            position         INTEGER      NOT NULL,
            position_name_ru VARCHAR(64)  NOT NULL,
            meaning_ru       TEXT         NOT NULL,
            CONSTRAINT uq_position_meaning UNIQUE (card_id, spread_type, position)
        );
    """)

    # ── tarot_readings ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS tarot_readings (
            id          SERIAL       PRIMARY KEY,
            user_id     BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            spread_type VARCHAR(32)  NOT NULL,
            cards_json  JSON         NOT NULL,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        );
    """)

    # ── subscriptions ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id                      SERIAL             PRIMARY KEY,
            user_id                 BIGINT             NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            plan                    subscriptionplan   NOT NULL,
            status                  subscriptionstatus NOT NULL,
            stars_paid              INTEGER            NOT NULL,
            tg_payment_charge_id    VARCHAR(256)       NOT NULL,
            starts_at               TIMESTAMPTZ        NOT NULL,
            expires_at              TIMESTAMPTZ        NOT NULL,
            created_at              TIMESTAMPTZ        NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ        NOT NULL DEFAULT now(),
            CONSTRAINT uq_subscriptions_tg_payment_charge_id UNIQUE (tg_payment_charge_id)
        );
    """)

    # ── purchases ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id                    SERIAL          PRIMARY KEY,
            user_id               BIGINT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            product_id            VARCHAR(64)     NOT NULL,
            status                purchasestatus  NOT NULL,
            stars_amount          INTEGER         NOT NULL,
            tg_payment_charge_id  VARCHAR(256),
            payload               VARCHAR(512)    NOT NULL,
            created_at            TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at            TIMESTAMPTZ     NOT NULL DEFAULT now(),
            CONSTRAINT uq_purchases_tg_payment_charge_id UNIQUE (tg_payment_charge_id)
        );
    """)

    # ── Indexes (idempotent) ───────────────────────────────────────────────────
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_sun_sign            ON users            (sun_sign);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_horoscopes_sign_date ON daily_horoscopes (sign, date);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_subscriptions_user_status  ON subscriptions    (user_id, status, expires_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_purchases_user_product     ON purchases        (user_id, product_id, status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tarot_readings_user        ON tarot_readings   (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_interpretations_lookup     ON interpretations  (planet, sign);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS purchases;")
    op.execute("DROP TABLE IF EXISTS subscriptions;")
    op.execute("DROP TABLE IF EXISTS tarot_readings;")
    op.execute("DROP TABLE IF EXISTS tarot_position_meanings;")
    op.execute("DROP TABLE IF EXISTS tarot_cards;")
    op.execute("DROP TABLE IF EXISTS daily_horoscopes;")
    op.execute("DROP TABLE IF EXISTS interpretations;")
    op.execute("DROP TABLE IF EXISTS natal_charts;")
    op.execute("DROP TABLE IF EXISTS users;")
    for enum_name in ['zodiacsign', 'subscriptionplan', 'subscriptionstatus',
                      'purchasestatus', 'tarotarcana', 'horoscopeperiod']:
        op.execute(f'DROP TYPE IF EXISTS {enum_name};')
