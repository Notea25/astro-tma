"""
Moon phase calculation for current date and full monthly calendar.
Uses Kerykeion's MoonPhaseDetailsFactory — Swiss Ephemeris precision.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from kerykeion import AstrologicalSubjectFactory
from kerykeion import MoonPhaseDetailsFactory

from core.logging import get_logger

log = get_logger(__name__)

# Moon phase names in Russian
_PHASE_NAMES_RU: dict[str, str] = {
    "New Moon":         "Новолуние",
    "Waxing Crescent":  "Молодая Луна",
    "First Quarter":    "Первая Четверть",
    "Waxing Gibbous":   "Прибывающая Луна",
    "Full Moon":        "Полнолуние",
    "Waning Gibbous":   "Убывающая Луна",
    "Last Quarter":     "Последняя Четверть",
    "Waning Crescent":  "Убывающий Серп",
}

_PHASE_EMOJI: dict[str, str] = {
    "New Moon": "🌑", "Waxing Crescent": "🌒", "First Quarter": "🌓",
    "Waxing Gibbous": "🌔", "Full Moon": "🌕", "Waning Gibbous": "🌖",
    "Last Quarter": "🌗", "Waning Crescent": "🌘",
}

# Descriptions for each phase
_PHASE_DESCRIPTIONS_RU: dict[str, str] = {
    "New Moon": "Время новых начинаний. Сажайте семена желаний — они прорастут вместе с луной. Идеально для постановки целей и медитаций на привлечение.",
    "Waxing Crescent": "Луна набирает силу. Начните действовать — энергия поддерживает движение вперёд. Хорошее время для обучения и новых знакомств.",
    "First Quarter": "Период преодоления препятствий. Появятся трудности — это проверка вашего намерения. Принимайте решения смело, действуйте уверенно.",
    "Waxing Gibbous": "Почти полная луна — усильте усилия. Совершенствуйте начатое, шлифуйте детали. Интуиция обострена — слушайте её.",
    "Full Moon": "Пик лунной энергии. Кульминация начатого в новолуние. Эмоции усилены — важно сохранять равновесие. Ритуалы благодарности особенно мощны.",
    "Waning Gibbous": "Время осмысления. Делитесь знаниями и опытом. Отдавайте то, что накопили, — это освобождает пространство для нового.",
    "Last Quarter": "Отпускайте лишнее. Завершайте проекты, прощайтесь с ненужным. Организм хорошо реагирует на детокс и очищающие практики.",
    "Waning Crescent": "Глубокий отдых и интроспекция. Замедлитесь, прислушайтесь к себе. Готовьтесь к новому циклу — скоро придёт новолуние.",
}


@dataclass
class MoonPhaseInfo:
    phase_name: str
    phase_name_ru: str
    emoji: str
    description_ru: str
    illumination: float    # 0.0–1.0
    date: date


def get_moon_phase(dt: datetime | None = None) -> MoonPhaseInfo:
    """Calculate current moon phase."""
    dt = dt or datetime.now(timezone.utc)
    subject = AstrologicalSubjectFactory.from_birth_data(
        name="_moon",
        year=dt.year, month=dt.month, day=dt.day,
        hour=dt.hour, minute=dt.minute,
        lat=0.0, lng=0.0, tz_str="UTC",
        online=False,
    )
    factory = MoonPhaseDetailsFactory(subject)
    # v5: attributes live on the factory itself; v4: .get_phase() returned a dataclass
    phase = factory.get_phase() if callable(getattr(factory, "get_phase", None)) else factory

    phase_name = (
        getattr(phase, "moon_phase", None)
        or getattr(phase, "phase_name", None)
        or "Full Moon"
    )
    illumination = (
        getattr(phase, "moon_illumination", None)
        or getattr(phase, "illumination", None)
        or 0.5
    )

    return MoonPhaseInfo(
        phase_name=phase_name,
        phase_name_ru=_PHASE_NAMES_RU.get(phase_name, phase_name),
        emoji=_PHASE_EMOJI.get(phase_name, "🌙"),
        description_ru=_PHASE_DESCRIPTIONS_RU.get(phase_name, ""),
        illumination=round(float(illumination), 3),
        date=dt.date(),
    )


def get_monthly_calendar(year: int, month: int) -> list[dict[str, Any]]:
    """
    Return moon phase for each day of the month.
    Used to render the lunar calendar grid in the UI.
    """
    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    result: list[dict[str, Any]] = []

    for day in range(1, days_in_month + 1):
        dt = datetime(year, month, day, 12, 0, tzinfo=timezone.utc)
        info = get_moon_phase(dt)
        result.append({
            "day": day,
            "phase_name": info.phase_name,
            "phase_name_ru": info.phase_name_ru,
            "emoji": info.emoji,
            "illumination": info.illumination,
        })

    log.debug("moon.calendar_built", year=year, month=month, days=len(result))
    return result
