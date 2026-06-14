"""V3 destiny-matrix interpreter — 15 sections, one Sonnet call each.

Replaces the legacy 8-section interpreter (`interpreter.py`) for V3
readings. Each section is generated independently so the frontend
accordion can show partial progress and the user can ask for one
specific card to be re-rolled without invalidating the other 14.

Architecture:
  * `V3Context` packages everything the prompts need (matrix positions,
    full arcana_base text per cited card, purposes_v3 triples, year
    energy, karmic-program row).
  * `SECTIONS` is the registry of 15 `SectionSpec` entries. Each spec
    has a key, title, prompt builder, and target word count.
  * `generate_all()` fires the 15 calls concurrently through the global
    `llm_semaphore` (limit=6). Wall-clock ≈ 12-20s at Sonnet rates.
  * Results are cached row-per-section in `destiny_interpretations_v3`,
    keyed by `(user_id, birth_date, gender, section)`. Cache survives
    profile updates as long as gender doesn't flip.

Cost: 15 × ~3000 input + ~900 output tokens at Sonnet 4.5 rates ≈
$0.10-0.18 per full generation. Cached forever after first run for the
same (user, birth_date, gender) — only the year-energy section is
regenerated annually by the BD cron.

Gender directive is repeated in BOTH system and per-section user
prompts (long-tail generations sometimes drop the system rule).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.settings import settings
from db.models import (
    ArcanaBase,
    DestinyInterpretationV3,
    KarmicProgram,
)
from services.destiny_matrix.arcana_names import ARCANA_NAMES_RU
from services.destiny_matrix.extended import (
    PurposeTriple,
    YearEnergy,
    calculate_purposes_v3,
    calculate_year_energy,
    karmic_program_key,
)
from services.llm_pool import llm_semaphore

log = get_logger(__name__)

MODEL_V3 = "claude-sonnet-4-5-20250929"

SECTION_TITLES: dict[str, str] = {
    "visitka":       "Визитка",
    "drk":           "Дерево Рода и Кармы",
    # higher_self / soul_tasks / realization deliberately removed — their
    # content was 1:1 with purpose_personal_divine / purpose_*_personal /
    # purpose_wholeness_lineage respectively. Canonical home is now the
    # 8 dedicated purpose_* pages + the purposes overview.
    "karmic_tail":   "Кармический хвост",
    "relationships": "Отношения",
    "money":         "Деньги",
    "harmonization": "Гармонизация",
    "talents":       "Таланты",
    "anahata":       "Анахата (сердечный центр)",
    "purposes":      "8 предназначений",
    "power_code":    "Код силы",
    "health":        "Здоровье и чакры",
    "year_energy":   "Энергия года",
    # 8 per-purpose deep dives — each is a separate Sonnet call so the
    # tap-to-expand UI shows context-specific text. Without these, all 8
    # cells pulled the same `arcana_meanings.context='purpose'` row, so
    # purposes that happened to land on the same arcana got identical
    # copy and purposes whose arcana row was missing showed empty text.
    "purpose_celestial_personal": "Предназначение · Небесное личное",
    "purpose_earthly_personal":   "Предназначение · Земное личное",
    "purpose_wholeness_personal": "Предназначение · Целостное личное",
    "purpose_father_lineage":     "Предназначение · Род Отца",
    "purpose_mother_lineage":     "Предназначение · Род Матери",
    "purpose_wholeness_lineage":  "Предназначение · Социальная реализация",
    "purpose_personal_divine":    "Предназначение · Личное Божественное",
    "purpose_divine_mission":     "Предназначение · Божественная миссия",
}

# Short framing line injected into each per-purpose prompt so the model
# orients on the specific role of that linе in the Ладини methodology.
_PURPOSE_CONTEXT_HINTS: dict[str, str] = {
    "celestial_personal": (
        "Небесное личное — духовная жизнь, что ведёт изнутри, источник смысла."
    ),
    "earthly_personal": (
        "Земное личное — материальная сторона жизни, тело, ресурсы, дом."
    ),
    "wholeness_personal": (
        "Целостное личное — баланс между духовным и земным в твоей жизни."
    ),
    "father_lineage": (
        "Что приходит по линии Отца — таланты и кармические задачи рода отца."
    ),
    "mother_lineage": (
        "Что приходит по линии Матери — таланты и кармические задачи рода матери."
    ),
    "wholeness_lineage": (
        "Социальная реализация на пересечении родов — что отдаёшь миру в зрелости."
    ),
    "personal_divine": (
        "Личное Божественное — путь индивидуальной духовной зрелости и интуиции."
    ),
    "divine_mission": (
        "Большая миссия — что значит твоё проявление для других людей."
    ),
}


# ── Context ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ArcanaDoc:
    """Subset of an `arcana_base` row, kept light because we ship many
    of these to the LLM at once."""
    num: int
    name: str
    essence: str
    mission: str
    shadow: str
    healing: str
    activities: str


@dataclass(frozen=True)
class KarmicDoc:
    key: str
    name: str
    description: str
    manifestations: str
    how_to_heal: str


@dataclass(frozen=True)
class V3Context:
    user_id: int
    birth_date: date
    gender: str                  # 'male' / 'female' / 'any'
    name: str | None
    positions: dict[str, Any]
    purposes: dict[str, PurposeTriple]
    year_energy: YearEnergy
    arcana: dict[int, ArcanaDoc]
    karmic: KarmicDoc | None
    extras: dict[str, Any] = field(default_factory=dict)


async def load_v3_context(
    session: AsyncSession,
    *,
    user_id: int,
    birth_date: date,
    gender: str,
    name: str | None,
    positions: dict[str, Any],
    on_date: date | None = None,
) -> V3Context:
    """Hydrate everything the 15 section generators need with one trip
    to the DB. `positions` is the calculator output; `on_date` defaults
    to today for year-energy timing."""
    arc_rows = (await session.execute(select(ArcanaBase))).scalars().all()
    arcana = {
        r.num: ArcanaDoc(
            num=r.num,
            name=r.name_ru,
            essence=r.essence,
            mission=r.mission,
            shadow=r.shadow,
            healing=r.healing,
            activities=r.activities,
        )
        for r in arc_rows
    }

    km_key = karmic_program_key(positions)
    km_row = (
        await session.execute(select(KarmicProgram).where(KarmicProgram.key == km_key))
    ).scalar_one_or_none()
    karmic = (
        KarmicDoc(
            key=km_row.key,
            name=km_row.name,
            description=km_row.description,
            manifestations=km_row.manifestations,
            how_to_heal=km_row.how_to_heal,
        )
        if km_row
        else None
    )

    return V3Context(
        user_id=user_id,
        birth_date=birth_date,
        gender=gender or "any",
        name=name,
        positions=positions,
        purposes=calculate_purposes_v3(positions),
        year_energy=calculate_year_energy(birth_date, on_date),
        arcana=arcana,
        karmic=karmic,
    )


# ── Prompt helpers ──────────────────────────────────────────────────────────


def _arcana_canon_block() -> str:
    """Inject the 22 canonical arcana names so the model can't fall back
    on the Rider-Waite tarot tradition (Дьявол / Луна / Повешенный / …)."""
    from services.destiny_matrix.calculator import ARCANA_NAMES
    rows = [f"  {n:2d} {ARCANA_NAMES[n]}" for n in range(1, 23)]
    return "\n".join(rows)


_BASE_SYSTEM = f"""Ты — практикующий мастер Матрицы Судьбы, опираешься на \
методологию Натальи Ладини. Пишешь тёплый, конкретный, поддерживающий \
разбор для читателя на «ты».

