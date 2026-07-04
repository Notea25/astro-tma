"""
LLM-based daily horoscope generation via Anthropic Claude Haiku.

Generates unique daily horoscope texts in Russian for all 12 zodiac signs.
Called by APScheduler at 00:05 UTC nightly.
"""

from datetime import date

from core.logging import get_logger
from core.settings import settings
from services.llm_utils import first_text_block

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


_WEEKDAY_RU = [
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
]


def _ru_weekday(d: date) -> str:
    """Russian weekday name only — no date or year. We pass weekday
    explicitly because Haiku is unreliable at computing it from a date."""
    return _WEEKDAY_RU[d.weekday()]


# Five distinct stylistic registers. Cycled strictly by
# `date.toordinal() % 5` (see `_style_for_date` below) so two
# consecutive days can never share a style. Each block controls tone,
# structure, and — most importantly — the opener, which is what makes
# consecutive pushes «feel» same-y when it repeats.
_HOROSCOPE_STYLES: tuple[dict[str, str], ...] = (
    {
        "name": "energetic",
        "tone": (
            "Энергичный, деловой, уверенный. Как будто друг-редактор "
            "сжато рассказывает, что делать. Никакой мягкой прелюдии."
        ),
        "opener": (
            "Первое предложение — прямое действие. Начни с глагола или "
            "с конкретного «решите», «сделайте», «договоритесь», "
            "«закройте». Не с «Сегодня…», не с «У вас…»."
        ),
        "structure": (
            "Порядок: (1) прямое действие дня. (2) работа/деньги — "
            "конкретика. (3) общение/личное — короткий акцент. "
            "(4) финальный совет — одно точное действие."
        ),
    },
    {
        "name": "calm",
        "tone": (
            "Спокойный, домашний, наблюдательный. Как будто рассказчик "
            "медленно вглядывается в день, без спешки и без надрыва."
        ),
        "opener": (
            "Первое предложение — наблюдение о настроении утра или "
            "дня, БЕЗ призыва к действию. Пример: «Утро приходит тише "
            "обычного, и это к лучшему.», «День идёт своим темпом.»"
        ),
        "structure": (
            "Порядок: (1) наблюдение о дне. (2) одна сфера подробно "
            "(работа ИЛИ отношения). (3) лёгкий переход к другой. "
            "(4) мягкий совет — без императива."
        ),
    },
    {
        "name": "laconic",
        "tone": (
            "Лаконичный, картинками. Короткие предложения, много точек, "
            "минимум сложных оборотов. Стиль — телеграфный, но живой."
        ),
        "opener": (
            "Первое предложение — короткий образ до 8 слов. "
            "Пример: «День делится на две половины.», «Утро ваше.»"
        ),
        "structure": (
            "Все предложения короткие (до 12 слов), почти все "
            "завершаются точкой. Никаких длинных перечислений. Сферы "
            "затрагиваются 1-2 фразами каждая, без развёрнутых пояснений."
        ),
    },
    {
        "name": "metaphoric",
        "tone": (
            "Метафорический, образный. День описывается через одну "
            "развёрнутую метафору — чемодан, книга, разговор, погода, "
            "дорога — которая раскрывается к финалу."
        ),
        "opener": (
            "Первое предложение — развёрнутая метафора дня. "
            "Пример: «Пятница похожа на разбор старого чемодана: "
            "наверху свежее, а внизу лежит то, что давно ждёт разговора.»"
        ),
        "structure": (
            "Порядок: (1) метафора. (2) её приложение к работе/деньгам. "
            "(3) её приложение к общению/личному. (4) финальный совет "
            "как продолжение той же метафоры."
        ),
    },
    {
        "name": "direct",
        "tone": (
            "Прямое обращение к читателю. Разговорный, доверительный, "
            "иногда вопросительный. Стиль — «поговорим»."
        ),
        "opener": (
            "Первое предложение — ВОПРОС или ПРЯМОЙ ПРИЗЫВ. "
            "Пример: «Что если сегодня сказать вслух то, что "
            "откладывали?», «Позвольте себе одно медленное утро.»"
        ),
        "structure": (
            "Порядок: (1) вопрос или призыв. (2-3) две-три сферы через "
            "призму этого вопроса. (4) ответ-совет как замыкание."
        ),
    },
)


