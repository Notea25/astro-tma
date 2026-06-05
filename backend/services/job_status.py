"""Status tracking for async natal-PDF generation jobs.

The HTTP endpoint enqueues a job and the arq worker processes it; both sides
read/write a small JSON blob in Redis so the frontend can poll progress. One
shared format keeps `/pdf/status/{job_id}` and the worker in sync.

Status machine: queued → processing → (ready | failed).
"""

from __future__ import annotations

import time
from typing import Any

from core.cache import cache_get, cache_set, key_natal_pdf_jobstatus

JOB_STATUS_TTL = 1800  # 30 min — long enough to outlive a slow free-tier run


async def set_job_status(job_id: str, status: str, **fields: Any) -> None:
    """Write the job status blob. `fields` may carry error / download_token /
    filename / progress depending on the state."""
    payload = {"status": status, "updated_at": int(time.time()), **fields}
    await cache_set(key_natal_pdf_jobstatus(job_id), payload, JOB_STATUS_TTL)


async def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Return the job status blob, or None if unknown/expired."""
    data = await cache_get(key_natal_pdf_jobstatus(job_id))
    return data if isinstance(data, dict) else None