КРИТИЧНО ПРО ПОЛ ЧИТАТЕЛЯ:
Если в пользовательском промпте указан пол, ВСЕ грамматические формы
(прилагательные, причастия, глаголы прошедшего времени, обращения)
должны быть в соответствующем роде. Не объясняй сам факт пола читателя —
просто пиши в нужном роде.

СТИЛЬ:
- Связный осмысленный текст, не свалка значений арканов.
- Принцип «плюс/минус»: энергия не плохая, важно как проживается.
- Без эзотерических штампов («высшее служение», «вселенский поток»).
- Без медицинских, юридических, инвестиционных советов.
- Без предсказаний дат и событий.

ИМЕНА АРКАНОВ (КАНОН ЛАДИНИ — ИСПОЛЬЗОВАТЬ ТОЛЬКО ЭТИ):
{_arcana_canon_block()}

Цитируй арканы по номеру и названию из таблицы выше: «аркан 5 (Учитель)».
ЗАПРЕЩЕНЫ классические таро-имена: Дьявол, Луна, Повешенный, Шут, Дурак,
Иерофант, Жрец, Колесо Фортуны, Смерть, Умеренность, Башня, Отшельник,
Верховная Жрица, Колесница, Суд, Маги́цы и т.п. При нумерации N всегда
берёшь {{N}} → имя из таблицы выше.

ФОРМАТ:
- Возвращай ТОЛЬКО готовый текст секции на русском.
- НЕ начинай ответ со слов «Ответ», «Вот», «Разбор», «Конечно», «Хорошо».
  Сразу с первого осмысленного абзаца.
