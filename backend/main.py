"""
FastAPI application entry point.

Architecture notes:
- Lifespan: init/teardown Redis, schedule jobs
- Routers: one per domain, all prefixed with /api
- CORS: allow Telegram Mini App origins
- Middleware: request logging, error normalisation
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from api.routes import (
    admin_stars,
    destiny_matrix,
    destiny_matrix_v3,
    glossary,
    horoscope,
    mac,
    natal,
    news,
    payments,
    referrals,
    support,
    synastry,
    tarot,
    transits,
    users,
)
from core.cache import close_redis, init_redis
from core.logging import get_logger, setup_logging
from core.settings import settings

setup_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown sequence."""
    log.info("app.starting", env=settings.APP_ENV)

    await init_redis()

    # arq enqueue pool for the natal-PDF queue (worker runs in its own container).
    from services.arq_pool import init_arq_pool

    await init_arq_pool()

    # Schedule daily horoscope generation at midnight UTC.
    #
    # NOTE: uvicorn runs with --workers 2, so every cron tick fires in
    # BOTH worker processes. Without coordination this caused:
    #   * 2× LLM spend on daily_horoscopes and daily_news
    #   * duplicate daily horoscope pushes at the user's local 09:00
    # `with_leader_lock` uses a Redis SET NX so exactly one worker
    # actually runs the job each tick. TTL is sized < the cron cadence
    # so a crashed leader doesn't lock out the next tick.
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from core.scheduler_lock import with_leader_lock

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        with_leader_lock("daily_horoscopes", ttl_seconds=3600)(
            _generate_daily_horoscopes,
        ),
        trigger="cron",
        hour=0,
        minute=5,
        id="daily_horoscopes",
    )

    if settings.FEATURE_PUSH_NOTIFICATIONS:
        from services.notifications.scheduler import send_daily_pushes

        scheduler.add_job(
            with_leader_lock("daily_pushes", ttl_seconds=300)(send_daily_pushes),
            trigger="cron",
            minute=0,
            id="daily_pushes",
        )

    from services.news.scheduler import generate_daily_news

    scheduler.add_job(
        with_leader_lock("daily_news", ttl_seconds=3600)(generate_daily_news),
        trigger="cron",
        hour=6,
        minute=0,
        id="daily_news",
    )

    # V3 destiny matrix — invalidate year_energy section on user's BD.
    # Hourly so we catch the BD rollover for every timezone bucket.
    from services.destiny_matrix.year_energy_scheduler import (
        invalidate_year_energy_on_birthday,
    )

    scheduler.add_job(
        with_leader_lock("destiny_v3_year_energy_invalidate", ttl_seconds=300)(
            invalidate_year_energy_on_birthday,
        ),
        trigger="cron",
        minute=15,
        id="destiny_v3_year_energy_invalidate",
    )

    scheduler.start()
    log.info("scheduler.started")

    # Idempotently (re-)register the support bot webhook with Telegram.
    # No-op when SUPPORT_BOT_TOKEN is unset.
    from api.routes.support import setup_support_webhook

    await setup_support_webhook()

    yield

    scheduler.shutdown(wait=False)
    from services.arq_pool import close_arq_pool

    await close_arq_pool()
    await close_redis()
    log.info("app.shutdown")


app = FastAPI(
    title="Astro TMA API",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Trust X-Forwarded-Proto from nginx so the app generates https:// URLs
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# ── Session (required by SQLAdmin auth) ───────────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.APP_SECRET_KEY,
    https_only=False,
    same_site="lax",
    session_cookie="session",
    max_age=86400 * 14,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Telegram Mini Apps are served from *.telegram.org in production
# Allow localhost for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web.telegram.org",
        "https://webk.telegram.org",
        "https://webz.telegram.org",
        "https://astro-tma.vercel.app",
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", path=request.url.path, exc=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Request logging middleware ─────────────────────────────────────────────────
# Requests above this threshold emit at WARNING level — easy to grep in
# `docker logs` to spot the routes that are pinning workers under load.
SLOW_REQUEST_MS = 1500


@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    if duration_ms >= SLOW_REQUEST_MS:
        log.warning(
            "http.request.slow",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
    else:
        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
    return response


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(users.router, prefix="/api")
app.include_router(horoscope.router, prefix="/api")
app.include_router(tarot.router, prefix="/api")
app.include_router(natal.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(mac.router, prefix="/api")
app.include_router(transits.router, prefix="/api")
app.include_router(synastry.router, prefix="/api")
app.include_router(glossary.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(referrals.router, prefix="/api")
app.include_router(destiny_matrix.router, prefix="/api")
app.include_router(destiny_matrix_v3.router, prefix="/api")
app.include_router(admin_stars.router, prefix="/api")
app.include_router(support.router, prefix="/api")


# ── Admin ─────────────────────────────────────────────────────────────────────
from admin import create_admin

create_admin(app)


@app.get("/health")
async def health():
    """Load balancer health check."""
    return {"status": "ok", "env": settings.APP_ENV}


# ── Scheduled jobs ─────────────────────────────────────────────────────────────
async def _generate_daily_horoscopes() -> None:
    """
    Pre-generate and cache horoscopes for all 12 signs via LLM.
    Runs nightly at 00:05 UTC via APScheduler.
    Falls back to generic texts if LLM unavailable.
    """
    from datetime import date

    from api.routes.horoscope import _GENERIC_TEXTS, _SIGN_RU
    from api.schemas.horoscope import HoroscopeResponse
    from core.cache import cache_set, key_horoscope
    from db.models import ZodiacSign
    from services.astro.llm_horoscope import generate_daily_horoscope

    today_date = date.today()
    today = today_date.isoformat()
    log.info("scheduler.horoscopes_generating", date=today)

    for sign in ZodiacSign:
        try:
            # Generate text via LLM
            text = await generate_daily_horoscope(sign.value, today_date, "today")
            if not text:
                text = _GENERIC_TEXTS.get(sign.value, "")

            response = HoroscopeResponse(
                sign=sign.value,
                sign_ru=_SIGN_RU.get(sign.value, sign.value),
                date=today_date,
                period="today",
                text_ru=text,
                is_personalised=False,
            )
            cache_key = key_horoscope(sign.value, today, "today")
            await cache_set(cache_key, response.model_dump(mode="json"), 90000)
            log.info("scheduler.horoscope_ok", sign=sign.value)
        except Exception as e:
            log.error("scheduler.horoscope_failed", sign=sign.value, error=str(e))

    log.info("scheduler.horoscopes_done")
