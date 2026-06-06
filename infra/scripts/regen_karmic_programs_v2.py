#!/usr/bin/env python3
"""Regenerate karmic-tail programs from the canonical JSON via Sonnet.

This is the V2 version that replaces ``seed_karmic_programs.py``:
- Input source is now an external file (``content/karmic_programs_canonical.json``),
  not hard-coded inside the script.
- Sonnet only EXPANDS the short ``proven_*`` lines into full text in the
  voice of the reference program; it doesn't invent the program itself.
- Key format changed: from ``f"{bottom}-{bottom_1}-{bottom_2}"`` (B → near
  corner → mid) to ``f"{bottom_2}-{bottom_1}-{bottom}"`` (mid → near corner
  → B). Canonical reading order is from the centre to the corner of the
  octagram. The reference key flipped from ``19-22-3`` to ``3-22-19``.
- Truncates the table first because the old rows are at the wrong keys
  and have content that doesn't match the new canonical names.

Run on prod:
    docker compose exec backend python /app/scripts/regen_karmic_programs_v2.py

Flags:
    --dry-run        list the 26 keys + names without calling the LLM
    --skip-truncate  don't TRUNCATE first; only upsert (faster for retries)

Cost: 26 Sonnet calls × ~1500 in + ~1000 out tokens ≈ $0.30-0.60 total.
Wall-clock ~3-5 min sequentially.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from core.settings import settings  # noqa: E402
from db.database import AsyncSessionLocal  # noqa: E402
from db.models import KarmicProgram  # noqa: E402

_MODEL = "claude-sonnet-4-5-20250929"
_CANONICAL_JSON = (
    Path(__file__).resolve().parents[2] / "content" / "karmic_programs_canonical.json"
)

_REFERENCE_KEY = "3-22-19"
_REFERENCE_FULL = {
    "key": _REFERENCE_KEY,
    "name": "Нерождённое дитя",
    "description": (
        "В прошлом воплощении душа могла не родиться (недоношенная "
        "беременность, аборт у матери) или уйти из тела очень рано — "
        "в раннем детстве, до 7-10 лет. Альтернативный сценарий: душа "
        "обладала большими деньгами, использовала их в корыстных целях, "
        "прожив разгульную, поверхностную жизнь. В обоих случаях задача "
        "не была пройдена — отсюда сильная привязанность к матери, поиск "
        "материнской любви в партнёре, желание успеть в этой жизни всё, "
        "страх не успеть."
    ),
    "manifestations": (
        "В этой жизни проявляется как очень сильная привязанность к "
        "матери — либо до уровня созависимости, либо как поиск "
        "материнской любви в партнёре. Внутренний ребёнок не до конца "
        "исцелён — отсюда инфантильность, бегство от ответственности, "
        "желание «оставаться ребёнком» подольше. Может проявиться тема "
        "абортов (своих или у близких), сложные решения о рождении детей. "
        "Сильное ощущение «не успеваю» — хочется всё попробовать. Эгоизм "
        "«жить только для себя» как защита от того что не дополучил."
    ),
    "how_to_heal": (
        "1. Восстановить отношения с матерью — исключить ссоры, обиды, "
        "держать тёплый контакт.\n"
        "2. Исключить аборты в своей жизни, не осуждать женщин сделавших "
        "такой выбор.\n"
        "3. Работать с внутренним ребёнком — но в здоровом ключе, не через "
        "инфантильность. Радовать его, но из позиции взрослого.\n"
        "4. Если есть знание/контакт с детьми — взять на себя ответственную "
        "роль (благотворительность, работа в детских сферах, помощь "
        "племянникам).\n"
        "5. Воспитывать в себе щедрость — делать подарки себе и близким "
        "без повода. Тренировать ощущение изобилия.\n"
        "6. Учиться говорить «да» новым возможностям — но не из «надо "
        "успеть всё», а из «я доверяю своему пути»."
    ),
}

_SYSTEM_PROMPT = """Ты — практикующий мастер Матрицы Судьбы.

Тебе дана КОРОТКАЯ каноническая программа кармического хвоста.
Твоя задача — РАЗВЕРНУТЬ её в полный текст из трёх блоков:
description, manifestations, how_to_heal.

