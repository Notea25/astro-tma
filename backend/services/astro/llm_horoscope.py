"""
LLM-based daily horoscope generation via Anthropic Claude Haiku.

Generates unique daily horoscope texts in Russian for all 12 zodiac signs.
Called by APScheduler at 00:05 UTC nightly.
"""

from datetime import date

from core.logging import get_logger
from core.settings import settings

log = get_logger(__name__)

_SIGN_RU: dict[str, str] = {
    "aries": "Овен", "taurus": "Телец", "gemini": "Близнецы",
    "cancer": "Рак", "leo": "Лев", "virgo": "Дева",
    "libra": "Весы", "scorpio": "Скорпион", "sagittarius": "Стрелец",
    "capricorn": "Козерог", "aquarius": "Водолей", "pisces": "Рыбы",
}

_SIGN_RULERS: dict[str, str] = {
    "aries": "Марс", "taurus": "Венера", "gemini": "Меркурий",
    "cancer": "Луна", "leo": "Солнце", "virgo": "Меркурий",
    "libra": "Венера", "scorpio": "Плутон", "sagittarius": "Юпитер",
    "capricorn": "Сатурн", "aquarius": "Уран", "pisces": "Нептун",
}

_SIGN_ELEMENTS: dict[str, str] = {
    "aries": "огонь", "taurus": "земля", "gemini": "воздух",
    "cancer": "вода", "leo": "огонь", "virgo": "земля",
    "libra": "воздух", "scorpio": "вода", "sagittarius": "огонь",
    "capricorn": "земля", "aquarius": "воздух", "pisces": "вода",
}


def _build_horoscope_prompt(sign: str, target_date: date, period: str = "today") -> str:
    sign_ru = _SIGN_RU.get(sign, sign)
    ruler = _SIGN_RULERS.get(sign, "")
    element = _SIGN_ELEMENTS.get(sign, "")

    period_desc = {
        "today": f"на сегодня ({target_date.strftime('%d.%m.%Y')})",
        "tomorrow": f"на завтра ({target_date.strftime('%d.%m.%Y')})",
        "week": "на эту неделю",
        "month": "на этот месяц",
    }.get(period, "на сегодня")

    return f"""Ты — мудрый и вдохновляющий астролог. Напиши гороскоп {period_desc} для знака {sign_ru}.

Контекст:
- Знак: {sign_ru}
- Стихия: {element}
- Управитель: {ruler}
- Дата: {target_date.strftime('%d %B %Y')}

Требования:
1. Напиши на русском языке, 4-6 предложений
2. Будь конкретным — упомяни влияние планет, аспектов, транзитов
3. Затронь 2-3 сферы: карьера/деньги, отношения/любовь, здоровье/энергия
4. Дай один конкретный совет дня
5. Тон — мудрый, тёплый, вдохновляющий, без банальностей
6. Не начинай с "Сегодня" — варьируй начало
7. Не используй emoji
8. Каждый гороскоп должен быть уникальным

Ответь ТОЛЬКО текстом гороскопа, без заголовков и пояснений."""


async def generate_daily_horoscope(
    sign: str,
    target_date: date | None = None,
    period: str = "today",
) -> str | None:
    """Generate a single horoscope text via Claude Haiku. Returns None on failure."""
    if not settings.ANTHROPIC_API_KEY:
        log.warning("llm_horoscope.no_api_key")
        return None

    target_date = target_date or date.today()

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        prompt = _build_horoscope_prompt(sign, target_date, period)

        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        log.info("llm_horoscope.generated", sign=sign, period=period, chars=len(text))
        return text
    except Exception as e:
        log.error("llm_horoscope.failed", sign=sign, error=str(e))
        return None


async def generate_energy_scores_llm(sign: str, target_date: date) -> dict[str, int]:
    """Generate energy scores via LLM. Returns dict with love/career/health/luck (0-100)."""
    if not settings.ANTHROPIC_API_KEY:
        return _fallback_scores(sign)

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        sign_ru = _SIGN_RU.get(sign, sign)

        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": (
                    f"Оцени энергии для {sign_ru} на {target_date.strftime('%d.%m.%Y')} "
                    f"по шкале 40-95. Ответь ТОЛЬКО в формате: "
                    f"love:XX career:XX health:XX luck:XX"
                ),
            }],
        )
        text = message.content[0].text.strip()
        scores = {}
        for pair in text.split():
            if ":" in pair:
                k, v = pair.split(":", 1)
                k = k.strip().lower()
                if k in ("love", "career", "health", "luck"):
                    scores[k] = max(20, min(95, int(v.strip())))
        if len(scores) == 4:
            return scores
    except Exception as e:
        log.error("llm_scores.failed", sign=sign, error=str(e))

    return _fallback_scores(sign)


def _fallback_scores(sign: str) -> dict[str, int]:
    """Deterministic fallback scores based on sign + date."""
    import hashlib
    h = hashlib.md5(f"{sign}{date.today().isoformat()}".encode()).hexdigest()
    base = [int(h[i:i+2], 16) for i in range(0, 8, 2)]
    return {
        "love": 40 + base[0] % 50,
        "career": 40 + base[1] % 50,
        "health": 45 + base[2] % 45,
        "luck": 35 + base[3] % 55,
    }
