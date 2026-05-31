"""Global concurrency gate for Anthropic API calls.

Anthropic's tier-1 plan caps at ~50 RPM with a low concurrent-connection
ceiling. Without coordination, a sudden burst of users hitting any
LLM-backed endpoint (cold destiny interpretation, first natal reading,
first tarot interpretation) can quickly trigger HTTP 429s — which then
cascade into user-visible errors because most of our callers don't
implement exponential backoff.

This semaphore bounds the number of concurrent ``messages.create``
calls inside this Python process. With two uvicorn workers the
effective ceiling is ``LLM_CONCURRENCY × 2``.

Usage:

    from services.llm_pool import llm_semaphore

    async with llm_semaphore:
        message = await client.messages.create(...)

Why a context manager instead of wrapping the SDK call? Two reasons:
the SDK exposes many shapes (``messages.create``, streams, tools, …)
and a wrapper would have to mirror all of them; plus we want the
semaphore to be visible at every call site so reviewers can see the
contention point.
"""

from __future__ import annotations

import asyncio
import os

# Tune via env on the host without a code change. 6 is a reasonable
# default for tier-1: enough to soak up bursts without pinning the API
# at the per-minute ceiling. Bump to 12-16 on tier-2.
LLM_CONCURRENCY = int(os.environ.get("LLM_CONCURRENCY", "6"))

llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY)
