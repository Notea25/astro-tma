"""
Glossary seed — idempotent upsert of astrology terms.

Usage:
    python -m services.glossary.seed

If ANTHROPIC_API_KEY is set, missing `full_ru` fields are filled via LLM.
Existing terms are updated by slug (non-destructive — preserves `full_ru` if already present).
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.settings import settings
from db.database import AsyncSessionLocal
from db.models import GlossaryCategory, GlossaryTerm

log = get_logger(__name__)


# (slug, title_ru, category, short_ru, related_slugs)
SEED: list[tuple[str, str, GlossaryCategory, str, list[str]]] = [
    # Planets
    ("sun", "Солнце", GlossaryCategory.PLANET, "Главный светило — ядро личности, воли и жизненной силы.", ["moon", "ascendant"]),
    ("moon", "Луна", GlossaryCategory.PLANET, "Эмоции, привычки, внутренний мир и потребности души.", ["sun", "cancer"]),
    ("mercury", "Меркурий", GlossaryCategory.PLANET, "Ум, речь, обучение, коммуникация.", ["gemini", "virgo"]),
    ("venus", "Венера", GlossaryCategory.PLANET, "Любовь, ценности, красота и удовольствие.", ["taurus", "libra"]),
    ("mars", "Марс", GlossaryCategory.PLANET, "Воля, энергия действия, страсть и агрессия.", ["aries", "scorpio"]),
    ("jupiter", "Юпитер", GlossaryCategory.PLANET, "Рост, удача, философия и мировоззрение.", ["sagittarius", "pisces"]),
    ("saturn", "Сатурн", GlossaryCategory.PLANET, "Структура, дисциплина, ограничения и время.", ["capricorn"]),
    ("uranus", "Уран", GlossaryCategory.PLANET, "Свобода, перемены, оригинальность.", ["aquarius"]),
    ("neptune", "Нептун", GlossaryCategory.PLANET, "Мечты, интуиция, духовность, иллюзии.", ["pisces"]),
    ("pluto", "Плутон", GlossaryCategory.PLANET, "Трансформация, власть, глубокие перемены.", ["scorpio"]),

    # Signs
    ("aries", "Овен", GlossaryCategory.SIGN, "Кардинальный огонь. Инициатива, смелость, лидерство.", ["mars"]),
    ("taurus", "Телец", GlossaryCategory.SIGN, "Фиксированная земля. Стабильность, чувственность, верность.", ["venus"]),
    ("gemini", "Близнецы", GlossaryCategory.SIGN, "Мутабельный воздух. Любознательность, общение, гибкость.", ["mercury"]),
    ("cancer", "Рак", GlossaryCategory.SIGN, "Кардинальная вода. Чувствительность, забота, дом.", ["moon"]),
    ("leo", "Лев", GlossaryCategory.SIGN, "Фиксированный огонь. Харизма, творчество, щедрость.", ["sun"]),
    ("virgo", "Дева", GlossaryCategory.SIGN, "Мутабельная земля. Анализ, служение, точность.", ["mercury"]),
    ("libra", "Весы", GlossaryCategory.SIGN, "Кардинальный воздух. Гармония, партнёрство, эстетика.", ["venus"]),
    ("scorpio", "Скорпион", GlossaryCategory.SIGN, "Фиксированная вода. Глубина, страсть, трансформация.", ["pluto", "mars"]),
    ("sagittarius", "Стрелец", GlossaryCategory.SIGN, "Мутабельный огонь. Поиск истины, свобода, оптимизм.", ["jupiter"]),
    ("capricorn", "Козерог", GlossaryCategory.SIGN, "Кардинальная земля. Амбиции, дисциплина, ответственность.", ["saturn"]),
    ("aquarius", "Водолей", GlossaryCategory.SIGN, "Фиксированный воздух. Новаторство, гуманизм, независимость.", ["uranus"]),
    ("pisces", "Рыбы", GlossaryCategory.SIGN, "Мутабельная вода. Сопереживание, интуиция, мечты.", ["neptune"]),

    # Houses
    ("house-1", "1-й дом (Асцендент)", GlossaryCategory.HOUSE, "Личность, самопрезентация, первое впечатление.", ["ascendant"]),
    ("house-2", "2-й дом", GlossaryCategory.HOUSE, "Деньги, ценности, ресурсы, самооценка.", []),
    ("house-3", "3-й дом", GlossaryCategory.HOUSE, "Коммуникация, братья/сёстры, ближайшее окружение.", ["mercury"]),
    ("house-4", "4-й дом (IC)", GlossaryCategory.HOUSE, "Семья, дом, корни, эмоциональная основа.", ["moon"]),
    ("house-5", "5-й дом", GlossaryCategory.HOUSE, "Творчество, романтика, дети, самовыражение.", ["sun"]),
    ("house-6", "6-й дом", GlossaryCategory.HOUSE, "Работа, здоровье, привычки, служение.", ["virgo"]),
    ("house-7", "7-й дом (DSC)", GlossaryCategory.HOUSE, "Партнёрство, брак, значимые другие.", ["venus", "libra"]),
    ("house-8", "8-й дом", GlossaryCategory.HOUSE, "Трансформация, общие ресурсы, глубокие связи.", ["pluto", "scorpio"]),
    ("house-9", "9-й дом", GlossaryCategory.HOUSE, "Философия, дальние путешествия, высшее образование.", ["jupiter"]),
    ("house-10", "10-й дом (MC)", GlossaryCategory.HOUSE, "Карьера, призвание, социальный статус.", ["saturn"]),
    ("house-11", "11-й дом", GlossaryCategory.HOUSE, "Друзья, сообщества, цели и мечты.", ["aquarius"]),
    ("house-12", "12-й дом", GlossaryCategory.HOUSE, "Подсознание, уединение, духовность, скрытое.", ["neptune"]),

    # Aspects
    ("conjunction", "Соединение", GlossaryCategory.ASPECT, "Угол 0°. Слияние энергий двух планет в одну силу.", []),
    ("opposition", "Оппозиция", GlossaryCategory.ASPECT, "Угол 180°. Напряжение противоположностей, требующее баланса.", []),
    ("trine", "Трин", GlossaryCategory.ASPECT, "Угол 120°. Гармоничный поток энергии, лёгкость и поддержка.", []),
    ("square", "Квадрат", GlossaryCategory.ASPECT, "Угол 90°. Вызов, конфликт, движущая сила роста.", []),
    ("sextile", "Секстиль", GlossaryCategory.ASPECT, "Угол 60°. Возможности, требующие активных действий.", []),

    # Concepts
    ("ascendant", "Асцендент", GlossaryCategory.CONCEPT, "Восходящий знак на горизонте в момент рождения — маска для мира.", ["house-1"]),
    ("mc", "MC (Середина Неба)", GlossaryCategory.CONCEPT, "Вершина карты — призвание, репутация, карьерные цели.", ["house-10"]),
    ("retrograde", "Ретроградность", GlossaryCategory.CONCEPT, "Видимое движение планеты вспять — время переосмысления её темы.", []),
    ("transit", "Транзит", GlossaryCategory.CONCEPT, "Текущее положение планеты относительно вашей натальной карты.", []),
    ("synastry", "Синастрия", GlossaryCategory.CONCEPT, "Анализ совместимости через наложение двух натальных карт.", []),
    ("natal-chart", "Натальная карта", GlossaryCategory.CONCEPT, "Снимок неба в момент рождения — ваша астрологическая ДНК.", []),
    ("orb", "Орб", GlossaryCategory.CONCEPT, "Допустимое отклонение от точного угла аспекта.", []),
    ("element", "Стихия", GlossaryCategory.CONCEPT, "Огонь, Земля, Воздух, Вода — базовые энергетические качества знаков.", []),
    ("modality", "Крест качеств", GlossaryCategory.CONCEPT, "Кардинальный, фиксированный, мутабельный — способ проявления энергии.", []),
]


async def _generate_full(title: str, short: str, category: str) -> str:
    """Generate full description via Anthropic, fall back to short text."""
    if not settings.ANTHROPIC_API_KEY:
        return short
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        prompt = (
            f"Ты — астролог. Напиши развёрнутое определение термина «{title}» "
            f"(категория: {category}). 120–180 слов, на русском, без воды, "
            f"конкретно и с практическим применением. Краткое определение для контекста: {short}"
        )
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        return text or short
    except Exception as e:
        log.warning("glossary.llm_failed", title=title, error=str(e))
        return short


async def run() -> None:
    async with AsyncSessionLocal() as db:
        created = 0
        updated = 0
        for slug, title, category, short, related in SEED:
            result = await db.execute(
                select(GlossaryTerm).where(GlossaryTerm.slug == slug)
            )
            term = result.scalar_one_or_none()
            if term is None:
                full_ru = await _generate_full(title, short, category.value)
                term = GlossaryTerm(
                    slug=slug,
                    title_ru=title,
                    category=category,
                    short_ru=short,
                    full_ru=full_ru,
                    related_slugs=related,
                )
                db.add(term)
                created += 1
                log.info("glossary.term_created", slug=slug)
            else:
                term.title_ru = title
                term.short_ru = short
                term.category = category
                term.related_slugs = related
                if not term.full_ru or term.full_ru == term.short_ru:
                    term.full_ru = await _generate_full(title, short, category.value)
                updated += 1
        await db.commit()
        log.info("glossary.seed_done", created=created, updated=updated)


if __name__ == "__main__":
    asyncio.run(run())
