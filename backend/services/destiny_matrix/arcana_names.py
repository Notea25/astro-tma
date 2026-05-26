"""
22 Major Arcana — names and minimal fallback descriptions.

Important: this uses the Marseille numbering (8 = Justice / Справедливость,
11 = Strength / Сила), which is the convention the Destiny Matrix
methodology was built on. The tarot module of this same project uses
Rider-Waite (8 = Strength, 11 = Justice) — DO NOT reuse the names
across modules.

The proper per-context descriptions live in the `arcana_meanings` table,
filled by infra/scripts/seed_destiny_arcana.py. This module is the
content of last resort — if the DB row for a given (arcana, context)
isn't there yet, callers can fall back to GENERIC_DESC.
"""

from __future__ import annotations

# ── Marseille names (1..22), Russian ──────────────────────────────────────────
ARCANA_NAMES_RU: dict[int, str] = {
    1:  "Маг",
    2:  "Жрица",
    3:  "Императрица",
    4:  "Император",
    5:  "Иерофант",
    6:  "Влюблённые",
    7:  "Колесница",
    8:  "Справедливость",     # Marseille — note this is NOT Strength!
    9:  "Отшельник",
    10: "Колесо Фортуны",
    11: "Сила",               # Marseille — note this is NOT Justice!
    12: "Повешенный",
    13: "Смерть",
    14: "Умеренность",
    15: "Дьявол",
    16: "Башня",
    17: "Звезда",
    18: "Луна",
    19: "Солнце",
    20: "Суд",
    21: "Мир",
    22: "Шут",                 # Convention used by Russian Destiny Matrix sources
}


# Eight contexts the matrix maps a number to. Used as `context` column
# in arcana_meanings table and as keys in API responses.
CONTEXTS = (
    "personality",   # personality / "who you are"
    "mission",       # life purpose / main task
    "money",         # wealth / financial channel
    "love",          # love / relationships
    "health",        # body / health
    "karma",         # karmic / ancestral
    "shadow",        # shadow / lesson
    "advice",        # advice / next-step
)


GENERIC_DESC_RU = (
    "Этот аркан описывает важную часть вашей жизненной программы. "
    "Подробная интерпретация в этом контексте раскрывается через "
    "полный разбор матрицы. Откройте Premium-описание, чтобы увидеть, "
    "как именно эта энергия работает в данной сфере."
)


# Keyword cluster per arcana — used both for LLM prompts (seed script)
# and as a tiny "vibe" tag the UI can show in the bottom-sheet header.
# Kept generic / archetypal so the same list is usable in any context.
ARCANA_KEYWORDS_RU: dict[int, list[str]] = {
    1:  ["воля", "инициатива", "мастерство", "ясный ум"],
    2:  ["интуиция", "тайна", "внутреннее знание", "тишина"],
    3:  ["плодородие", "забота", "красота", "изобилие"],
    4:  ["структура", "власть", "ответственность", "порядок"],
    5:  ["традиция", "учительство", "опыт", "вера"],
    6:  ["выбор", "союз", "любовь", "ценности"],
    7:  ["движение", "победа", "контроль", "напор"],
    8:  ["баланс", "справедливость", "истина", "решение"],
    9:  ["уединение", "поиск", "мудрость", "самопознание"],
    10: ["судьба", "цикл", "поворот", "удача"],
    11: ["сила", "терпение", "укрощение", "внутренний стержень"],
    12: ["пауза", "перевёрнутый взгляд", "жертва", "переоценка"],
    13: ["трансформация", "конец", "перерождение", "освобождение"],
    14: ["умеренность", "интеграция", "поток", "алхимия"],
    15: ["соблазн", "теневое", "зависимость", "материя"],
    16: ["крах", "пробуждение", "разрушение иллюзий", "очищение"],
    17: ["надежда", "вдохновение", "вера", "обновление"],
    18: ["иллюзия", "интуиция", "ночь души", "тайные процессы"],
    19: ["радость", "ясность", "успех", "жизненная сила"],
    20: ["пробуждение", "оценка", "зов", "обновление"],
    21: ["завершение", "целостность", "мир внутри", "интеграция"],
    22: ["свобода", "наивность", "начало", "доверие потоку"],
}


def arcana_name(num: int) -> str:
    """Human Russian name for an arcana number. Falls back to f'Аркан {num}'
    if the number is out of range — defensive, shouldn't happen if the
    calculator's fold_to_arcana is used correctly."""
    return ARCANA_NAMES_RU.get(num, f"Аркан {num}")