def _style_for_date(target_date: date) -> dict[str, str]:
    """Same rotation index as push.daily_style_index — text style and
    push-wrapper style rotate together, so a given day has a coherent
    stylistic register from opener to closing."""
    return _HOROSCOPE_STYLES[target_date.toordinal() % len(_HOROSCOPE_STYLES)]


def _build_horoscope_prompt(sign: str, target_date: date, period: str = "today") -> str:
    from datetime import timedelta

    sign_ru = _SIGN_RU.get(sign, sign)
    ruler = _SIGN_RULERS.get(sign, "")
    element = _SIGN_ELEMENTS.get(sign, "")

    # Effective date for THIS prompt — for "tomorrow" it's literally
    # target_date + 1, not today. Otherwise the model anchored both
    # «today» and «tomorrow» horoscopes to today's weekday («В
    # понедельник вас ждёт период…» on a Monday-tomorrow tab).
    effective_date = target_date + timedelta(days=1) if period == "tomorrow" else target_date
    weekday = _ru_weekday(effective_date)
    period_desc = {
        "today":    f"на сегодня ({weekday})",
        "tomorrow": f"на завтра ({weekday})",
        "week":     "на эту неделю",
        "month":    "на этот месяц",
    }.get(period, "на сегодня")

    # Single-day horoscopes (today/tomorrow) get a weekday hint — Haiku is
    # unreliable computing the weekday from a date string, so we feed it.
    # Week/Month horoscopes intentionally OMIT the hint — they cover many
    # days, and forcing one weekday name into a multi-day forecast made
    # the model write Monday-only prose for the whole week/month.
    if period in ("today", "tomorrow"):
        weekday_hint = (
            f" Если упоминаешь день недели, используй именно: {weekday}."
        )
    else:
        weekday_hint = (
            " Не привязывайся к одному конкретному дню недели — текст "
            "должен описывать весь период целиком."
        )

    style = _style_for_date(effective_date)

    return f"""Ты пишешь короткие гороскопы для популярного приложения. Читатели — обычные люди, не астрологи.

Гороскоп {period_desc} для знака {sign_ru} (стихия — {element}, управитель — {ruler}).{weekday_hint}

СТИЛЬ ТЕКСТА СЕГОДНЯ ({style["name"]}):
Тон: {style["tone"]}
Первое предложение: {style["opener"]}
Структура: {style["structure"]}

ЧТО НУЖНО НАПИСАТЬ (4-6 предложений):
- Главный тон периода — что приходит, на что обратить внимание.
- Затронь 2-3 жизненные сферы: работа/деньги, отношения/общение, энергия/здоровье.
- Закончи одним конкретным советом — что попробовать или чего избежать.

КАК ПИСАТЬ:
- Живой человеческий язык, как будто рассказываешь подруге за кофе.
- Конкретные образы из жизни: переписки, встречи, рабочие задачи, домашние дела.
- Без астрологического жаргона: ни «энергии», ни «вселенная подарит», ни «эманации», ни «работа со страхами».
- Без банальностей в духе «звёзды благоволят» и «впереди новые возможности».
- Обращайся на «вы», без официоза.
- Без emoji, без markdown, без заголовков.
- СТРОГО СЛЕДУЙ БЛОКУ «СТИЛЬ ТЕКСТА СЕГОДНЯ» — тон, первое предложение и структура должны точно соответствовать указанному стилю.

Ответь ТОЛЬКО текстом гороскопа."""


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

        from services.llm_pool import llm_semaphore

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        prompt = _build_horoscope_prompt(sign, target_date, period)

        async with llm_semaphore:
            message = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
        text = first_text_block(message.content).strip()
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

        from services.llm_pool import llm_semaphore

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        sign_ru = _SIGN_RU.get(sign, sign)

        async with llm_semaphore:
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
        text = first_text_block(message.content).strip()
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
