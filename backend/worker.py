"""arq worker entry-point for background natal-PDF generation.

Runs as a separate container (`arq worker.WorkerSettings`) sharing the same
image as the API. It connects to the same Redis and Postgres, pulls
`generate_natal_pdf_task` jobs, and does the slow LLM work outside the HTTP
request path. The global token bucket (services.rate_limiter) keeps all worker
replicas under the configured provider's output-token ceiling.
"""

from __future__ import annotations

from arq.connections import RedisSettings

from core.cache import close_redis, init_redis
from core.logging import get_logger, setup_logging
from core.settings import settings
from services.tasks.natal_pdf_task import generate_natal_pdf_task

setup_logging()
log = get_logger(__name__)


async def startup(ctx: dict) -> None:
    # Our decode_responses Redis client — used by job status, the token bucket
    # and the dedup lock (separate from arq's own bytes-mode connection).
    await init_redis()
    log.info("worker.started")


async def shutdown(ctx: dict) -> None:
    await close_redis()
    log.info("worker.stopped")


class WorkerSettings:
    functions = [generate_natal_pdf_task]
    redis_settings = RedisSettings.from_dsn(str(settings.REDIS_URL))
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = settings.ARQ_MAX_JOBS
    job_timeout = settings.ARQ_JOB_TIMEOUT
    # Retries are deliberate (user re-clicks), not automatic — a partial run is
    # idempotent and a re-enqueue finishes from the warm cache instantly.
    max_tries = 1
    keep_result = 0  # job result lives in our Redis status blob, not arq's
