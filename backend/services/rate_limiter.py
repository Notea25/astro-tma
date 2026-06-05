"""Distributed token-bucket rate limiter for Anthropic output tokens.

Anthropic's per-minute output-token limit is enforced on the API KEY, not per
process. An in-process semaphore can't coordinate across the HTTP workers and
the arq worker container, so a burst of natal-PDF jobs still storms the key with
429s. This bucket lives in Redis: every LLM call reserves its estimated output
tokens from one shared bucket before hitting the API, so N workers honestly
split the key's budget no matter how many replicas run.

The bucket is a single Redis hash {tokens, ts}. A Lua script does the
refill-and-consume atomically so concurrent workers can't double-spend.

Usage:

    from services.rate_limiter import AnthropicLimiter

    async with AnthropicLimiter(estimated_output_tokens=3200):
        msg = await client.messages.create(..., max_tokens=3200)

We reserve `max_tokens` (the upper bound) up front rather than the real usage —
a small over-estimate just makes us slightly more conservative, which is the
safe direction. ``ANTHROPIC_OUTPUT_TPM`` defaults below the real ceiling to keep
a buffer for the reading call and retries.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, cast

import core.cache as cache
from core.logging import get_logger

log = get_logger(__name__)

# Per-minute output-token budget for the whole API key. Default sits under the
# free-tier 10k/min ceiling so the reading call + backoff have headroom. Bump on
# higher tiers via env (tier-2 ~200k, tier-4 ~2M). Set <= 0 to DISABLE limiting
# entirely (useful for measuring raw generation time or on a high tier).
OUTPUT_TPM = int(os.environ.get("ANTHROPIC_OUTPUT_TPM", "9000"))
_LIMITER_ENABLED = OUTPUT_TPM > 0

_BUCKET_KEY = "anthropic:tokenbucket:output"
_REFILL_PER_MS = OUTPUT_TPM / 60_000.0  # tokens regenerated per millisecond

# How long a single acquire may wait before giving up. A stalled bucket
# shouldn't pin a coroutine forever — the caller surfaces this as a failed job
# the user can retry.
_ACQUIRE_TIMEOUT_S = float(os.environ.get("ANTHROPIC_ACQUIRE_TIMEOUT_S", "180"))

# Atomic refill-then-consume. Returns {allowed(0|1), wait_ms}.
#   KEYS[1] = bucket hash
#   ARGV    = now_ms, capacity, refill_per_ms, requested
_LUA_CONSUME = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then
  tokens = capacity
  ts = now
end

local elapsed = now - ts
if elapsed > 0 then
  tokens = math.min(capacity, tokens + elapsed * refill)
  ts = now
end

if tokens >= requested then
  tokens = tokens - requested
  redis.call('HMSET', key, 'tokens', tokens, 'ts', ts)
  redis.call('PEXPIRE', key, 120000)
  return {1, 0}
else
  local deficit = requested - tokens
  local wait_ms = math.ceil(deficit / refill)
  redis.call('HMSET', key, 'tokens', tokens, 'ts', ts)
  redis.call('PEXPIRE', key, 120000)
  return {0, wait_ms}
end
"""


async def _now_ms(redis: Any) -> int:
    """Server time in ms from Redis, so all workers share one clock."""
    secs, micros = await cast(Any, redis.time())
    return int(secs) * 1000 + int(micros) // 1000


async def acquire_output_tokens(
    estimated_tokens: int,
    *,
    timeout_s: float = _ACQUIRE_TIMEOUT_S,
) -> None:
    """Block until `estimated_tokens` are available in the shared bucket.

    Loops EVAL → if allowed return, else sleep wait_ms and retry. On timeout it
    does NOT raise — it logs and proceeds, letting the real API call through.
    The bucket is a smoother, not a hard gate: dropping the call would lose
    work, whereas proceeding falls back to Anthropic's own 429 + the caller's
    exponential backoff. Worst case we briefly exceed the soft TPM target.

    Degrades to a no-op when Redis isn't initialized (unit tests, or a Redis
    outage) — better to let the call through than to break every LLM path.
    """
    if not _LIMITER_ENABLED:  # disabled via ANTHROPIC_OUTPUT_TPM<=0
        return
    if cache._redis is None:  # noqa: SLF001 — Redis not wired up; skip limiting
        return
    redis = cache.get_redis()
    # A single request can never need more than the whole bucket; clamp so we
    # don't deadlock when a max_tokens estimate exceeds capacity.
    requested = max(1, min(estimated_tokens, OUTPUT_TPM))
    deadline = await _now_ms(redis) + int(timeout_s * 1000)

    while True:
        now = await _now_ms(redis)
        allowed, wait_ms = await cast(
            Any,
            redis.eval(
                _LUA_CONSUME,
                1,
                _BUCKET_KEY,
                str(now),
                str(OUTPUT_TPM),
                str(_REFILL_PER_MS),
                str(requested),
            ),
        )
        if int(allowed) == 1:
            return
        if now >= deadline:
            # Proceed anyway — don't lose the batch. The call may 429; the
            # caller's backoff handles that.
            log.warning(
                "rate_limiter.acquire_timeout_proceeding",
                requested=requested,
                wait_ms=int(wait_ms),
            )
            return
        # Don't sleep past the deadline, and cap so we re-check periodically.
        sleep_ms = min(int(wait_ms), 5_000, max(0, deadline - now))
        await asyncio.sleep(max(sleep_ms, 50) / 1000.0)


class AnthropicLimiter:
    """Async context manager reserving output tokens before an LLM call.

    async with AnthropicLimiter(estimated_output_tokens=3200):
        msg = await client.messages.create(..., max_tokens=3200)
    """

    def __init__(self, estimated_output_tokens: int, *, timeout_s: float = _ACQUIRE_TIMEOUT_S):
        self._est = estimated_output_tokens
        self._timeout_s = timeout_s

    async def __aenter__(self) -> AnthropicLimiter:
        await acquire_output_tokens(self._est, timeout_s=self._timeout_s)
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False
