#!/usr/bin/env python3
"""Backfill server-resolved birth country codes without exposing birth data.

Dry-run is the default and performs no database writes:
    python scripts/backfill_birth_country_codes.py --limit 100

After reviewing the aggregate counts, apply with an explicit checkpoint:
    python scripts/backfill_birth_country_codes.py \
      --apply --confirm-reviewed-dry-run

Nominatim's public rate limit is respected by the default 1.1 second delay.
Use ``--resume-after-id`` with the aggregate resume token printed at the end.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import select, update

from db.database import AsyncSessionLocal
from db.models import User
from services.users.birth_location import reverse_country_code


async def backfill(
    *,
    apply: bool,
    batch_size: int,
    delay_seconds: float,
    limit: int | None,
    resume_after_id: int,
) -> tuple[int, int, Counter[str], int]:
    processed = 0
    updated = 0
    country_counts: Counter[str] = Counter()
    last_id = resume_after_id

    async with httpx.AsyncClient(timeout=8.0) as client:
        while limit is None or processed < limit:
            fetch_size = batch_size
            if limit is not None:
                fetch_size = min(fetch_size, limit - processed)
            if fetch_size <= 0:
                break

            async with AsyncSessionLocal() as session:
                rows = (
                    await session.execute(
                        select(User.id, User.birth_lat, User.birth_lng)
                        .where(
                            User.id > last_id,
                            User.birth_country_code.is_(None),
                            User.birth_lat.is_not(None),
                            User.birth_lng.is_not(None),
                        )
                        .order_by(User.id)
                        .limit(fetch_size)
                    )
                ).all()

            if not rows:
                break

            resolved_rows: list[tuple[int, str]] = []
            for user_id, birth_lat, birth_lng in rows:
                country_code = await reverse_country_code(
                    float(birth_lat),
                    float(birth_lng),
                    client=client,
                )
                processed += 1
                last_id = int(user_id)
                country_counts[country_code or "UNKNOWN"] += 1
                if country_code is not None:
                    resolved_rows.append((int(user_id), country_code))
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)

            if apply and resolved_rows:
                async with AsyncSessionLocal() as session:
                    for user_id, country_code in resolved_rows:
                        result = await session.execute(
                            update(User)
                            .where(
                                User.id == user_id,
                                User.birth_country_code.is_(None),
                            )
                            .values(birth_country_code=country_code)
                        )
                        updated += int(result.rowcount or 0)
                    await session.commit()

            if len(rows) < fetch_size:
                break

    return processed, updated, country_counts, last_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="persist resolved codes")
    parser.add_argument(
        "--confirm-reviewed-dry-run",
        action="store_true",
        help="required checkpoint for --apply",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--delay-seconds", type=float, default=1.1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume-after-id", type=int, default=0)
    args = parser.parse_args()

    if args.apply and not args.confirm_reviewed_dry_run:
        parser.error("--apply requires --confirm-reviewed-dry-run")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.delay_seconds < 0:
        parser.error("--delay-seconds cannot be negative")

    processed, updated, country_counts, last_id = asyncio.run(
        backfill(
            apply=args.apply,
            batch_size=args.batch_size,
            delay_seconds=args.delay_seconds,
            limit=args.limit,
            resume_after_id=args.resume_after_id,
        )
    )

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Processed: {processed}")
    print(f"Updated: {updated}")
    print("Resolved country counts:")
    for country_code, count in sorted(country_counts.items()):
        print(f"  {country_code}: {count}")
    print(f"Resume after ID: {last_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
