#!/usr/bin/env python3
"""Dependency-free concurrent HTTP load probe.

The default target is loopback and a non-loopback target requires an explicit
``--allow-remote`` flag. This probe opens one connection per request; for high
concurrency run it inside the same Docker network to avoid measuring Docker
Desktop's host port proxy instead of the API.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import statistics
import time
import urllib.error
import urllib.parse
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
    expected_statuses: set[int] = field(default_factory=lambda: {200})

    @property
    def passed(self) -> bool:
        return not self.errors and all(
            status in self.expected_statuses for status in self.statuses
        )

    def print(self) -> None:
        ok = sum(v for k, v in self.statuses.items() if k in self.expected_statuses)
        print(f"\n=== {self.name} ===")
        print(f"Requests: {self.n}  Concurrency: {self.concurrency}")
        print(f"Duration: {self.elapsed_s:.2f}s  RPS: {self.n / max(self.elapsed_s, 0.001):.1f}")
        print(f"Status codes: {dict(self.statuses)}")
        print(f"Expected status codes: {sorted(self.expected_statuses)}")
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
        print(f"Expected responses: {ok}/{self.n} ({100 * ok / self.n:.1f}%)")
        print(f"Result: {'PASS' if self.passed and ok == self.n else 'FAIL'}")


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
    expected_statuses: set[int] | None = None,
) -> Report:
    if n < 1 or concurrency < 1:
        raise ValueError("n and concurrency must be positive")
    report = Report(
        name=name,
        n=n,
        concurrency=concurrency,
        expected_statuses=expected_statuses or {200},
    )
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


def parse_statuses(value: str) -> set[int]:
    try:
        statuses = {int(part.strip()) for part in value.split(",") if part.strip()}
    except ValueError as exc:
        raise argparse.ArgumentTypeError("statuses must be comma-separated integers") from exc
    if not statuses or any(code < 100 or code > 599 for code in statuses):
        raise argparse.ArgumentTypeError("statuses must contain HTTP codes from 100 to 599")
    return statuses


def target_is_loopback(url: str) -> bool:
    hostname = urllib.parse.urlsplit(url).hostname
    return hostname in {"127.0.0.1", "::1", "localhost", "host.docker.internal"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=os.environ.get("LOAD_BASE", "http://127.0.0.1:8018"),
        help="API origin; defaults to local Docker Compose port 8018",
    )
    parser.add_argument("--path", default="/health")
    parser.add_argument("--method", choices=("GET", "POST", "PUT", "PATCH", "DELETE"), default="GET")
    parser.add_argument("--body", help="UTF-8 request body; Content-Type is application/json")
    parser.add_argument("-n", "--requests", type=int, default=2000)
    parser.add_argument("-c", "--concurrency", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--expect", type=parse_statuses, default={200})
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="allow a non-loopback target; use only for an approved environment",
    )
    args = parser.parse_args()

    base = args.base.rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        parser.error(f"invalid --base: {base!r}")
    if not args.allow_remote and not target_is_loopback(base):
        parser.error("non-loopback targets require --allow-remote")
    if args.requests < 1 or args.concurrency < 1:
        parser.error("--requests and --concurrency must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    path = args.path if args.path.startswith("/") else f"/{args.path}"
    url = f"{base}{path}"
    body = args.body.encode() if args.body is not None else None
    report = run_load(
        f"{args.method} {path}",
        url,
        args.requests,
        args.concurrency,
        args.method,
        body,
        args.timeout,
        args.expect,
    )
    report.print()

    postflight = one_request("GET", f"{base}/health", None, min(args.timeout, 5))
    print(
        f"Postflight health: status={postflight.status} "
        f"latency={postflight.latency_ms:.1f}ms"
    )
    if not report.passed or sum(report.statuses.values()) != args.requests:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
