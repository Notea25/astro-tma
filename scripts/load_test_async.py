#!/usr/bin/env python3
"""Async load tester — no external deps beyond stdlib + optional aiohttp via urllib."""
from __future__ import annotations

import concurrent.futures
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Result:
    status: int
    latency_ms: float
    error: str = ""


@dataclass
class Report:
    name: str
    n: int
    concurrency: int
    statuses: Counter = field(default_factory=Counter)
    latencies: list[float] = field(default_factory=list)
    errors: Counter = field(default_factory=Counter)
    elapsed_s: float = 0.0

    def print(self) -> None:
        ok = sum(v for k, v in self.statuses.items() if 200 <= k < 400)
        print(f"\n=== {self.name} ===")
        print(f"Requests: {self.n}  Concurrency: {self.concurrency}")
        print(f"Duration: {self.elapsed_s:.2f}s  RPS: {self.n / max(self.elapsed_s, 0.001):.1f}")
        print(f"Status codes: {dict(self.statuses)}")
        if self.latencies:
            sorted_l = sorted(self.latencies)
            p50 = sorted_l[int(len(sorted_l) * 0.50)]
            p95 = sorted_l[min(len(sorted_l) - 1, int(len(sorted_l) * 0.95))]
            p99 = sorted_l[min(len(sorted_l) - 1, int(len(sorted_l) * 0.99))]
            print(
                f"Latency ms — min={min(sorted_l):.1f} p50={p50:.1f} "
                f"p95={p95:.1f} p99={p99:.1f} max={max(sorted_l):.1f} "
                f"avg={statistics.mean(sorted_l):.1f}"
            )
        if self.errors:
            print(f"Errors: {dict(self.errors)}")
        print(f"Success (2xx/3xx): {ok}/{self.n} ({100 * ok / self.n:.1f}%)")


def one_request(method: str, url: str, body: bytes | None, timeout: float) -> Result:
    req = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return Result(status=resp.status, latency_ms=(time.perf_counter() - t0) * 1000)
    except urllib.error.HTTPError as e:
        try:
            e.read()
        except Exception:
            pass
        return Result(status=e.code, latency_ms=(time.perf_counter() - t0) * 1000)
    except Exception as e:
        return Result(status=0, latency_ms=(time.perf_counter() - t0) * 1000, error=type(e).__name__)


def run_load(
    name: str,
    url: str,
    n: int,
    concurrency: int,
    method: str = "GET",
    body: bytes | None = None,
    timeout: float = 10.0,
) -> Report:
    report = Report(name=name, n=n, concurrency=concurrency)
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [
            ex.submit(one_request, method, url, body, timeout) for _ in range(n)
        ]
        for fut in concurrent.futures.as_completed(futs):
            r = fut.result()
            report.statuses[r.status] += 1
            report.latencies.append(r.latency_ms)
            if r.error:
                report.errors[r.error] += 1
    report.elapsed_s = time.perf_counter() - t0
    return report


def main() -> None:
    BASE = "http://127.0.0.1:8000"
    PUBLIC = "https://ip-194-99-21-53-142250.vps.hosted-by-mvps.net"

    scenarios = [
        ("1. Direct /health c=50 n=2000", f"{BASE}/health", 2000, 50, "GET", None),
        ("2. Direct /health c=100 n=5000", f"{BASE}/health", 5000, 100, "GET", None),
        ("3. Direct /api/payments/return c=40 n=1000", f"{BASE}/api/payments/return", 1000, 40, "GET", None),
        ("4. Direct POST /api/users/me (401) c=50 n=2000", f"{BASE}/api/users/me", 2000, 50, "POST", b"{}"),
        ("5. Direct GET /api/glossary (401) c=50 n=2000", f"{BASE}/api/glossary", 2000, 50, "GET", None),
        ("6. Nginx HTTPS /health c=30 n=1000", f"{PUBLIC}/health", 1000, 30, "GET", None),
        ("7. Nginx HTTPS /api/glossary (rate-limit) c=40 n=200", f"{PUBLIC}/api/glossary", 200, 40, "GET", None),
    ]

    print("Load test start", flush=True)
    for name, url, n, c, method, body in scenarios:
        rep = run_load(name, url, n, c, method, body)
        rep.print()
        print(flush=True)

    # final health
    r = one_request("GET", f"{BASE}/health", None, 5)
    print(f"Postflight health: status={r.status} latency={r.latency_ms:.1f}ms")


if __name__ == "__main__":
    main()
