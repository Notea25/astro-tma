"""Global concurrency gate for Playwright/Chromium-backed PDF generation.

Each PDF render spawns a fresh chromium subprocess that costs ~250-350 MB
of RAM. On the current 4 GB VPS, more than two concurrent renders pushes
the box into swap and risks an OOM-kill of the backend container.

This semaphore is process-local. With multiple uvicorn workers it caps
per worker — so the effective ceiling is `workers × PDF_CONCURRENCY`.
Currently 2 × 2 = 4, which leaves enough headroom for the rest of the
process.

Usage:

    from services.playwright_pool import pdf_semaphore

    async with pdf_semaphore:
        ...  # launch chromium and render
"""

from __future__ import annotations

import asyncio
import os

# Hard cap on simultaneous PDF renders inside this Python process.
# Override via env when scaling up the host.
PDF_CONCURRENCY = int(os.environ.get("PDF_CONCURRENCY", "2"))

pdf_semaphore = asyncio.Semaphore(PDF_CONCURRENCY)
