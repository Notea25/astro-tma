#!/usr/bin/env python3
"""Generate karmic-tail programs via Sonnet 4 and seed `karmic_programs`.

For every unique bottom-axis triple ``(bottom, bottom_1, bottom_2)`` that
can occur on a real birth date 1950-2030, asks Sonnet to write a
named program ({name, description, manifestations, how_to_heal}) in the
voice of a practicing Ладини master. Reference example "19-22-3
«Нерождённое дитя»" is shown to the model as canon style/format.

Idempotent: ON CONFLICT DO UPDATE. Re-running tries again for any keys
that previously errored or look unfinished. Use ``--missing-only`` to
skip keys that already have a non-stub `name`. Use ``--dry-run`` to
print the enumeration without calling the LLM.

Cost: 26 calls × ~1800 input + ~500 output tokens at Sonnet rates ≈
$0.30-0.50 total. Wall-clock ~3-5 minutes.

Run on prod:
    docker compose exec backend python /app/scripts/seed_karmic_programs.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from core.settings import settings  # noqa: E402
from db.database import AsyncSessionLocal  # noqa: E402
from db.models import ArcanaBase, KarmicProgram  # noqa: E402
from services.destiny_matrix.calculator import reduce  # noqa: E402

_MODEL = "claude-sonnet-4-5-20250929"
_REFERENCE_KEY = "19-22-3"
_REFERENCE = {
    "key": _REFERENCE_KEY,
    "name": "Нерождённое дитя",
    "description": (
        "В прошлом воплощении душа могла не родиться (не доношенная "
        "беременность, аборт у матери) или уйти из тела очень рано — "
        "в раннем детстве, до 7-10 лет. Альтернативный сценарий: душа "
        "обладала большими деньгами, использовала их в корыстных целях, "
        "прожив разгульную, поверхностную жизнь. В том и в другом "
        "случае задача не была пройдена — отсюда сильная привязанность "
        "к матери, поиск материнской любви в партнёре, желание "
        "успеть в этой жизни всё, страх не успеть."
    ),
    "manifestations": (
        "В этой жизни проявляется как очень сильная привязанность к "
        "матери — либо до уровня созависимости, либо как поиск "
        "материнской любви в партнёре. Внутренний ребёнок не до конца "
        "исцелён — отсюда инфантильность, бегство от ответственности, "
        "желание «оставаться ребёнком» подольше. Может проявиться "
        "тема абортов (своих или у близких), сложные решения о "
        "рождении детей. Сильное ощущение «не успеваю» — хочется "
        "всё попробовать, всё успеть, объять необъятное. "
        "Эгоизм «жить только для себя» как защита от того что "
        "не дополучил."
    ),
    "how_to_heal": (
        "1. Восстановить отношения с матерью — исключить ссоры, "
        "обиды, держать тёплый контакт.\n"
        "2. Исключить аборты в своей жизни, не осуждать женщин "
        "сделавших такой выбор.\n"
        "3. Работать с внутренним ребёнком — но в здоровом ключе, "
        "не через инфантильность. Радовать его, но из позиции "
        "взрослого.\n"
        "4. Если есть знание/контакт с детьми — взять на себя "
        "ответственную роль (благотворительность, работа в детских "
        "сферах, помощь племянникам).\n"
        "5. Воспитывать в себе щедрость — делать подарки себе и "
        "близким без повода. Тренировать ощущение изобилия.\n"
        "6. Учиться говорить «да» новым возможностям — но не из "
        "«надо успеть всё», а из «я доверяю своему пути»."
    ),
}

_SYSTEM_PROMPT = """Ты — практикующий мастер Матрицы Судьбы с глубоким \
пониманием кармической методологии школы Натальи Ладини.

Твоя задача — описать кармическую программу из трёх арканов
(нижняя ось матрицы) в каноническом формате.

ПРИНЦИПЫ:
- Программа описывает что было в прошлом воплощении + как это
  проявляется сейчас + как прорабатывать
- Стиль — прямой, конкретный, как разговор с человеком на «ты»
- Никаких эзотерических штампов («высшее служение», «вселенский поток»)
- Никаких диагнозов и предсказаний
- Конкретные действия в how_to_heal — пронумерованным списком

СТРУКТУРА ВЫХОДА — строго JSON:
{
  "key": "<номер_1>-<номер_2>-<номер_3>",
  "name": "<2-4 слова, образное название программы>",
  "description": "<2-3 предложения про прошлое воплощение>",
  "manifestations": "<3-5 предложений про текущие проявления>",
  "how_to_heal": "<нумерованный список из 5-7 пунктов>"
}

ВАЖНО: name должно быть запоминающимся, образным — не описанием.
Хорошо: «Нерождённое дитя», «Сирота», «Изгнанник», «Зависимый король».
Плохо: «Программа отвержения родителей», «Кармический долг любви».
"""

_USER_TEMPLATE = """Опиши кармическую программу с ключом {key}.

Арканы программы:
- Аркан {a1} ({a1_name}) — главная нота, общая характеристика прошлого
- Аркан {a2} ({a2_name}) — детализация прошлого, дополнительный слой
- Аркан {a3} ({a3_name}) — пересечение с центром (как это в текущей жизни)

Описания арканов:

АРКАН {a1} — {a1_name}
Суть: {a1_essence}
Тень: {a1_shadow}

АРКАН {a2} — {a2_name}
Суть: {a2_essence}
Тень: {a2_shadow}

АРКАН {a3} — {a3_name}
Суть: {a3_essence}
Тень: {a3_shadow}

