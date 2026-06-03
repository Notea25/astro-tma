"""Phase 5 smoke test: import v3_interpreter, build a context for Юля,
and generate the smallest section ("anahata", ~280 words) via Sonnet.

Confirms:
  1. Module imports cleanly (no key/attr typos in prompt builders).
  2. load_v3_context() round-trips through arcana_base + karmic_programs.
  3. The LLM call works end-to-end and writes to destiny_interpretations_v3.

Run on prod:
    docker compose exec backend python /app/scripts/smoke_v3_interpreter.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from sqlalchemy import delete  # noqa: E402

from db.database import AsyncSessionLocal  # noqa: E402
from db.models import DestinyInterpretationV3  # noqa: E402
from services.destiny_matrix.calculator import calculate_matrix  # noqa: E402
from services.destiny_matrix.v3_interpreter import (  # noqa: E402
    SECTIONS,
    load_v3_context,
    regenerate_sections,
)


# Owner's tg_user_id (any real users.id works — the smoke creates one
# interpretation row, then deletes it). Override via CLI: `… 1234567`.
SMOKE_USER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 414053177
SMOKE_BIRTH = date(2002, 7, 8)        # Юля reference birth
SMOKE_GENDER = "female"
SMOKE_NAME = "Юля (smoke)"
SMOKE_SECTION = "anahata"


async def main() -> None:
    print(f"Found {len(SECTIONS)} sections registered", flush=True)
    print(f"Section keys: {[s.key for s in SECTIONS]}", flush=True)

    positions = calculate_matrix(SMOKE_BIRTH)
    async with AsyncSessionLocal() as session:
        ctx = await load_v3_context(
            session,
            user_id=SMOKE_USER_ID,
            birth_date=SMOKE_BIRTH,
            gender=SMOKE_GENDER,
            name=SMOKE_NAME,
            positions=positions,
        )
        print(
            f"Context built: karmic={ctx.karmic.name if ctx.karmic else None}, "
            f"year={ctx.year_energy.current}→{ctx.year_energy.upcoming}, "
            f"purposes={len(ctx.purposes)}, arcana={len(ctx.arcana)}",
            flush=True,
        )

        print(f"\nGenerating section: {SMOKE_SECTION} …", flush=True)
        out = await regenerate_sections(session, ctx=ctx, keys=[SMOKE_SECTION])
        text = out.get(SMOKE_SECTION, "")
        if not text:
            print("FAIL — section returned empty content", flush=True)
            sys.exit(1)
        print(f"\n──── {SMOKE_SECTION} ({len(text)} chars) ────")
        print(text)
        print("\n────────────")

        # Clean up the smoke row so the user doesn't see a wrong Юля
        # interpretation in their cache.
        await session.execute(
            delete(DestinyInterpretationV3).where(
                DestinyInterpretationV3.user_id == SMOKE_USER_ID,
                DestinyInterpretationV3.birth_date == SMOKE_BIRTH,
                DestinyInterpretationV3.gender == SMOKE_GENDER,
                DestinyInterpretationV3.section == SMOKE_SECTION,
            )
        )
        await session.commit()
        print("Smoke row cleaned up.")
        print("PHASE 5 SMOKE PASS — section generated + cached + cleaned.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
