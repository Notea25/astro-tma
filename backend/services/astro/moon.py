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

# Phase-based action guidance (favorable / avoid).
# Used by MoonPhaseResponse and MoonCalendarDay to drive the UI guidance blocks.
_PHASE_FAVORABLE_RU: dict[str, list[str]] = {
    "New Moon": [
        "Ставить намерения и цели",
        "Начинать новое дело или проект",
        "Тихие практики и медитация",
    ],
    "Waxing Crescent": [
        "Составлять план на цикл",
        "Искать ресурсы и партнёров",
        "Учиться новому",
    ],
    "First Quarter": [
        "Принимать решения",
        "Преодолевать сопротивление",
        "Активная работа и спорт",
    ],
    "Waxing Gibbous": [
        "Творчество и самовыражение",
        "Социальные встречи и общение",
        "Продвижение проектов",
    ],
    "Full Moon": [
        "Завершать важные дела",
        "Благодарить и отпускать",
        "Отмечать результаты",
    ],
    "Waning Gibbous": [
        "Делиться опытом и знаниями",
        "Убирать лишнее из жизни и дома",
        "Завершать долги и обязательства",
    ],
    "Last Quarter": [
        "Глубокая уборка и расхламление",
        "Прощение и отпускание обид",
        "Ревизия планов",
    ],
    "Waning Crescent": [
        "Отдых и восстановление",
        "Медитация, природа, тишина",
        "Подведение итогов цикла",
    ],
}

_PHASE_AVOID_RU: dict[str, list[str]] = {
    "New Moon": [
        "Публичные события и громкие анонсы",
        "Важные переговоры и подписания",
        "Тяжёлые физические нагрузки",
    ],
    "Waxing Crescent": [
        "Отказ от только что начатых инициатив",
        "Затягивать с первыми шагами",
    ],
    "First Quarter": [
        "Долгие совещания без итогов",
        "Откладывать сложные разговоры",
    ],
    "Waxing Gibbous": [
        "Крупные траты на эмоциях",
        "Начинать диеты и ограничения",
    ],
    "Full Moon": [
        "Ссоры и острые конфликты",
        "Операции и косметические процедуры",
        "Важные решения на эмоциях",
    ],
    "Waning Gibbous": [
        "Старт новых амбициозных проектов",
        "Переедание и ночные застолья",
    ],
    "Last Quarter": [
        "Новые знакомства с расчётом на долгое",
        "Крупные покупки",
    ],
    "Waning Crescent": [
        "Перегрузки и стресс",
        "Резкие перемены и переезды",
    ],
}


def _guidance_for(phase_name: str) -> tuple[list[str], list[str]]:
    """Return (favorable_actions, avoid_actions) for a moon phase name."""
    return (
        list(_PHASE_FAVORABLE_RU.get(phase_name, [])),
        list(_PHASE_AVOID_RU.get(phase_name, [])),
    )


@dataclass
class MoonPhaseInfo:
    phase_name: str
    phase_name_ru: str
    emoji: str
    description_ru: str
    illumination: float    # 0.0–1.0
    date: date
    favorable_actions: list[str]
    avoid_actions: list[str]


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
    # kerykeion v5: MoonPhaseDetailsFactory.from_subject() → MoonPhaseOverviewModel
    overview = MoonPhaseDetailsFactory.from_subject(subject)
    moon = overview.moon  # MoonPhaseMoonSummaryModel

    phase_name = moon.phase_name or "Full Moon"

    # illumination is stored as "100%" string; convert to 0.0–1.0
    try:
        illum_str = str(moon.illumination).replace("%", "").strip()
        illumination = round(float(illum_str) / 100, 3)
    except (ValueError, TypeError):
        try:
            illumination = round(moon.detailed.illumination_details.visible_fraction, 3)
        except Exception:
            illumination = 0.5

    favorable, avoid = _guidance_for(phase_name)
    return MoonPhaseInfo(
        phase_name=phase_name,
        phase_name_ru=_PHASE_NAMES_RU.get(phase_name, phase_name),
        emoji=_PHASE_EMOJI.get(phase_name, "🌙"),
        description_ru=_PHASE_DESCRIPTIONS_RU.get(phase_name, ""),
        illumination=round(float(illumination), 3),
        date=dt.date(),
        favorable_actions=favorable,
        avoid_actions=avoid,
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
            "favorable_actions": info.favorable_actions,
            "avoid_actions": info.avoid_actions,
        })

    log.debug("moon.calendar_built", year=year, month=month, days=len(result))
    return result