Не выдумывай новую программу — разворачивай то что дано в кратком
описании. Сохрани её суть, тематику, тональность. Просто пиши
подробнее, конкретнее, в живом стиле.

ВАЖНО:
- Стиль — на «ты», тёплый, прямой, как разговор с человеком
- description: 2-3 предложения про прошлое воплощение
- manifestations: 3-5 предложений про конкретные сценарии в этой жизни
- how_to_heal: нумерованный список из 5-7 пунктов
- Никаких эзотерических штампов («высшее служение», «вселенский поток»)
- Никаких диагнозов и предсказаний
- Никаких упоминаний камней
- Тон без пугалок: «карма наказывает», «расплата» — НЕ использовать

СТРУКТУРА ОТВЕТА — строго JSON, без markdown-обёрток:
{
  "key": "<тот же ключ что в задании>",
  "name": "<сохранить из задания>",
  "description": "<2-3 предложения>",
  "manifestations": "<3-5 предложений>",
  "how_to_heal": "<нумерованный список через \\n>"
}
"""


def _build_user_prompt(key: str, program: dict[str, Any]) -> str:
    return f"""Разверни эту программу в полный текст.

КАНОНИЧЕСКАЯ ПРОГРАММА ДЛЯ ТЕБЯ (это твой ИСТОЧНИК — следуй ей):
- Ключ: {key}
- Название: «{program['name']}»
- Что проявляется в этой жизни: {program['proven_manifestations']}
- Как прорабатывать: {program['proven_how_to_heal']}
- Путь в плюс: {program['proven_growth']}

────────────────────────────────────────────────────
ЭТАЛОН СТИЛЯ — программа «Нерождённое дитя» (3-22-19):
────────────────────────────────────────────────────

{json.dumps(_REFERENCE_FULL, ensure_ascii=False, indent=2)}

────────────────────────────────────────────────────

Теперь напиши программу «{program['name']}» ({key}) в этом же формате и стиле.
Сохрани название, сохрани суть, разверни в полные тексты.
JSON, без обёрток markdown.
"""


def _parse(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
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


async def _expand_one(
    client: Any, key: str, program: dict[str, Any],
) -> dict[str, Any] | None:
    """Run Sonnet on one canonical program. Returns parsed dict or None."""
    if program.get("is_reference"):
        return dict(_REFERENCE_FULL)

    from services.llm_pool import llm_semaphore

    user_prompt = _build_user_prompt(key, program)
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
    parsed["key"] = key  # canonical key wins
    parsed["name"] = program["name"]  # canonical name wins
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


def _load_canonical() -> dict[str, dict[str, Any]]:
    raw = json.loads(_CANONICAL_JSON.read_text(encoding="utf-8"))
    return raw["programs"]


async def main(*, dry_run: bool = False, skip_truncate: bool = False) -> None:
    canonical = _load_canonical()
    print(f"Loaded {len(canonical)} canonical programs", flush=True)

    if dry_run:
        for key, prog in sorted(canonical.items()):
            ref = " (reference)" if prog.get("is_reference") else ""
            print(f"  {key:>10}  «{prog['name']}»{ref}", flush=True)
        return

    if not settings.ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY missing — aborting", flush=True)
        sys.exit(1)

    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async with AsyncSessionLocal() as session:
        if not skip_truncate:
            print("TRUNCATE karmic_programs …", flush=True)
            await session.execute(text("TRUNCATE TABLE karmic_programs"))
            await session.commit()

        for idx, (key, program) in enumerate(sorted(canonical.items()), 1):
            print(f"  [{idx:02d}/{len(canonical)}] {key:>10} …", end=" ", flush=True)
            try:
                expanded = await _expand_one(client, key, program)
            except Exception as e:  # noqa: BLE001
                print(f"ERROR: {e}", flush=True)
                continue
            if not expanded or not expanded.get("description"):
                print("SKIPPED (parse fail)", flush=True)
                continue
            await _upsert(session, expanded)
            print(f"OK — «{expanded['name']}»", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(
        main(
            dry_run="--dry-run" in args,
            skip_truncate="--skip-truncate" in args,
        )
    )
