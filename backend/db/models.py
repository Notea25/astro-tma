"""All ORM models — grouped by domain. One file = easy grep, easy schema overview."""
import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


# ── Enums ──────────────────────────────────────────────────────────────────────
class ZodiacSign(str, enum.Enum):
    ARIES = "aries"; TAURUS = "taurus"; GEMINI = "gemini"; CANCER = "cancer"
    LEO = "leo"; VIRGO = "virgo"; LIBRA = "libra"; SCORPIO = "scorpio"
    SAGITTARIUS = "sagittarius"; CAPRICORN = "capricorn"
    AQUARIUS = "aquarius"; PISCES = "pisces"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"

class SubscriptionPlan(str, enum.Enum):
    FREE = "free"; PREMIUM_MONTH = "premium_month"; PREMIUM_YEAR = "premium_year"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"; EXPIRED = "expired"; CANCELLED = "cancelled"

class PurchaseStatus(str, enum.Enum):
    PENDING = "pending"; COMPLETED = "completed"
    REFUNDED = "refunded"; FAILED = "failed"

class SupportTicketStatus(str, enum.Enum):
    OPEN = "open"; ANSWERED = "answered"

class MacCategory(str, enum.Enum):
    EMOTIONS = "emotions"
    RELATIONSHIPS = "relationships"
    SELF = "self"
    SHADOW = "shadow"
    RESOURCES = "resources"

class TarotArcana(str, enum.Enum):
    MAJOR = "major"; WANDS = "wands"; CUPS = "cups"
    SWORDS = "swords"; PENTACLES = "pentacles"

class HoroscopePeriod(str, enum.Enum):
    TODAY = "today"; TOMORROW = "tomorrow"
    WEEK = "week"; MONTH = "month"; YEAR = "year"

class SynastryRequestStatus(str, enum.Enum):
    PENDING = "pending"; COMPLETED = "completed"; EXPIRED = "expired"

class NotificationType(str, enum.Enum):
    DAILY_HOROSCOPE = "daily_horoscope"
    TRANSIT_ALERT = "transit_alert"
    NEWS = "news"

class NotificationStatus(str, enum.Enum):
    SENT = "sent"; FAILED = "failed"; SKIPPED = "skipped"

class GlossaryCategory(str, enum.Enum):
    PLANET = "planet"; SIGN = "sign"; HOUSE = "house"
    ASPECT = "aspect"; CONCEPT = "concept"

class NewsCategory(str, enum.Enum):
    ASPECT = "aspect"; INGRESS = "ingress"; MOON = "moon"; EVENT = "event"


# ── Mixin ─────────────────────────────────────────────────────────────────────
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False)


# ── User ──────────────────────────────────────────────────────────────────────
class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # = tg_user_id
    tg_username: Mapped[str | None] = mapped_column(String(64))
    tg_first_name: Mapped[str] = mapped_column(String(128))
    tg_last_name: Mapped[str | None] = mapped_column(String(128))
    tg_language_code: Mapped[str] = mapped_column(String(8), default="ru")
    tg_is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, values_callable=lambda e: [x.value for x in e]), nullable=True)
    birth_date: Mapped[datetime | None] = mapped_column(DateTime)
    birth_time_known: Mapped[bool] = mapped_column(Boolean, default=False)
    birth_city: Mapped[str | None] = mapped_column(String(128))
    birth_lat: Mapped[float | None] = mapped_column(Float)
    birth_lng: Mapped[float | None] = mapped_column(Float)
    birth_tz: Mapped[str | None] = mapped_column(String(64))
    sun_sign: Mapped[ZodiacSign | None] = mapped_column(Enum(ZodiacSign, values_callable=lambda e: [x.value for x in e]))
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Launch monetization v1.1 — referral programme (Model B)
    referral_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True)
    referred_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    referred_by_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    referred_purchase_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    natal_chart: Mapped["NatalChart | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    purchases: Mapped[list["Purchase"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    tarot_readings: Mapped[list["TarotReading"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")