- Не добавляй markdown-заголовок секции — заголовок уже есть в UI.
- Допустим список (нумерованный или •) и абзацы.
- Не оборачивай ответ в кавычки или код-блок."""


def _gender_directive(gender: str) -> str:
    if gender == "male":
        return (
            "Пол читателя: МУЖЧИНА. ВСЕ формы глаголов и прилагательных в "
            "мужском роде («ты сделал», «настоящий», «один такой»). Партнёр "
            "= партнёрша, жена. Ребёнок = сын или дочь.\n\n"
        )
    if gender == "female":
        return (
            "Пол читателя: ЖЕНЩИНА. ВСЕ формы глаголов и прилагательных в "
            "женском роде («ты сделала», «настоящая», «одна такая»). Партнёр "
            "= партнёр, муж. Ребёнок = сын или дочь.\n\n"
        )
    return ""


def _arc_brief(arc: ArcanaDoc, *, sections: tuple[str, ...] = ("essence", "shadow")) -> str:
    """Compact arcana reference block, ~150-300 words depending on which
    sections of the canonical text we include."""
    parts = [f"АРКАН {arc.num} — {arc.name}"]
    if "essence" in sections:
        parts.append(f"Суть: {arc.essence}")
    if "mission" in sections:
        parts.append(f"Миссия: {arc.mission}")
    if "shadow" in sections:
        parts.append(f"Тень: {arc.shadow}")
    if "healing" in sections:
        parts.append(f"Исцеление: {arc.healing}")
    if "activities" in sections:
        parts.append(f"Сферы: {arc.activities}")
    return "\n".join(parts)


def _name(num: int) -> str:
    return ARCANA_NAMES_RU.get(num, f"Аркан {num}")


def _format_cards(nums: list[int], arcana: dict[int, ArcanaDoc]) -> str:
    """Bulleted list of cards by number → name, deduped while preserving
    order — handy for prompts that want a quick overview before the
    deep reference blocks."""
    seen: set[int] = set()
    lines: list[str] = []
    for n in nums:
        if n in seen:
            continue
        seen.add(n)
        a = arcana.get(n)
        nm = a.name if a else _name(n)
        lines.append(f"• Аркан {n} — {nm}")
    return "\n".join(lines)


def _header(ctx: V3Context, section_key: str) -> str:
    bd = ctx.birth_date.strftime("%d.%m.%Y")
    name_line = f"Имя: {ctx.name}\n" if ctx.name else ""
    return (
        f"{name_line}Дата рождения: {bd}\n"
        f"Раздел разбора: {SECTION_TITLES[section_key]}\n\n"
        f"{_gender_directive(ctx.gender)}"
    )


# ── 15 section prompt builders ──────────────────────────────────────────────


def _prompt_visitka(ctx: V3Context) -> tuple[str, int]:
    """Общий портрет: M, D, Y, B, C — центральные арканы личности."""
    pos = ctx.positions["personality"]
    nums = [pos["month"], pos["day"], pos["year"], pos["bottom"], pos["center"]]
    refs = "\n\n".join(_arc_brief(ctx.arcana[n]) for n in dict.fromkeys(nums))
    return (
        _header(ctx, "visitka")
        + "Это первый раздел разбора — короткая визитка читателя. Дай ёмкий "
        "портрет личности по пяти ключевым позициям, без подробностей "
        "(они будут в следующих разделах). Покажи через что читатель "
        "проявляется в мире и в чём его центральный мотив.\n\n"
        f"Позиции:\n"
        f"• Месяц (M) — аркан {pos['month']} ({_name(pos['month'])}) — таланты, "
        "что вдохновляет\n"
        f"• День (D) — аркан {pos['day']} ({_name(pos['day'])}) — портрет личности\n"
        f"• Год (Y) — аркан {pos['year']} ({_name(pos['year'])}) — опыт рода\n"
        f"• Низ (B) — аркан {pos['bottom']} ({_name(pos['bottom'])}) — "
        "главный кармический урок\n"
        f"• Центр (C) — аркан {pos['center']} ({_name(pos['center'])}) — "
        "характер, зона комфорта\n\n"
        f"Справка по арканам:\n\n{refs}\n\n"
        "Напиши 250-300 слов: 2-3 связных абзаца. Без списков, без подзаголовков."
    ), 280


def _prompt_drk(ctx: V3Context) -> tuple[str, int]:
    """Дерево Рода и Кармы — родовой квадрат + линии отца/матери.
    Предназначения Рода Отца/Матери раскрываются на страницах Предн.4/5 —
    здесь формулы-суммы НЕ выводим."""
    sq = ctx.positions["ancestral_square"]
    ln = ctx.positions["lines"]
    nums = [sq["top_left"], sq["top_right"], sq["bottom_right"], sq["bottom_left"]]
    refs = "\n\n".join(_arc_brief(ctx.arcana[n]) for n in dict.fromkeys(nums))
    return (
        _header(ctx, "drk")
        + "Дерево Рода — что приходит от родителей: программы, подарки и тени по "
        "линии отца и линии матери, и что встреча двух линий значит для тебя "
        "сейчас.\n\n"
        "ГРАНИЦА РАЗДЕЛА: НЕ выводи и не пересчитывай формулы-суммы "
        "предназначений Рода Отца и Рода Матери — для них есть отдельные "
        "страницы. Здесь — ТОЛЬКО родовой квадрат и линии: какие качества и "
        "кармические темы пришли, как проявляются, что важно прожить. Без "
        "сложений вида «X + Y = Z».\n\n"
        f"Родовой квадрат:\n"
        f"• Верх слева (отец, духовное): аркан {sq['top_left']} ({_name(sq['top_left'])})\n"
        f"• Верх справа (мать, духовное): аркан {sq['top_right']} ({_name(sq['top_right'])})\n"
        f"• Низ справа (мать, материальное): аркан {sq['bottom_right']} ({_name(sq['bottom_right'])})\n"
        f"• Низ слева (отец, материальное): аркан {sq['bottom_left']} ({_name(sq['bottom_left'])})\n\n"
        f"Линия Отца: аркан {ln['father']} ({_name(ln['father'])})\n"
        f"Линия Матери: аркан {ln['mother']} ({_name(ln['mother'])})\n\n"
        f"Справка по арканам:\n\n{refs}\n\n"
        "Напиши 300-380 слов. Сначала линия Отца (что унаследовано, как "
        "проявляется, что прорабатывать), потом линия Матери. Закончи 2-3 "
        "фразами о том, что отношения между линиями значат для тебя сейчас."
    ), 350


def _prompt_karmic_tail(ctx: V3Context) -> tuple[str, int]:
    """Кармический хвост — bottom + bottom_1 + bottom_2 + canonical program."""
    pos = ctx.positions
    bottom = pos["personality"]["bottom"]
    bottom_1 = pos["channels"]["karmic_tail"][0]
    bottom_2 = pos["specials"]["love"]
    refs = "\n\n".join(
        _arc_brief(ctx.arcana[n], sections=("essence", "shadow", "healing"))
        for n in dict.fromkeys([bottom, bottom_1, bottom_2])
    )

    if ctx.karmic:
        canon = (
            f"КАНОНИЧЕСКОЕ ОПИСАНИЕ ПРОГРАММЫ {ctx.karmic.key} "
            f"«{ctx.karmic.name}»:\n\n"
            f"{ctx.karmic.description}\n\n"
            f"Как проявляется: {ctx.karmic.manifestations}\n\n"
            f"Как прорабатывать:\n{ctx.karmic.how_to_heal}\n\n"
            "Используй это описание как опору, но не пересказывай дословно — "
            "адаптируй под конкретного читателя по его арканам и полу. Перефразируй, "
            "сделай личное обращение «ты»."
        )
    else:
        canon = (
            "Канонического описания этой программы нет в базе — "
            "построй её сам из трёх арканов оси."
        )

    return (
        _header(ctx, "karmic_tail")
        + "Кармический хвост — самая глубокая, корневая программа разбора. Это "
        "то, что душа принесла из прошлых воплощений и что важно прожить и "
        "исцелить в этой жизни.\n\n"
        f"Тройка нижней оси:\n"
        f"• Низ (B): аркан {bottom} ({_name(bottom)}) — главная нота\n"
        f"• Низ-1: аркан {bottom_1} ({_name(bottom_1)}) — пересечение с центром\n"
        f"• Низ-2: аркан {bottom_2} ({_name(bottom_2)}) — мидпоинт между B и центром\n\n"
        f"Справка по арканам:\n\n{refs}\n\n"
        f"{canon}\n\n"
        "Напиши 350-450 слов: что было в прошлом воплощении, как это "
        "проявляется сейчас, и пронумерованный список из 5-7 конкретных "
        "шагов проработки. Без расплывчатых формулировок."
    ), 400


def _prompt_relationships(ctx: V3Context) -> tuple[str, int]:
    """Отношения — love special + B_right + sky-line."""
    sp = ctx.positions["specials"]
    pos = ctx.positions["personality"]
    love = sp["love"]
    nums = [love, pos["month"], pos["day"]]
    refs = "\n\n".join(
        _arc_brief(ctx.arcana[n], sections=("essence", "shadow", "healing"))
        for n in dict.fromkeys(nums)
    )
    return (
        _header(ctx, "relationships")
        + "Раздел про любовь и партнёрство. Какого партнёра ты притягиваешь, "
        "что тебе в нём отзывается, какие сценарии повторяются и через что "
        "ты учишься любви.\n\n"
        f"• Точка любви: аркан {love} ({_name(love)})\n"
        f"• Месяц (что в тебе видят): аркан {pos['month']} ({_name(pos['month'])})\n"
        f"• День (как ты подаёшь себя): аркан {pos['day']} ({_name(pos['day'])})\n\n"
        f"Справка:\n\n{refs}\n\n"
        "Напиши 300-400 слов. Покажи: 1) тип партнёра, который тебя притягивает; "
        "2) что в отношениях даётся легко; 3) на чём чаще всего «застреваешь» "
        "и как с этим работать. Без советов «найди другого» — только про "
        "внутреннюю работу."
    ), 350


def _prompt_money(ctx: V3Context) -> tuple[str, int]:
    """Деньги — финансовый канал + точка денег + вход денег."""
    ch = ctx.positions["channels"]
    fin = ch["finance"]
    sp = ctx.positions["specials"]
    entries = ctx.positions["entries"]
    money_point = sp["money"]
    money_entry = entries["money"]
    nums = [fin[0], fin[1], fin[2], money_point, money_entry]
    refs = "\n\n".join(
        _arc_brief(ctx.arcana[n], sections=("essence", "shadow", "activities"))
        for n in dict.fromkeys(nums)
    )
    return (
        _header(ctx, "money")
        + "Деньги — откуда приходят, через что блокируются, какие профессии "
        "дают доход без надрыва.\n\n"
        f"Финансовый канал (вход → работа → итог): "
        f"{fin[0]} ({_name(fin[0])}) → {fin[1]} ({_name(fin[1])}) → {fin[2]} ({_name(fin[2])})\n"
        f"• Точка денег: аркан {money_point} ({_name(money_point)})\n"
        f"• Вход денег (как заходят): аркан {money_entry} ({_name(money_entry)})\n\n"
        f"Справка:\n\n{refs}\n\n"
        "Напиши 300-380 слов. Покажи: 1) откуда приходят деньги; 2) через что "
        "нужно проявляться, чтобы они шли; 3) куда уходят и в чём итог канала; "
        "4) типичные блоки и как их размыкать. Конкретно, без «откройся "
        "изобилию»."
    ), 350


def _prompt_harmonization(ctx: V3Context) -> tuple[str, int]:
    """Гармонизация — баланс sky/earth + центр (C)."""
    pos = ctx.positions
    lines = pos["lines"]
    center = pos["personality"]["center"]
    nums = [lines["sky"], lines["earth"], center]
    refs = "\n\n".join(
        _arc_brief(ctx.arcana[n], sections=("essence", "healing"))
        for n in dict.fromkeys(nums)
    )
    return (
        _header(ctx, "harmonization")
        + "Гармонизация — про баланс Небесного и Земного, духа и материи. "
        "Какая из вертикалей ведущая, в какую сторону читателя «уносит» и "
        "как через центр (C) приходить в равновесие.\n\n"
        f"• Небо (вертикаль): аркан {lines['sky']} ({_name(lines['sky'])})\n"
        f"• Земля (горизонталь): аркан {lines['earth']} ({_name(lines['earth'])})\n"
        f"• Центр (C): аркан {center} ({_name(center)})\n\n"
        f"Справка:\n\n{refs}\n\n"
        "Напиши 250-320 слов. Покажи, какая ось доминирует, какие перекосы "
        "это даёт, и через что центральный аркан возвращает в баланс."
    ), 300


def _prompt_talents(ctx: V3Context) -> tuple[str, int]:
    """Таланты — канал talents + month (M)."""
    ch = ctx.positions["channels"]
    tal = ch["talents"]
    month = ctx.positions["personality"]["month"]
    nums = [tal[0], tal[1], tal[2], month]
    refs = "\n\n".join(
        _arc_brief(ctx.arcana[n], sections=("essence", "mission", "activities"))
        for n in dict.fromkeys(nums)
    )
    return (
        _header(ctx, "talents")
        + "Таланты — что даётся легко, что вдохновляет, через что читатель "
        "входит в поток. Это не обязательно работа — может быть хобби, "
        "способ отдыха, способ восстановиться.\n\n"
        f"Канал талантов: {tal[0]} ({_name(tal[0])}) → {tal[1]} ({_name(tal[1])}) → "
        f"{tal[2]} ({_name(tal[2])})\n"
        f"Месяц (M): аркан {month} ({_name(month)})\n\n"
        f"Справка:\n\n{refs}\n\n"
        "Напиши 300-380 слов про конкретные сферы и форматы деятельности, "
        "которые подойдут. Не «работа в творчестве», а «звукорежиссура, "
        "фотография, написание текстов». Без советов поменять профессию."
    ), 350


def _prompt_anahata(ctx: V3Context) -> tuple[str, int]:
    """Анахата — сердечная чакра, центральная позиция в чакрах."""
    pos = ctx.positions
    center = pos["personality"]["center"]
    # chakras["sky"|"earth"] is a dict keyed by chakra name in our payload.
    anahata_sky = pos["chakras"]["sky"]["anahata"]
    anahata_earth = pos["chakras"]["earth"]["anahata"]
    nums = [anahata_sky, anahata_earth, center]
    refs = "\n\n".join(
        _arc_brief(ctx.arcana[n], sections=("essence", "healing"))
        for n in dict.fromkeys(nums)
    )
    return (
        _header(ctx, "anahata")
        + "Анахата (сердечный центр) — про любовь к себе, доверие миру, "
        "способность принимать и отдавать. Это центральный энергетический "
        "узел всей матрицы.\n\n"
        f"• Анахата Небо: аркан {anahata_sky} ({_name(anahata_sky)})\n"
        f"• Анахата Земля: аркан {anahata_earth} ({_name(anahata_earth)})\n"
        f"• Центр (С): аркан {center} ({_name(center)})\n\n"
        f"Справка:\n\n{refs}\n\n"
        "Напиши 250-300 слов о том, как у читателя устроена работа сердца — "
        "в духовном измерении (Небо) и в материальном (Земля), и какую роль "
        "играет центральный аркан."
    ), 280


def _make_purpose_prompt(purpose_key: str):
    """Factory for the 8 per-purpose deep-dive prompts.

    Each generated prompt focuses on ONE of the 8 Ладини purposes
    (`celestial_personal`, `earthly_personal`, …) and asks Sonnet to
    write ~250 words about THAT specific line — not a general overview.
    The summary `purposes` section still exists; these are the
    per-cell expansions for the DestinyPurposes UI block."""

    section_key = f"purpose_{purpose_key}"

    def builder(ctx: V3Context) -> tuple[str, int]:
        p = ctx.purposes[purpose_key]
        left, right, total = p.key
        arcana_blocks = "\n\n".join(
            _arc_brief(
                ctx.arcana[n],
                sections=("essence", "mission", "shadow"),
            )
            for n in dict.fromkeys([left, right, total])
        )
        return (
            _header(ctx, section_key)
            + f"Раздел про одно конкретное предназначение — «{p.name}».\n\n"
            f"Формула: аркан {left} ({_name(left)}) + аркан {right} "
            f"({_name(right)}) = аркан {total} ({_name(total)}).\n\n"
            f"Контекст этой линии: {_PURPOSE_CONTEXT_HINTS[purpose_key]}\n\n"
            f"Справка по аркaнaм формулы:\n\n{arcana_blocks}\n\n"
            "Напиши 220-280 слов ИМЕННО про это предназначение. Не обобщай "
            "и не сравнивай с другими линиями (для них есть отдельные "
            "разделы). Структура:\n"
            f"1) Что даёт сложение арканов {left} и {right} через итог "
            f"{total} ({_name(total)}).\n"
            "2) Как это проявляется в жизни читателя по этой конкретной "
            "линии (учитывай пол и тон обращения).\n"
            "3) Одна конкретная подсказка/практика, чтобы прожить это "
            "предназначение сильнее."
        ), 250

    return builder


def _prompt_purposes(ctx: V3Context) -> tuple[str, int]:
    """8 предназначений — ТОЛЬКО синтез-спираль (интро к блоку).
    Пораздельный разбор каждого из 8 живёт на страницах Предн.1–8 и в
    сводной таблице — здесь его НЕ повторяем."""
    p = ctx.purposes
    cp = p["wholeness_personal"].key[2]   # целостное личное
    wl = p["wholeness_lineage"].key[2]    # соц. реализация
    pd = p["personal_divine"].key[2]      # высшее я
    dm = p["divine_mission"].key[2]       # миссия
    return (
        _header(ctx, "purposes")
        + "Восемь предназначений — карта смысловых задач от рождения до миссии. "
        "Это вводный разворот к блоку: каждое из восьми подробно раскрыто на "
        "отдельных страницах далее, а числовая композиция — в сводной таблице. "
        "Поэтому ЗДЕСЬ задача другая — показать ЛОГИКУ всей восьмёрки как единой "
        "усиливающей спирали, НЕ пересказывая каждое предназначение отдельно.\n\n"
        "Опорные вершины спирали:\n"
        f"• Целостное личное: аркан {cp} ({_name(cp)}) — куда сходятся три личные задачи\n"
        f"• Социальная реализация: аркан {wl} ({_name(wl)}) — куда сходятся два рода\n"
        f"• Высшее «Я»: аркан {pd} ({_name(pd)}) — личное + родовое\n"
        f"• Божественная миссия: аркан {dm} ({_name(dm)}) — итог для людей\n\n"
        "Напиши 200-240 слов одним связным текстом: как три личных "
        "предназначения собираются в Целостное личное, как два рода — в "
        "Социальную реализацию, как эти две вершины складываются в Высшее «Я» и "
        "как всё вместе разворачивается в Божественную миссию. Без списков, без "
        "пересказа каждого предназначения, без вывода всех восьми формул. Только "
        "смысловая связь — зачем эта спираль и куда она ведёт."
    ), 220


def _prompt_power_code(ctx: V3Context) -> tuple[str, int]:
    """Код силы — centers.holistic (C + родовой центр)."""
    pos = ctx.positions
    centers = pos["centers"]
    holistic = centers["holistic"]
    lineage = centers["lineage"]
    center = centers["personal"]
    nums = [center, lineage, holistic]
    refs = "\n\n".join(
        _arc_brief(ctx.arcana[n], sections=("essence", "mission", "activities"))
        for n in dict.fromkeys(nums)
    )
    return (
        _header(ctx, "power_code")
        + "Код силы — что выкристаллизовывается, когда читатель синтезирует "
        "свой центр (C) с энергией рода (центральная диагональ). Это его "
        "«главный инструмент влияния».\n\n"
        f"• Центр (C): аркан {center} ({_name(center)})\n"
        f"• Родовой центр: аркан {lineage} ({_name(lineage)})\n"
        f"• Код силы (С + родовой центр): аркан {holistic} ({_name(holistic)})\n\n"
        f"Справка:\n\n{refs}\n\n"
        "Напиши 250-320 слов о том, в чём проявляется код силы, в каких "
        "ситуациях он раскрывается и через что блокируется."
    ), 300


def _prompt_health(ctx: V3Context) -> tuple[str, int]:
    """Здоровье — чакры sky vs earth, баланс."""
    pos = ctx.positions
    sky = pos["chakras"]["sky"]
    earth = pos["chakras"]["earth"]
    # bottom→top order so the prompt reads grounded-first.
    chakra_seq: list[tuple[str, str]] = [
        ("Муладхара",   "muladhara"),
        ("Свадхистана", "svadhisthana"),
        ("Манипура",    "manipura"),
        ("Анахата",     "anahata"),
        ("Вишудха",     "vishuddha"),
        ("Аджна",       "adjna"),
        ("Сахасрара",   "sahasrara"),
    ]
    nums = list(dict.fromkeys(
        [sky[k] for _, k in chakra_seq] + [earth[k] for _, k in chakra_seq]
    ))[:6]
    refs = "\n\n".join(
        _arc_brief(ctx.arcana[n], sections=("essence", "healing"))
        for n in nums
    )
    chakra_lines = []
    for ru, key in chakra_seq:
        s = sky[key]
        e = earth[key]
        chakra_lines.append(f"• {ru}: Небо {s} ({_name(s)}) | Земля {e} ({_name(e)})")
    return (
        _header(ctx, "health")
        + "Здоровье — общая энергетическая карта по 7 чакрам. Слева Небесная "
        "сторона (психо-эмоциональное измерение), справа Земная (физическое "
        "проявление). Чакра с большим перекосом — место, требующее внимания.\n\n"
        + "\n".join(chakra_lines)
        + f"\n\nСправка по самым нагруженным арканам:\n\n{refs}\n\n"
        "Напиши 250-320 слов про общую картину чакр: какие хорошо снабжены, "
        "какие в зоне внимания, как поддерживать баланс. БЕЗ медицинских "
        "диагнозов — только про энергетику и образ жизни."
    ), 300


def _prompt_year_energy(ctx: V3Context) -> tuple[str, int]:
    """Энергия года — current + upcoming."""
    ye = ctx.year_energy
    refs = "\n\n".join(
        _arc_brief(ctx.arcana[n], sections=("essence", "mission", "activities"))
        for n in dict.fromkeys([ye.current, ye.upcoming])
    )
    return (
        _header(ctx, "year_energy")
        + "Энергия года — какой аркан задаёт тон твоему текущему жизненному "
        "году (от прошлого ДР до следующего) и какой придёт после следующего "
        "Дня рождения.\n\n"
        f"• Текущий год — аркан {ye.current} ({_name(ye.current)})\n"
        f"• Следующий год — аркан {ye.upcoming} ({_name(ye.upcoming)})\n\n"
        f"Справка:\n\n{refs}\n\n"
        "ЯЗЫК: НЕ называй год классическим таро-именем аркана и его "
        "склонениями («Год Луны», «энергия Шута», «Год Дьявола», «Башня»). "
        "Если хочешь дать году имя — называй каноном: «Год Магии», «Год "
        "Уровневой свободы». А лучше — говори просто «текущий год», «этот год»\n\n"
        "Напиши 320-400 слов: 1) тема текущего года и через что её прожить; "
        "2) на чём можно споткнуться; 3) короткий переход — что приносит "
        "следующий год и к чему готовиться. Без точных дат и предсказаний "
        "событий — только энергетика."
    ), 380


# ── Registry ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SectionSpec:
    key: str
    title: str
    prompt: Callable[[V3Context], tuple[str, int]]   # → (user_prompt, target_words)
    # Conceptual group for ordered counters in the PDF eyebrow.
    # "main"    — 15 narrative sections, render as «Раздел NN из 15»
    # "purpose" —  8 предназначений, render as «Предназначение N из 8»
    group: str = "main"


SECTIONS: list[SectionSpec] = [
    SectionSpec("visitka",       SECTION_TITLES["visitka"],       _prompt_visitka),
    SectionSpec("drk",           SECTION_TITLES["drk"],           _prompt_drk),
    # higher_self / soul_tasks / realization removed — their content
    # was 1:1 with the dedicated purpose_* deep dives that follow.
    # The 12 narrative sections now form group="main"; purpose_* the 8 deep dives.
    SectionSpec("karmic_tail",   SECTION_TITLES["karmic_tail"],   _prompt_karmic_tail),
    SectionSpec("relationships", SECTION_TITLES["relationships"], _prompt_relationships),
    SectionSpec("money",         SECTION_TITLES["money"],         _prompt_money),
    SectionSpec("harmonization", SECTION_TITLES["harmonization"], _prompt_harmonization),
    SectionSpec("talents",       SECTION_TITLES["talents"],       _prompt_talents),
    SectionSpec("anahata",       SECTION_TITLES["anahata"],       _prompt_anahata),
    SectionSpec("purposes",      SECTION_TITLES["purposes"],      _prompt_purposes),
    SectionSpec("power_code",    SECTION_TITLES["power_code"],    _prompt_power_code),
    SectionSpec("health",        SECTION_TITLES["health"],        _prompt_health),
    SectionSpec("year_energy",   SECTION_TITLES["year_energy"],   _prompt_year_energy),
    # 8 per-purpose deep-dives — driven by the same `purposes` dict on
    # V3Context, registered as separate sections so each gets its own
    # Sonnet call and its own cached row. Marked group="purpose" so the
    # PDF eyebrow renders «Предназначение N из 8» instead of continuing
    # the «Раздел NN из 15» series.
    *[
        SectionSpec(
            f"purpose_{k}",
            SECTION_TITLES[f"purpose_{k}"],
            _make_purpose_prompt(k),
            group="purpose",
        )
        for k in (
            "celestial_personal",
            "earthly_personal",
            "wholeness_personal",
            "father_lineage",
            "mother_lineage",
            "wholeness_lineage",
            "personal_divine",
            "divine_mission",
        )
    ],
]

SECTIONS_BY_KEY: dict[str, SectionSpec] = {s.key: s for s in SECTIONS}

# Section keys for the 8 per-purpose deep-dives — used by the
# DestinyPurposes UI block to look up content per cell.
PURPOSE_SECTION_KEYS: tuple[str, ...] = (
    "purpose_celestial_personal",
    "purpose_earthly_personal",
    "purpose_wholeness_personal",
    "purpose_father_lineage",
    "purpose_mother_lineage",
    "purpose_wholeness_lineage",
    "purpose_personal_divine",
    "purpose_divine_mission",
)


# ── LLM call + DB cache ─────────────────────────────────────────────────────


def _max_tokens_for(target_words: int) -> int:
    # ~2.5 tokens per Russian word, +50% headroom for headings/lists.
    return max(1200, int(target_words * 4))


async def _call_llm(client: Any, system: str, user: str, target_words: int) -> str:
    async with llm_semaphore:
        msg = await client.messages.create(
            model=MODEL_V3,
            max_tokens=_max_tokens_for(target_words),
            temperature=0.6,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    return "".join(b.text for b in msg.content if hasattr(b, "text")).strip()


async def _generate_one(
    client: Any, spec: SectionSpec, ctx: V3Context,
) -> tuple[str, str, int]:
    """Returns (section_key, content, elapsed_ms). Raises on LLM error
    so the caller can decide whether to retry or fall back per-section.

    Runs the V3 polish pipeline (canonical arcana names, leading-service-
    word strip, code fence + stray-asterisk cleanup) BEFORE caching, so
    we never store dirty content. See ``text_fix.polish_section_text``.
    """
    from services.destiny_matrix.text_fix import polish_section_text

    t0 = time.monotonic()
    user_prompt, target = spec.prompt(ctx)
    content = await _call_llm(client, _BASE_SYSTEM, user_prompt, target)
    content, stats = polish_section_text(content)
    elapsed = int((time.monotonic() - t0) * 1000)
    if any(stats.values()):
        log.info(
            "v3.section.polished",
            section_key=spec.key,
            arcana_fixes=stats.get("arcana_name_mismatch", 0),
            preamble_strip=stats.get("leading_service_word", 0),
            code_fence=stats.get("code_fence", 0),
            stray_asterisk=stats.get("stray_asterisk", 0),
        )
    return spec.key, content, elapsed


async def _upsert(
    session: AsyncSession,
    *,
    user_id: int,
    birth_date: date,
    gender: str,
    section: str,
    content: str,
) -> None:
    stmt = pg_insert(DestinyInterpretationV3).values(
        user_id=user_id,
        birth_date=birth_date,
        gender=gender,
        section=section,
        content=content,
        model=MODEL_V3,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "birth_date", "gender", "section"],
        set_=dict(content=stmt.excluded.content, model=stmt.excluded.model),
    )
    await session.execute(stmt)


async def load_cached_sections(
    session: AsyncSession,
    *,
    user_id: int,
    birth_date: date,
    gender: str,
) -> dict[str, str]:
    rows = await session.execute(
        select(DestinyInterpretationV3).where(
            DestinyInterpretationV3.user_id == user_id,
            DestinyInterpretationV3.birth_date == birth_date,
            DestinyInterpretationV3.gender == gender,
        )
    )
    return {r.section: r.content for r in rows.scalars()}


def _anthropic_client() -> Any:
    import anthropic
    return anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


async def regenerate_sections(
    session: AsyncSession,
    *,
    ctx: V3Context,
    keys: list[str] | None = None,
) -> dict[str, str]:
    """Run the LLM for the requested section keys (or all 15), upsert
    each result independently, and return the dict. Sections that fail
    are skipped — others still get cached so the user can retry just
    the failing ones."""
    if not settings.ANTHROPIC_API_KEY:
        log.warning("v3_interpreter: ANTHROPIC_API_KEY missing — returning empty")
        return {}

    specs = (
        [SECTIONS_BY_KEY[k] for k in keys if k in SECTIONS_BY_KEY]
        if keys else list(SECTIONS)
    )
    if not specs:
        return {}

    client = _anthropic_client()
    coros: list[Awaitable[tuple[str, str, int]]] = [
        _generate_one(client, spec, ctx) for spec in specs
    ]
    results: dict[str, str] = {}
    for fut in asyncio.as_completed(coros):
        try:
            key, content, elapsed = await fut
        except Exception as e:  # noqa: BLE001
            log.warning("v3_interpreter section failed: %s", e)
            continue
        results[key] = content
        await _upsert(
            session,
            user_id=ctx.user_id,
            birth_date=ctx.birth_date,
            gender=ctx.gender,
            section=key,
            content=content,
        )
        log.info("v3_interpreter section=%s elapsed_ms=%d", key, elapsed)
    await session.commit()
    return results


async def get_or_generate(
    session: AsyncSession,
    *,
    ctx: V3Context,
    force_keys: list[str] | None = None,
) -> dict[str, str]:
    """Hybrid loader: returns cached rows + generates anything missing.

    `force_keys` re-rolls those sections even if cached (used by the
    "обновить раздел" button in the UI)."""
    cached = await load_cached_sections(
        session,
        user_id=ctx.user_id,
        birth_date=ctx.birth_date,
        gender=ctx.gender,
    )
    needed: list[str] = []
    if force_keys:
        needed.extend(k for k in force_keys if k in SECTIONS_BY_KEY)
    needed.extend(s.key for s in SECTIONS if s.key not in cached and s.key not in needed)

    if needed:
        fresh = await regenerate_sections(session, ctx=ctx, keys=needed)
        cached.update(fresh)
    return cached
