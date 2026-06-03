"""Redis-backed leader lock so a cron job runs in only ONE uvicorn worker.

The Dockerfile launches uvicorn with `--workers 2`, and each worker
boots its own AsyncIOScheduler. Without coordination, every cron tick
fires the same job twice — at best wasted work (news re-generated, year
energy re-invalidated), at worst duplicate side-effects (users got two
identical daily horoscope pushes at 09:00).

`with_leader_lock(name, ttl)` wraps a coroutine so that exactly one
worker per tick acquires `SET NX` on `scheduler:lock:{name}`. The TTL
is set just under the job's run cadence so a crashed leader doesn't
hold the lock forever. The other worker(s) see the existing key,
log a quiet skip, and return.

Lock-key namespace is per-job — picking the same `name` you use for
`scheduler.add_job(..., id=name)` keeps it grep-able.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

from core.cache import get_redis
from core.logging import get_logger

log = get_logger(__name__)


def with_leader_lock(name: str, ttl_seconds: int) -> Callable[
    [Callable[[], Awaitable[None]]], Callable[[], Awaitable[None]]
]:
    """Decorator factory. `ttl_seconds` should be shorter than the
    cron interval so a stalled worker doesn't lock everyone out for
    the next tick, but longer than the expected job runtime."""
    def decorator(
        job: Callable[[], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        async def wrapped() -> None:
            key = f"scheduler:lock:{name}"
            r = get_redis()
            acquired = await cast(
                Awaitable[bool],
                r.set(key, "1", nx=True, ex=ttl_seconds),
            )
            if not acquired:
                log.info("scheduler.skipped_not_leader", job=name)
                return
            try:
                await job()
            finally:
                # Best-effort release; if we crashed mid-job the TTL
                # cleans up next tick.
                try:
                    await cast(Awaitable[Any], r.delete(key))
                except Exception:  # noqa: BLE001
                    pass

        wrapped.__name__ = job.__name__
        return wrapped

    return decorator