Пример формата (программа 19-22-3 «Нерождённое дитя»):
{reference}

Дай результат ТОЛЬКО JSON-объектом, без обёрток markdown."""


def _enumerate_keys() -> list[tuple[int, int, int]]:
    """All unique (bottom, bottom_1, bottom_2) triples that occur on
    valid birth dates 1950-2030. Math mirrors `calculator_site.py`."""
    combos: set[tuple[int, int, int]] = set()
    for year in range(1950, 2031):
        for month in range(1, 13):
            for day in range(1, 32):
                try:
                    date(year, month, day)
                except ValueError:
                    continue
                d = reduce(day)
                m = reduce(month)
                y = reduce(sum(int(c) for c in str(year)))
                b = reduce(d + m + y)
                c = reduce(d + m + y + b)
                mid = reduce(b + c)          # bottom_2
                near = reduce(b + mid)       # bottom_1
                combos.add((b, near, mid))
    return sorted(combos)


async def _load_arcana(session) -> dict[int, dict[str, str]]:
    rows = await session.execute(select(ArcanaBase))
    return {
        r.num: {"name": r.name_ru, "essence": r.essence, "shadow": r.shadow}
        for r in rows.scalars()
    }


def _build_user_prompt(
    key: tuple[int, int, int], arcana: dict[int, dict[str, str]]
) -> str:
    a1, a2, a3 = key
    return _USER_TEMPLATE.format(
        key=f"{a1}-{a2}-{a3}",
        a1=a1, a1_name=arcana[a1]["name"],
        a2=a2, a2_name=arcana[a2]["name"],
        a3=a3, a3_name=arcana[a3]["name"],
        a1_essence=arcana[a1]["essence"][:600],
        a1_shadow=arcana[a1]["shadow"][:400],
        a2_essence=arcana[a2]["essence"][:600],
        a2_shadow=arcana[a2]["shadow"][:400],
        a3_essence=arcana[a3]["essence"][:600],
        a3_shadow=arcana[a3]["shadow"][:400],
        reference=json.dumps(_REFERENCE, ensure_ascii=False, indent=2),
    )


def _parse(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


async def _generate_one(
    client: Any, key: tuple[int, int, int], arcana: dict[int, dict[str, str]],
) -> dict[str, Any] | None:
    """Run Sonnet for one program. Returns the parsed dict or None on
    a parse / API failure."""
    if key == (19, 22, 3):
        return dict(_REFERENCE)

    from services.llm_pool import llm_semaphore

    user_prompt = _build_user_prompt(key, arcana)
    async with llm_semaphore:
        message = await client.messages.create(
            model=_MODEL,
            max_tokens=2000,
            temperature=0.7,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    raw = "".join(b.text for b in message.content if hasattr(b, "text"))
    parsed = _parse(raw)
    if not parsed:
        return None
    # Enforce the key (model sometimes drops it or formats differently)
    parsed["key"] = f"{key[0]}-{key[1]}-{key[2]}"
    return parsed


async def _upsert(session, program: dict[str, Any]) -> None:
    stmt = pg_insert(KarmicProgram).values(
        key=program["key"],
        name=str(program.get("name", "")).strip(),
        description=str(program.get("description", "")).strip(),
        manifestations=str(program.get("manifestations", "")).strip(),
        how_to_heal=str(program.get("how_to_heal", "")).strip(),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_=dict(
            name=stmt.excluded.name,
            description=stmt.excluded.description,
            manifestations=stmt.excluded.manifestations,
            how_to_heal=stmt.excluded.how_to_heal,
        ),
    )
    await session.execute(stmt)
    await session.commit()


async def _existing_keys(session) -> set[str]:
    rows = await session.execute(select(KarmicProgram.key))
    return {row[0] for row in rows.all() if row[0]}


async def main(*, dry_run: bool = False, missing_only: bool = False) -> None:
    keys = _enumerate_keys()
    print(f"Found {len(keys)} unique karmic-tail triples", flush=True)
    if dry_run:
        for k in keys:
            print(f"  {k[0]:2d}-{k[1]:2d}-{k[2]:2d}", flush=True)
        return

    if not settings.ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY missing — aborting", flush=True)
        sys.exit(1)

    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async with AsyncSessionLocal() as session:
        existing: set[str] = set()
        if missing_only:
            existing = await _existing_keys(session)
            print(f"Already in DB: {len(existing)} keys", flush=True)

        arcana = await _load_arcana(session)
        if len(arcana) < 22:
            print(
                f"⚠️  arcana_base has only {len(arcana)}/22 rows — "
                "run seed_arcana_base.py first",
                flush=True,
            )
            sys.exit(1)

        for idx, key in enumerate(keys, 1):
            key_str = f"{key[0]}-{key[1]}-{key[2]}"
            if missing_only and key_str in existing:
                print(f"  [{idx:02d}/{len(keys)}] {key_str} — skipped", flush=True)
                continue
            print(f"  [{idx:02d}/{len(keys)}] {key_str} …", end=" ", flush=True)
            try:
                program = await _generate_one(client, key, arcana)
            except Exception as e:  # noqa: BLE001
                print(f"ERROR: {e}", flush=True)
                continue
            if not program or not program.get("name"):
                print("SKIPPED (parse fail)", flush=True)
                continue
            await _upsert(session, program)
            print(f"OK — «{program['name']}»", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(
        main(
            dry_run="--dry-run" in args,
            missing_only="--missing-only" in args,
        )
    )
