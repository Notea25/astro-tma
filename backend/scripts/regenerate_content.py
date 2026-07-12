#!/usr/bin/env python3
"""Resume-safe production regeneration for safety-v1 generated content.

Dry run (no writes, no LLM calls):
    python scripts/regenerate_content.py --dry-run

Execute only after reviewing dry-run cost and creating a pg_dump:
    python scripts/regenerate_content.py --execute \
      --backup-file /backups/astro-before-safety-v1.dump \
      --confirm-version 2026-07-safety-v1
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# The regeneration contract explicitly caps LLM calls at two at a time.
os.environ["LLM_CONCURRENCY"] = "2"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from core.cache import cache_get, cache_set, close_redis, init_redis, key_natal
from core.settings import settings
from db.database import AsyncSessionLocal
from db.models import (
    DestinyInterpretationV3,
    DestinyMatrixInterpretation,
    DestinyMatrixReading,
    NatalChart,
    SynastryInterpretation,
    SynastryPairSummary,
    SynastryRequest,
    TarotCard,
    TarotReading,
    TransitInterpretation,
    User,
)
from services.astro.llm_interpreter import (
    generate_natal_mini_reading,
    generate_natal_reading,
)
from services.content_version import CONTENT_VERSION
from services.destiny_matrix.interpreter import generate_interpretation
from services.destiny_matrix.v3_interpreter import (
    get_or_generate,
    load_v3_context,
)
from services.tarot.interpreter import generate_spread_interpretation, is_supported_spread

TOKEN_ESTIMATES = {
    "natal": 25_200,
    "transit": 900,
    "synastry": 900,
    "synastry_summary": 900,
    "matrix_v2": 3_000,
    "matrix_v3_section": 1_600,
    "tarot": 2_400,
}


async def _count(session: Any, model: Any, *criteria: Any) -> int:
    return int(
        (
            await session.execute(select(func.count()).select_from(model).where(*criteria))
        ).scalar_one()
    )


async def inventory() -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        transit_current = {
            (row.transit_planet, row.natal_planet, row.aspect)
            for row in (
                await session.execute(
                    select(TransitInterpretation).where(
                        TransitInterpretation.content_version == CONTENT_VERSION
                    )
                )
            ).scalars()
        }
        transit_legacy = {
            (row.transit_planet, row.natal_planet, row.aspect)
            for row in (
                await session.execute(
                    select(TransitInterpretation).where(
                        TransitInterpretation.content_version != CONTENT_VERSION
                    )
                )
            ).scalars()
        }
        synastry_current = {
            (row.p1, row.p2, row.aspect)
            for row in (
                await session.execute(
                    select(SynastryInterpretation).where(
                        SynastryInterpretation.content_version == CONTENT_VERSION
                    )
                )
            ).scalars()
        }
        synastry_legacy = {
            (row.p1, row.p2, row.aspect)
            for row in (
                await session.execute(
                    select(SynastryInterpretation).where(
                        SynastryInterpretation.content_version != CONTENT_VERSION
                    )
                )
            ).scalars()
        }
        reading_count = await _count(session, DestinyMatrixReading)
        current_v3 = await _count(
            session,
            DestinyInterpretationV3,
            DestinyInterpretationV3.content_version == CONTENT_VERSION,
        )
        return {
            "natal": await _count(session, NatalChart),
            "transit": len(transit_legacy - transit_current),
            "synastry": len(synastry_legacy - synastry_current),
            "synastry_summary": await _count(
                session,
                SynastryPairSummary,
                SynastryPairSummary.content_version != CONTENT_VERSION,
            ),
            "matrix_v2": await _count(
                session,
                DestinyMatrixReading,
                ~select(DestinyMatrixInterpretation.id).where(
                    DestinyMatrixInterpretation.reading_id == DestinyMatrixReading.id,
                    DestinyMatrixInterpretation.content_version == CONTENT_VERSION,
                ).exists(),
            ),
            "matrix_v3_section": max(0, reading_count * 20 - current_v3),
            "tarot": await _count(session, TarotReading),
        }


def print_inventory(counts: dict[str, int]) -> None:
    total_tokens = sum(counts[key] * TOKEN_ESTIMATES[key] for key in TOKEN_ESTIMATES)
    print(f"Target content version: {CONTENT_VERSION}")
    print("Order: tarot static -> natal -> transit -> synastry -> matrix_v2 -> matrix_v3 -> horoscope caches")
    for key, count in counts.items():
        estimate = count * TOKEN_ESTIMATES.get(key, 0)
        print(f"  {key:18} records={count:5d} estimated_output_tokens={estimate:9d}")
    print(f"Estimated maximum output tokens: {total_tokens}")
    print("Create backup before execute, for example:")
    print("  pg_dump -Fc -d astro_tma -f /backups/astro-before-safety-v1.dump")


async def regenerate_tarot_static(session: Any) -> int:
    """Remove leaked markdown service headings without touching readings/cards_json."""
    rows = (await session.execute(select(TarotCard))).scalars().all()
    changed = 0
    for card in rows:
        for attr in ("upright_ru", "reversed_ru"):
            value = str(getattr(card, attr) or "")
            cleaned = "\n".join(
                line
                for line in value.splitlines()
                if not line.lstrip().startswith(("#", "🩺"))
            ).strip()
            if cleaned != value:
                setattr(card, attr, cleaned)
                changed += 1
    await session.commit()
    return changed


async def regenerate_natal(session: Any) -> int:
    from services.astro.natal import calculate_natal, chart_to_json

    rows = (
        await session.execute(select(User, NatalChart).join(NatalChart, NatalChart.user_id == User.id))
    ).all()
    done = 0
    for user, chart in rows:
        payload = await cache_get(key_natal(user.id))
        payload = payload if isinstance(payload, dict) else {}
        if payload.get("content_version") == CONTENT_VERSION:
            continue
        if user.birth_date and user.birth_tz:
            recalculated = calculate_natal(
                name=user.tg_first_name or "User",
                birth_dt=user.birth_date,
                lat=user.birth_lat or 0.0,
                lng=user.birth_lng or 0.0,
                tz_str=user.birth_tz,
                birth_time_known=user.birth_time_known,
            )
            chart.sun_sign = recalculated.sun.sign
            chart.moon_sign = recalculated.moon.sign
            chart.ascendant_sign = recalculated.ascendant_sign
            chart.chart_data = chart_to_json(recalculated)
            await session.commit()
        data = chart.chart_data or {}
        planets = {
            name: {**position, "house": position.get("house") if user.birth_time_known else None}
            for name, position in (data.get("planets") or {}).items()
        }
        asc = chart.ascendant_sign if user.birth_time_known else None
        gender = user.gender.value if user.gender else None
        reading = await generate_natal_reading(
            chart.sun_sign,
            chart.moon_sign,
            asc,
            planets,
            (data.get("aspects") or [])[:10],
            settings.LLM_API_KEY,
            gender,
            nodes=data.get("nodes"),
        )
        mini = await generate_natal_mini_reading(
            chart.sun_sign, chart.moon_sign, asc, settings.LLM_API_KEY, gender
        )
        await cache_set(
            key_natal(user.id),
            {
                **payload,
                "reading": reading,
                "mini_reading": mini,
                "reading_gender": gender,
                "mini_reading_gender": gender,
                "reading_version": 3,
                "mini_reading_version": 2,
                "content_version": CONTENT_VERSION,
            },
            settings.CACHE_TTL_NATAL,
        )
        done += 1
        print(f"natal {done}/{len(rows)} user={user.id}")
    return done


async def regenerate_transits(session: Any) -> int:
    from services.astro.aspect_policy import is_classic_planet
    from services.astro.transit_interpreter import _llm_batch

    rows = (
        await session.execute(
            select(TransitInterpretation).where(
                TransitInterpretation.content_version != CONTENT_VERSION
            )
        )
    ).scalars().all()
    current = {
        (row.transit_planet, row.natal_planet, row.aspect)
        for row in (
            await session.execute(
                select(TransitInterpretation).where(
                    TransitInterpretation.content_version == CONTENT_VERSION
                )
            )
        ).scalars()
    }
    triples = [
        (r.transit_planet, r.natal_planet, r.aspect)
        for r in rows
        if is_classic_planet(r.transit_planet) and is_classic_planet(r.natal_planet)
        and (r.transit_planet, r.natal_planet, r.aspect) not in current
    ]
    generated = await _llm_batch(triples, settings.LLM_API_KEY) if triples else {}
    for triple, text in generated.items():
        session.add(
            TransitInterpretation(
                transit_planet=triple[0],
                natal_planet=triple[1],
                aspect=triple[2],
                text_ru=text,
                content_version=CONTENT_VERSION,
            )
        )
    await session.commit()
    return len(generated)


async def regenerate_synastry(session: Any) -> int:
    from services.astro.aspect_policy import is_classic_planet
    from services.astro.synastry_interpreter import _llm_batch

    rows = (
        await session.execute(
            select(SynastryInterpretation).where(
                SynastryInterpretation.content_version != CONTENT_VERSION
            )
        )
    ).scalars().all()
    current = {
        (row.p1, row.p2, row.aspect)
        for row in (
            await session.execute(
                select(SynastryInterpretation).where(
                    SynastryInterpretation.content_version == CONTENT_VERSION
                )
            )
        ).scalars()
    }
    triples = [
        (r.p1, r.p2, r.aspect)
        for r in rows
        if is_classic_planet(r.p1) and is_classic_planet(r.p2)
        and (r.p1, r.p2, r.aspect) not in current
    ]
    generated = await _llm_batch(triples, settings.LLM_API_KEY) if triples else {}
    for triple, text in generated.items():
        session.add(
            SynastryInterpretation(
                p1=triple[0],
                p2=triple[1],
                aspect=triple[2],
                text_ru=text,
                content_version=CONTENT_VERSION,
            )
        )
    await session.commit()
    return len(generated)


async def regenerate_synastry_summaries(session: Any) -> int:
    from services.astro.aspect_policy import (
        is_classic_planet,
        natal_or_synastry_orb_limit,
    )
    from services.astro.synastry_interpreter import get_or_generate_pair_summary

    requests = (
        await session.execute(
            select(SynastryRequest).where(SynastryRequest.result_json.is_not(None))
        )
    ).scalars().all()
    done = 0
    for request in requests:
        data = request.result_json or {}
        aspects = [
            aspect
            for aspect in (data.get("aspects") or [])
            if is_classic_planet(str(aspect.get("p1_name", "")))
            and is_classic_planet(str(aspect.get("p2_name", "")))
            and float(aspect.get("orb", 99))
            <= natal_or_synastry_orb_limit(
                str(aspect.get("p1_name", "")), str(aspect.get("p2_name", ""))
            )
        ]
        if not aspects:
            continue
        initiator = await session.get(User, request.initiator_user_id)
        partner = (
            await session.get(User, request.partner_user_id)
            if request.partner_user_id
            else None
        )
        summary = await get_or_generate_pair_summary(
            session,
            initiator.tg_first_name if initiator else None,
            partner.tg_first_name if partner else data.get("partner_name"),
            aspects,
            settings.LLM_API_KEY,
        )
        if summary:
            request.result_json = {
                **data,
                "aspects": aspects,
                "total_aspects": len(aspects),
                "summary_ru": summary,
            }
            request.result_json.pop("scores", None)
            await session.commit()
            done += 1
    return done


async def regenerate_matrix_v2(session: Any) -> int:
    readings = (await session.execute(select(DestinyMatrixReading))).scalars().all()
    done = 0
    for reading in readings:
        existing = await session.scalar(
            select(DestinyMatrixInterpretation.id).where(
                DestinyMatrixInterpretation.reading_id == reading.id,
                DestinyMatrixInterpretation.content_version == CONTENT_VERSION,
            )
        )
        if existing:
            continue
        user = await session.get(User, reading.user_id)
        gender = user.gender.value if user and user.gender else None
        sections, model = await generate_interpretation(
            reading.positions,
            user.tg_first_name if user else None,
            settings.LLM_API_KEY,
            gender,
        )
        if model == "fallback":
            continue
        session.add(
            DestinyMatrixInterpretation(
                reading_id=reading.id,
                sections=sections,
                model=model,
                gender_used=gender,
                content_version=CONTENT_VERSION,
            )
        )
        await session.commit()
        done += 1
    return done


async def regenerate_matrix_v3(session: Any) -> int:
    readings = (await session.execute(select(DestinyMatrixReading))).scalars().all()
    before = await _count(
        session,
        DestinyInterpretationV3,
        DestinyInterpretationV3.content_version == CONTENT_VERSION,
    )
    for reading in readings:
        user = await session.get(User, reading.user_id)
        if not user:
            continue
        gender = user.gender.value if user.gender else "any"
        ctx = await load_v3_context(
            session,
            user_id=user.id,
            birth_date=reading.birth_date,
            gender=gender,
            name=user.tg_first_name,
            positions=reading.positions,
        )
        await get_or_generate(session, ctx=ctx)
    after = await _count(
        session,
        DestinyInterpretationV3,
        DestinyInterpretationV3.content_version == CONTENT_VERSION,
    )
    return after - before


async def regenerate_tarot_interpretations(session: Any) -> int:
    readings = (await session.execute(select(TarotReading))).scalars().all()
    done = 0
    for reading in readings:
        if not is_supported_spread(reading.spread_type):
            continue
        from core.cache import key_tarot_interpret

        if await cache_get(key_tarot_interpret(reading.id)) is not None:
            continue
        drawn = sorted(reading.cards_json or [], key=lambda item: item["position"])
        cards = {
            card.id: card
            for card in (
                await session.execute(
                    select(TarotCard).where(TarotCard.id.in_([x["card_id"] for x in drawn]))
                )
            ).scalars()
        }
        prompt_cards = []
        for item in drawn:
            card = cards.get(item["card_id"])
            if not card:
                continue
            reversed_flag = bool(item.get("reversed"))
            prompt_cards.append(
                {
                    "card_id": card.id,
                    "name_ru": card.name_ru,
                    "reversed": reversed_flag,
                    "meaning_ru": card.reversed_ru if reversed_flag else card.upright_ru,
                    "keywords_ru": card.keywords_ru or [],
                }
            )
        if not prompt_cards:
            continue
        user = await session.get(User, reading.user_id)
        gender = user.gender.value if user and user.gender else None
        result = await generate_spread_interpretation(
            reading.spread_type, prompt_cards, settings.LLM_API_KEY, gender
        )
        await cache_set(
            key_tarot_interpret(reading.id),
            {**result, "reading_id": reading.id, "spread_type": reading.spread_type, "gender_used": gender},
            settings.CACHE_TTL_TAROT_INTERPRET,
        )
        done += 1
    return done


async def execute() -> None:
    if not settings.LLM_API_KEY:
        raise SystemExit("LLM_API_KEY is required for --execute")
    await init_redis()
    try:
        async with AsyncSessionLocal() as session:
            print("tarot_static:", await regenerate_tarot_static(session))
            print("tarot_interpretations:", await regenerate_tarot_interpretations(session))
            print("natal:", await regenerate_natal(session))
            print("transit:", await regenerate_transits(session))
            print("synastry:", await regenerate_synastry(session))
            print("synastry_summary:", await regenerate_synastry_summaries(session))
            print("matrix_v2:", await regenerate_matrix_v2(session))
            print("matrix_v3:", await regenerate_matrix_v3(session))
            print("Horoscope caches use versioned keys and will refill on demand.")
    finally:
        await close_redis()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--backup-file", type=Path)
    parser.add_argument("--confirm-version")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    counts = await inventory()
    print_inventory(counts)
    if args.dry_run:
        return
    if args.confirm_version != CONTENT_VERSION:
        raise SystemExit(f"Pass --confirm-version {CONTENT_VERSION} after human review")
    if not args.backup_file or not args.backup_file.is_file() or args.backup_file.stat().st_size == 0:
        raise SystemExit("--backup-file must point to a non-empty pg_dump created before execute")
    await execute()


if __name__ == "__main__":
    asyncio.run(main())
