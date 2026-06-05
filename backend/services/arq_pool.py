"""arq enqueue pool for the HTTP side.

arq talks to Redis in bytes mode, while `core.cache` uses
`decode_responses=True` for our JSON helpers. The two can't share one client,
so the HTTP process keeps a separate arq pool just for enqueuing jobs. The arq
worker has its own connection via `WorkerSettings.redis_settings`.
"""

from __future__ import annotations

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from core.logging import get_logger
from core.settings import settings

log = get_logger(__name__)

_arq: ArqRedis | None = None


async def init_arq_pool() -> None:
    global _arq
    _arq = await create_pool(RedisSettings.from_dsn(str(settings.REDIS_URL)))
    log.info("arq.pool_connected")


async def close_arq_pool() -> None:
    global _arq
    if _arq is not None:
        await _arq.aclose()
        _arq = None
        log.info("arq.pool_disconnected")


def get_arq_pool() -> ArqRedis:
    if _arq is None:
        raise RuntimeError("arq pool not initialized. Call init_arq_pool() first.")
    return _arq