# ── Natal Chart ───────────────────────────────────────────────────────────────
class NatalChart(TimestampMixin, Base):
    """Pre-computed via Kerykeion. Stored as JSON — never recalculate unless birth data changes."""
    __tablename__ = "natal_charts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    sun_sign: Mapped[str] = mapped_column(String(32))
    moon_sign: Mapped[str] = mapped_column(String(32))
    ascendant_sign: Mapped[str | None] = mapped_column(String(32))
    chart_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    chart_svg_url: Mapped[str | None] = mapped_column(Text)
    # Durable generated copy. Redis remains a hot cache, but an eviction must
    # never force the user to pay for the same LLM reading again.
    reading_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reading_gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reading_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reading_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    user: Mapped["User"] = relationship(back_populates="natal_chart")


class NatalPdfCache(Base):
    """One durable rendered PDF per user, kept out of hot NatalChart loads."""

    __tablename__ = "natal_pdf_cache"
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False)
    pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── Interpretation ────────────────────────────────────────────────────────────
class Interpretation(Base):
    """Content DB: planet × sign (× house × aspect) → text. Written by astrologers."""
    __tablename__ = "interpretations"
    __table_args__ = (UniqueConstraint("planet", "sign", "house", "aspect"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    planet: Mapped[str] = mapped_column(String(32))
    sign: Mapped[str | None] = mapped_column(String(32), nullable=True)
    house: Mapped[int | None] = mapped_column(Integer)
    aspect: Mapped[str | None] = mapped_column(String(32))
    text_ru: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str | None] = mapped_column(Text)


# ── Daily Horoscope ───────────────────────────────────────────────────────────
class DailyHoroscope(TimestampMixin, Base):
    """Generated nightly by APScheduler. DB copy is backup to Redis cache."""
    __tablename__ = "daily_horoscopes"
    __table_args__ = (
        UniqueConstraint(
            "sign", "date", "period", "content_version",
            name="uq_daily_horoscope_period_version",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sign: Mapped[ZodiacSign] = mapped_column(Enum(ZodiacSign, values_callable=lambda e: [x.value for x in e]), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period: Mapped[HoroscopePeriod] = mapped_column(Enum(HoroscopePeriod, values_callable=lambda e: [x.value for x in e]), nullable=False)
    text_ru: Mapped[str] = mapped_column(Text, nullable=False)
    love_score: Mapped[int] = mapped_column(Integer, default=50)
    career_score: Mapped[int] = mapped_column(Integer, default=50)
    health_score: Mapped[int] = mapped_column(Integer, default=50)
    luck_score: Mapped[int] = mapped_column(Integer, default=50)
    aspects_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    content_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="legacy", server_default="legacy"
    )


# ── Tarot ─────────────────────────────────────────────────────────────────────
class TarotCard(Base):
    """78-card deck — static data seeded once via migration."""
    __tablename__ = "tarot_cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_ru: Mapped[str] = mapped_column(String(100), unique=True)
    name_en: Mapped[str] = mapped_column(String(100), unique=True)
    arcana: Mapped[TarotArcana] = mapped_column(Enum(TarotArcana, values_callable=lambda e: [x.value for x in e]))
    number: Mapped[int] = mapped_column(Integer)
    emoji: Mapped[str] = mapped_column(String(8))
    upright_ru: Mapped[str] = mapped_column(Text)
    reversed_ru: Mapped[str] = mapped_column(Text)
    keywords_ru: Mapped[list[str]] = mapped_column(JSON)
    element: Mapped[str | None] = mapped_column(String(20))
    image_key: Mapped[str | None] = mapped_column(String(128))
    position_meanings: Mapped[list["TarotPositionMeaning"]] = relationship(
        back_populates="card", cascade="all, delete-orphan")


class TarotPositionMeaning(Base):
    """Card meaning in specific spread position. e.g. Star in position 2 = 'present'."""
    __tablename__ = "tarot_position_meanings"
    __table_args__ = (UniqueConstraint("card_id", "spread_type", "position"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("tarot_cards.id", ondelete="CASCADE"))
    spread_type: Mapped[str] = mapped_column(String(32))
    position: Mapped[int] = mapped_column(Integer)
    position_name_ru: Mapped[str] = mapped_column(String(64))
    meaning_ru: Mapped[str] = mapped_column(Text)
    card: Mapped["TarotCard"] = relationship(back_populates="position_meanings")


class TarotReading(TimestampMixin, Base):
    """User reading history. Cards stored as JSON array."""
    __tablename__ = "tarot_readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    spread_type: Mapped[str] = mapped_column(String(32))
    cards_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    user: Mapped["User"] = relationship(back_populates="tarot_readings")


# ── Payments ──────────────────────────────────────────────────────────────────
class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    plan: Mapped[SubscriptionPlan] = mapped_column(Enum(SubscriptionPlan, values_callable=lambda e: [x.value for x in e]))
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, values_callable=lambda e: [x.value for x in e]), default=SubscriptionStatus.ACTIVE)
    stars_paid: Mapped[int] = mapped_column(Integer)
    # Original Stars charge id. NULL for subscriptions bought via YuKassa
    # (where `yukassa_payment_id` carries the idempotency key instead).
    tg_payment_charge_id: Mapped[str | None] = mapped_column(String(256), unique=True, nullable=True)
    # `"stars"` (default — historical rows) or `"yukassa"`.
    payment_provider: Mapped[str] = mapped_column(String(16), default="stars", server_default="stars")
    # UUID from YuKassa's payment object. Unique → idempotent webhook retries.
    yukassa_payment_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    # Net amount paid in kopecks (rubles × 100). Only set for YuKassa rows.
    rub_amount_kopecks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Launch monetization v1.1: distinguish a granted trial from a paid sub
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    trial_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user: Mapped["User"] = relationship(back_populates="subscriptions")


class Purchase(TimestampMixin, Base):
    """One-time purchase. Every Stars or YuKassa transaction = one row."""
    __tablename__ = "purchases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, values_callable=lambda e: [x.value for x in e]), default=PurchaseStatus.PENDING)
    stars_amount: Mapped[int] = mapped_column(Integer)
    # Original Stars charge id. NULL for rows bought via YuKassa.
    tg_payment_charge_id: Mapped[str | None] = mapped_column(String(256), unique=True)
    # `"stars"` (default — historical rows) or `"yukassa"`.
    payment_provider: Mapped[str] = mapped_column(String(16), default="stars", server_default="stars")
    yukassa_payment_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    rub_amount_kopecks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[str] = mapped_column(String(512))
    user: Mapped["User"] = relationship(back_populates="purchases")


# ── Synastry ──────────────────────────────────────────────────────────────────
class SynastryRequest(TimestampMixin, Base):
    """Invite-based synastry flow: initiator buys, partner accepts via deep-link token."""
    __tablename__ = "synastry_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    initiator_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    partner_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    token: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    status: Mapped[SynastryRequestStatus] = mapped_column(
        Enum(SynastryRequestStatus, values_callable=lambda e: [x.value for x in e]),
        default=SynastryRequestStatus.PENDING, nullable=False)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hidden_by_initiator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hidden_by_partner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SynastryInterpretation(TimestampMixin, Base):
    """Cached LLM-generated text for a (planet_a, planet_b, aspect) triple.
    Keys are normalized so planet_a is alphabetically <= planet_b."""
    __tablename__ = "synastry_interpretations"
    __table_args__ = (
        UniqueConstraint(
            "p1", "p2", "aspect", "content_version",
            name="uq_synastry_interp_triple_version",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    p1: Mapped[str] = mapped_column(String(40), nullable=False)
    p2: Mapped[str] = mapped_column(String(40), nullable=False)
    aspect: Mapped[str] = mapped_column(String(40), nullable=False)
    text_ru: Mapped[str] = mapped_column(Text, nullable=False)
    content_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="legacy", server_default="legacy"
    )


class TransitInterpretation(TimestampMixin, Base):
    """Cached LLM-generated text for a (transit_planet, natal_planet, aspect)
    triple — "right now Saturn squares your Mercury" style. Separate from
    synastry_interpretations because the prompt is framed differently.

    `text_ru` is the short blurb shown on the transit card; `advice_do` /
    `advice_avoid` back the "What does this mean for me" deep-dive on the
    hero card. The advice columns are lazy-filled the first time a user
    expands the hero details.

    `affirmation` / `ritual` / `risk_warning` were added in 018 — short
    micro-content rendered in the same deep-dive panel. `risk_warning`
    is only generated for hard aspects (square / opposition, plus any
    conjunction with Mars/Saturn/Pluto/outer planets).
    """
    __tablename__ = "transit_interpretations"
    __table_args__ = (
        UniqueConstraint(
            "transit_planet", "natal_planet", "aspect", "content_version",
            name="uq_transit_interp_triple_version",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transit_planet: Mapped[str] = mapped_column(String(40), nullable=False)
    natal_planet: Mapped[str] = mapped_column(String(40), nullable=False)
    aspect: Mapped[str] = mapped_column(String(40), nullable=False)
    text_ru: Mapped[str] = mapped_column(Text, nullable=False)
    advice_do: Mapped[str | None] = mapped_column(Text, nullable=True)
    advice_avoid: Mapped[str | None] = mapped_column(Text, nullable=True)
    affirmation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ritual: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="legacy", server_default="legacy"
    )


class SynastryPairSummary(TimestampMixin, Base):
    """Cached LLM-generated pair portrait. Keyed by sha256 of the prompt-
    determining inputs (aspects + scores + names), so repeated requests
    for the same pair return the same text instead of new LLM-randomness."""
    __tablename__ = "synastry_pair_summaries"
    __table_args__ = (
        UniqueConstraint(
            "key_hash",
            "content_version",
            name="uq_synastry_pair_summary_key_version",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_ru: Mapped[str] = mapped_column(Text, nullable=False)
    content_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="legacy", server_default="legacy"
    )


# ── Notifications ─────────────────────────────────────────────────────────────
class NotificationLog(TimestampMixin, Base):
    __tablename__ = "notification_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, values_callable=lambda e: [x.value for x in e]), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, values_callable=lambda e: [x.value for x in e]), nullable=False)
    tg_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Glossary ──────────────────────────────────────────────────────────────────
class GlossaryTerm(TimestampMixin, Base):
    __tablename__ = "glossary_terms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title_ru: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[GlossaryCategory] = mapped_column(
        Enum(GlossaryCategory, values_callable=lambda e: [x.value for x in e]), nullable=False)
    short_ru: Mapped[str] = mapped_column(String(200), nullable=False)
    full_ru: Mapped[str] = mapped_column(Text, nullable=False)
    related_slugs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


# ── Astro News ────────────────────────────────────────────────────────────────
class AstroNews(TimestampMixin, Base):
    __tablename__ = "astro_news"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title_ru: Mapped[str] = mapped_column(String(200), nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[NewsCategory] = mapped_column(
        Enum(NewsCategory, values_callable=lambda e: [x.value for x in e]), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    source_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# ── MAC (Metaphorical Associative Cards) ─────────────────────────────────────
class MacCard(Base):
    """60 metaphorical cards in 5 categories — static data."""
    __tablename__ = "mac_cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_ru: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[MacCategory] = mapped_column(
        Enum(MacCategory, values_callable=lambda e: [x.value for x in e]))
    emoji: Mapped[str] = mapped_column(String(8))
    description_ru: Mapped[str] = mapped_column(Text)
    question_ru: Mapped[str] = mapped_column(Text)  # reflective question
    affirmation_ru: Mapped[str] = mapped_column(Text)  # positive affirmation
    image_key: Mapped[str | None] = mapped_column(String(128))


class MacReading(TimestampMixin, Base):
    """Legacy MAC reading history (pre-48-card deck). Kept for historical records."""
    __tablename__ = "mac_readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("mac_cards.id"))
    card: Mapped["MacCard"] = relationship()


class MacPick(Base):
    """Pick from the client-side 48-card deck (components/mac/macData.ts)."""
    __tablename__ = "mac_picks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    card_number: Mapped[int] = mapped_column(Integer)
    card_name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(32))
    created_at: Mapped["datetime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ── Referrals ────────────────────────────────────────────────────────────────
class ReferralReward(TimestampMixin, Base):
    """Audit log of every Premium-day grant from the referral programme.

    Event types:
    - "signup_referee_bonus" — referee got an extended welcome trial when
      they applied a code on signup
    - "first_purchase_referrer_bonus" — referrer got their +N days when
      the referee made their first real (paid) purchase
    """
    __tablename__ = "referral_rewards"
    __table_args__ = (
        UniqueConstraint(
            "referrer_id", "referee_id", "event_type",
            name="uq_referral_event",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    referee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    event_type: Mapped[str] = mapped_column(String(32))
    days_granted: Mapped[int] = mapped_column(Integer)


# ── Destiny Matrix ────────────────────────────────────────────────────────────


class ArcanaMeaning(Base):
    """22 arcana × 9 contexts × {any, male, female} text blocks for the
    Destiny Matrix interpretation. Filled by
    infra/scripts/seed_destiny_arcana_v2.py.

    Numbering follows the Marseille tradition (8 = Justice, 11 = Strength),
    which is what the Destiny Matrix methodology uses. The tarot module
    uses Rider-Waite (8 = Strength, 11 = Justice) — keep these tables
    separate to avoid mixing the two numbering systems.

    `gender` is 'any' / 'male' / 'female'. Lookup is reader's own gender
    first → 'any' as fallback.
    """
    __tablename__ = "arcana_meanings"
    __table_args__ = (
        CheckConstraint("arcana_num BETWEEN 1 AND 22", name="ck_arcana_num_range"),
        UniqueConstraint(
            "arcana_num", "context", "gender",
            name="uq_arcana_num_context_gender",
        ),
        Index("idx_arcana_num_ctx_gender", "arcana_num", "context", "gender"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arcana_num: Mapped[int] = mapped_column(SmallInteger)
    arcana_name: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(String(32))
    gender: Mapped[str] = mapped_column(String(8), default="any", server_default="any")
    meaning: Mapped[str] = mapped_column(Text)
    plus: Mapped[str | None] = mapped_column(Text, nullable=True)
    minus: Mapped[str | None] = mapped_column(Text, nullable=True)
    professions: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)


class DestinyMatrixReading(Base):
    """Per-user computed Destiny Matrix. Idempotent on (user_id, birth_date).
    Stored numbers — interpretation text lives in a separate table."""
    __tablename__ = "destiny_matrix_readings"
    __table_args__ = (
        UniqueConstraint("user_id", "birth_date", name="uq_dm_user_birthdate"),
        Index("idx_dm_user", "user_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"),
    )
    birth_date: Mapped[Any] = mapped_column(Date)
    positions: Mapped[dict[str, Any]] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )


class DestinyMatrixInterpretation(Base):
    """Cached LLM narrative for one Destiny Matrix reading. Lazily generated
    on first /interpretation request, cached forever per reading_id."""
    __tablename__ = "destiny_matrix_interpretations"
    __table_args__ = (
        UniqueConstraint(
            "reading_id", "content_version", name="uq_dm_interp_reading_version"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reading_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("destiny_matrix_readings.id", ondelete="CASCADE"),
    )
    sections: Mapped[dict[str, Any]] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(64))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    # 'male' / 'female' / None. NULL means «generated before gender
    # propagation existed» — route treats those as stale and regenerates
    # on the next call.
    gender_used: Mapped[str | None] = mapped_column(String(8), nullable=True)
    content_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="legacy", server_default="legacy"
    )


# ── Destiny Matrix V3 (20-section interpretation pipeline) ──────────────────


class ArcanaBase(Base):
    """22 Major Arcana cards in the Ладини canonical reading. Each row is
    the full reference text used as LLM context for V3 section generators
    — distinct from `arcana_meanings` which holds per-context (×9) shorter
    blurbs for the V2 PDF and the legacy /arcana endpoint.

    Marseille numbering (8=Justice, 11=Strength), same as the Destiny
    Matrix calculator. Filled by `infra/scripts/seed_arcana_base.py` from
    `book_arcana_base.json`.
    """
    __tablename__ = "arcana_base"
    __table_args__ = (
        CheckConstraint("num BETWEEN 1 AND 22", name="ck_arcana_base_num"),
    )
    num: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name_ru: Mapped[str] = mapped_column(Text)
    essence: Mapped[str] = mapped_column(Text)
    mission: Mapped[str] = mapped_column(Text)
    shadow: Mapped[str] = mapped_column(Text)
    healing: Mapped[str] = mapped_column(Text)
    activities: Mapped[str] = mapped_column(Text)
    famous_people: Mapped[str | None] = mapped_column(Text, nullable=True)


class KarmicProgram(Base):
    """A named karmic-tail program identified by the triple of arcana on
    the bottom axis. Canonical order is ``(bottom_2, bottom_1, bottom)``
    — read from the centre of the octagram outwards — rendered as
    ``"3-22-19"`` etc. Up to 26 unique combinations exist across all
    valid birth dates 1950-2030. Filled by
    `infra/scripts/regen_karmic_programs_v2.py` (Sonnet, reads canonical
    JSON from `content/karmic_programs_canonical.json`) + manual review.
    """
    __tablename__ = "karmic_programs"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    manifestations: Mapped[str] = mapped_column(Text)
    how_to_heal: Mapped[str] = mapped_column(Text)


class DestinyInterpretationV3(Base):
    """One LLM-generated section of the V3 destiny matrix report. The
    full report is 20 rows per (user, birth_date, gender). Cached
    permanently — the matrix doesn't change with time.

    Section keys (snake_case): ``visitka``, ``drk``, ``higher_self``,
    ``soul_tasks``, ``karmic_tail``, ``relationships``, ``money``,
    ``realization``, ``harmonization``, ``talents``, ``anahata``,
    ``purposes``, ``power_code``, ``health``, ``year_energy``.
    """
    __tablename__ = "destiny_interpretations_v3"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "birth_date", "gender", "section", "content_version",
            name="uq_destiny_v3_user_section_version",
        ),
        Index("idx_destiny_v3_user_bd", "user_id", "birth_date"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"),
    )
    birth_date: Mapped[date] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(8))
    section: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(64))
    content_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="legacy", server_default="legacy"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )


class YearEnergyInterpretation(Base):
    """Yearly forecast text keyed by ``(user_id, year_arcana)``. Refreshed
    on the user's birthday by a cron job; in the meantime it's the same
    text the user saw all year (the year_arcana value itself shifts on
    BD, so a new row appears then)."""
    __tablename__ = "year_energy_interpretations"
    __table_args__ = (
        CheckConstraint(
            "year_arcana BETWEEN 1 AND 22",
            name="ck_year_energy_arcana",
        ),
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    year_arcana: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(64))
    content_version: Mapped[str] = mapped_column(
        String(32), primary_key=True, nullable=False,
        default="legacy", server_default="legacy"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )


# ── Support tickets ──────────────────────────────────────────────────────────


class SupportTicket(TimestampMixin, Base):
    """One row per user DM to @astrosupport24_bot. First user message +
    first admin reply — MVP v1, see services/support flow.

    user_id is INTENTIONALLY not a FK to users.id: people can DM the
    support bot without ever using the main bot, and we want the ticket
    preserved even if the main user row is deleted later.
    """
    __tablename__ = "support_tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Telegram user id of the question author.
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    # Snapshot of the author's TG identity at ticket time — survives
    # username changes, useful when triaging.
    tg_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tg_first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tg_last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Original DM text (or caption for media). Empty for sticker-only or
    # voice messages — those still create a ticket so nothing's lost.
    user_message: Mapped[str] = mapped_column(Text, default="")
    # IDs to chain reply edits later if needed.
    user_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    forwarded_msg_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True,
    )
    header_msg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # open until an admin replies in the group; flips to answered on reply.
    status: Mapped[SupportTicketStatus] = mapped_column(
        Enum(SupportTicketStatus, values_callable=lambda e: [x.value for x in e]),
        default=SupportTicketStatus.OPEN,
        index=True,
    )
    # First admin reply only — MVP v1.
    admin_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    admin_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
