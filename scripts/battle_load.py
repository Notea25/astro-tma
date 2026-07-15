#!/usr/bin/env python3
"""Battle-profile load test: signed Telegram initData + realistic Mini App launch.

Safe by default:
  - loopback targets only unless LOAD_ALLOW_REMOTE=1
  - no YuKassa create
  - no PDF generation
  - no destiny v3 cold reading
  - horoscope/today hit after one warm-up (expects Redis cache)

The profile does POST /api/users/me, so unique virtual users create rows. Use a
dedicated ID range and delete it after the test. The script exits non-zero when
the error-rate or optional p95 threshold is exceeded.

Runs inside the docker network (host: backend:8000) or via public URL.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from urllib.parse import urlsplit


_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "host.docker.internal"}


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def validate_target(base: str) -> None:
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SystemExit(f"Invalid LOAD_BASE: {base!r}")
    if parsed.hostname not in _LOCAL_HOSTS and not env_flag("LOAD_ALLOW_REMOTE"):
        raise SystemExit(
            f"Refusing non-loopback LOAD_BASE={base!r}. "
            "Set LOAD_ALLOW_REMOTE=1 only for an approved target."
        )


def make_init_data(bot_token: str, user_id: int, first_name: str = "Load") -> str:
    user = json.dumps(
        {
            "id": user_id,
            "first_name": first_name,
            "last_name": "Test",
            "username": f"load_{user_id}",
            "language_code": "ru",
            "is_premium": False,
        },
        separators=(",", ":"),
    )
    params = {
        "user": user,
        "auth_date": str(int(time.time())),
        "query_id": f"AALoadTest{user_id}",
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


@dataclass
class CallResult:
    name: str
    status: int
    latency_ms: float
    error: str = ""
    response_body: bytes = b""


@dataclass
class Agg:
    counts: Counter = field(default_factory=Counter)
    latencies: list[float] = field(default_factory=list)
    errors: Counter = field(default_factory=Counter)

    def add(self, r: CallResult) -> None:
        self.counts[r.status] += 1
        self.latencies.append(r.latency_ms)
        if r.error:
            self.errors[r.error] += 1


def request(
    method: str,
    url: str,
    init_data: str,
    body: bytes | None = None,
    timeout: float = 20.0,
    capture_response: bool = False,
) -> CallResult:
    name = url.split("/api", 1)[-1] if "/api" in url else url
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("X-Init-Data", init_data)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            response_body = resp.read()
            return CallResult(
                name,
                resp.status,
                (time.perf_counter() - t0) * 1000,
                response_body=response_body if capture_response else b"",
            )
    except urllib.error.HTTPError as e:
        try:
            e.read()
        except Exception:
            pass
        return CallResult(name, e.code, (time.perf_counter() - t0) * 1000)
    except Exception as e:
        return CallResult(name, 0, (time.perf_counter() - t0) * 1000, type(e).__name__)


def user_session(base: str, init_data: str) -> list[CallResult]:
    """One Mini App open: typical first-paint fan-out."""
    out: list[CallResult] = []
    # sequential groups mirror real UI a bit, but parallel within group
    batches = [
        [
            ("POST", f"{base}/api/users/me", None),
            ("GET", f"{base}/api/payments/products", None),
            ("GET", f"{base}/api/users/me/purchases", None),
        ],
        [
            ("GET", f"{base}/api/horoscope/moon", None),
            ("GET", f"{base}/api/horoscope/today", None),
            ("GET", f"{base}/api/news", None),
        ],
        [
            ("GET", f"{base}/api/glossary", None),
            ("GET", f"{base}/api/natal/summary", None),
            ("GET", f"{base}/api/mac/today", None),
        ],
    ]
    for batch in batches:
        with ThreadPoolExecutor(max_workers=len(batch)) as ex:
            futs = [
                ex.submit(request, m, u, init_data, b)
                for m, u, b in batch
            ]
            out.extend(f.result() for f in as_completed(futs))
    return out


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * p))]


def print_agg(title: str, agg: Agg, elapsed: float, n_users: int) -> None:
    total = sum(agg.counts.values())
    ok = sum(v for k, v in agg.counts.items() if 200 <= k < 400)
    print(f"\n=== {title} ===")
    print(f"Users: {n_users}  Requests: {total}  Duration: {elapsed:.2f}s")
    if elapsed > 0:
        print(f"RPS: {total / elapsed:.1f}  Sessions/s: {n_users / elapsed:.2f}")
    print(f"Status: {dict(agg.counts)}")
    if agg.latencies:
        print(
            f"Latency ms — min={min(agg.latencies):.0f} p50={pct(agg.latencies,0.5):.0f} "
            f"p95={pct(agg.latencies,0.95):.0f} p99={pct(agg.latencies,0.99):.0f} "
            f"max={max(agg.latencies):.0f} avg={statistics.mean(agg.latencies):.0f}"
        )
    print(f"OK (2xx/3xx): {ok}/{total} ({100*ok/max(total,1):.1f}%)")
    if agg.errors:
        print(f"Transport errors: {dict(agg.errors)}")


def main() -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN required")

    base = os.environ.get("LOAD_BASE", "http://127.0.0.1:8018").rstrip("/")
    validate_target(base)
    n_users = int(os.environ.get("LOAD_USERS", "50"))
    concurrency = int(os.environ.get("LOAD_CONCURRENCY", "20"))
    user_id_base = int(os.environ.get("LOAD_USER_BASE", "9100000000"))
    max_error_rate = float(os.environ.get("LOAD_MAX_ERROR_RATE", "0"))
    max_p95_ms = float(os.environ.get("LOAD_MAX_P95_MS", "0"))

    if n_users < 1 or concurrency < 1:
        raise SystemExit("LOAD_USERS and LOAD_CONCURRENCY must be positive")
    if not 0 <= max_error_rate <= 100:
        raise SystemExit("LOAD_MAX_ERROR_RATE must be between 0 and 100")

    print(f"Battle load: users={n_users} concurrency={concurrency} base={base}")

    # Warm caches with one signed user (horoscope/today especially)
    warm_id = user_id_base
    warm_init = make_init_data(bot_token, warm_id, "Warm")
    print("Warm-up...")
    warm_user_response: bytes = b""
    for path, method, body in [
        (f"{base}/api/users/me", "POST", None),
        (f"{base}/api/horoscope/moon", "GET", None),
        (f"{base}/api/horoscope/today", "GET", None),
        (f"{base}/api/glossary", "GET", None),
        (f"{base}/api/news", "GET", None),
        (f"{base}/api/payments/products", "GET", None),
    ]:
        capture_response = path.endswith("/api/users/me")
        r = request(
            method,
            path,
            warm_init,
            body,
            timeout=60,
            capture_response=capture_response,
        )
        if capture_response:
            warm_user_response = r.response_body
        print(f"  warm {method} {path.split('/api')[-1]} -> {r.status} {r.latency_ms:.0f}ms")

    try:
        actual_warm_id = int(json.loads(warm_user_response)["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise SystemExit("Warm-up /api/users/me returned an invalid response")
    if actual_warm_id != warm_id:
        message = (
            f"Signed user {warm_id} became API user {actual_warm_id}; "
            "AUTH_BYPASS is probably active, so virtual users are not distinct."
        )
        if env_flag("LOAD_REQUIRE_DISTINCT_USERS", default=True):
            raise SystemExit(message + " Set LOAD_REQUIRE_DISTINCT_USERS=0 for a same-user test.")
        print(f"WARNING: {message}")

    tokens = [
        make_init_data(bot_token, user_id_base + i, f"VU{i}")
        for i in range(n_users)
    ]

    by_endpoint: dict[str, Agg] = defaultdict(Agg)
    overall = Agg()

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [ex.submit(user_session, base, tok) for tok in tokens]
        for fut in as_completed(futs):
            for r in fut.result():
                overall.add(r)
                by_endpoint[r.name].add(r)
    elapsed = time.perf_counter() - t0

    print_agg(f"Battle profile ({n_users} virtual users)", overall, elapsed, n_users)

    print("\n--- Per endpoint ---")
    for name, agg in sorted(by_endpoint.items(), key=lambda x: x[0]):
        total = sum(agg.counts.values())
        ok = sum(v for k, v in agg.counts.items() if 200 <= k < 400)
        p50 = pct(agg.latencies, 0.5) if agg.latencies else 0
        p95 = pct(agg.latencies, 0.95) if agg.latencies else 0
        print(
            f"{name:40s} n={total:4d} ok={ok:4d} "
            f"p50={p50:6.0f} p95={p95:6.0f} codes={dict(agg.counts)}"
        )

    req = urllib.request.Request(f"{base}/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"\nPostflight /health: {resp.status} {resp.read().decode()[:160]}")

    total = sum(overall.counts.values())
    ok = sum(v for code, v in overall.counts.items() if 200 <= code < 400)
    error_rate = 100 * (total - ok) / max(total, 1)
    p95_ms = pct(overall.latencies, 0.95)
    failures: list[str] = []
    if error_rate > max_error_rate:
        failures.append(f"error rate {error_rate:.2f}% > {max_error_rate:.2f}%")
    if max_p95_ms > 0 and p95_ms > max_p95_ms:
        failures.append(f"p95 {p95_ms:.0f}ms > {max_p95_ms:.0f}ms")
    if failures:
        print("Load thresholds failed: " + "; ".join(failures), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
