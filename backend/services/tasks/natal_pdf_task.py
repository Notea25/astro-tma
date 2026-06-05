"""arq task: generate the personal natal-report texts in the background.

The HTTP endpoint enqueues this and returns immediately; the worker does the
slow LLM work (descriptions + reading), persists them to DB/Redis, then mints a
download token. The PDF itself is NOT built here — it's rendered on demand by
the existing ``GET /natal/pdf-download/{token}`` endpoint, which by then finds
all texts in the hot cache and renders in ~300ms.

Status flow (Redis, read by ``GET /natal/pdf/status/{job_id}``):
    queued → processing → (ready{download_token} | failed{error})
"""

from __future__ import annotations

from secrets import token_urlsafe
from typing import Any

from core.cache import cache_set, get_redis, key_natal_pdf_download, key_natal_pdf_job
from core.logging import get_logger
from db.database import AsyncSessionLocal
from services.job_status import set_job_status
from services.users import repository as user_repo

log = get_logger(__name__)

# Download token TTL — generous so a slow user still catches the ready PDF.
_PDF_DOWNLOAD_TTL_SECONDS = 900


async def _has_access(db: Any, user: Any) -> bool:
    """Mirror of ``_get_pdf_user_or_error`` but without HTTP exceptions."""
    if not user or not user.natal_chart:
        return False
    is_prem = await user_repo.is_premium(db, user.id)
    has_purchase = await user_repo.has_purchased(db, user.id, "natal_full")
    return bool(is_prem or has_purchase)


async def generate_natal_pdf_task(ctx: dict, user_id: int, job_id: str) -> dict:
    """Generate descriptions + reading for ``user_id`` and publish a download
    token. ``job_id`` is the app-level id the endpoint handed the client (the
    status blob is keyed by it, not by arq's internal ctx job_id). Idempotent:
    ``_get_or_generate_*`` short-circuit on a warm cache."""
    # Imported here (not at module top) to avoid importing the FastAPI route
    # layer at worker startup before settings/logging are wired.
    from api.routes.natal import (
        _get_or_generate_descriptions,
        _get_or_generate_pdf_reading,
        _natal_pdf_filename,
    )

    await set_job_status(job_id, "processing")
    try:
        async with AsyncSessionLocal() as db:
            user = await user_repo.get_by_id(db, user_id)
            if not await _has_access(db, user):
                await set_job_status(job_id, "failed", error="Нет доступа или данных рождения")
                return {"status": "failed"}
            assert user is not None
            assert user.natal_chart is not None

            chart = user.natal_chart
            planets = chart.chart_data.get("planets", {})
            aspects = chart.chart_data.get("aspects", [])

            # Both short-circuit on a warm cache; otherwise hit the LLM (rate-
            # limited by the global token bucket).
            await _get_or_generate_descriptions(db, user)
            await _get_or_generate_pdf_reading(user, chart, planets, aspects)

            token = token_urlsafe(24)
            await cache_set(
                key_natal_pdf_download(token),
                {"user_id": user.id, "ready": True},
                _PDF_DOWNLOAD_TTL_SECONDS,
            )
            await set_job_status(
                job_id,
                "ready",
                download_token=token,
                filename=_natal_pdf_filename(user),
            )
            log.info("natal.pdf_job_ready", user_id=user_id, job_id=job_id)
            return {"status": "ready", "download_token": token}
    except Exception as e:  # noqa: BLE001
        log.error("natal.pdf_job_failed", user_id=user_id, job_id=job_id, error=str(e))
        await set_job_status(job_id, "failed", error="Не удалось сгенерировать отчёт")
        return {"status": "failed"}
    finally:
        # Release the per-user dedup lock so the next request can enqueue.
        try:
            await get_redis().delete(key_natal_pdf_job(user_id))
        except Exception:  # noqa: BLE001
            pass
