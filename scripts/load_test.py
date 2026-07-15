#!/usr/bin/env python3
"""Production load test — safe endpoints only (no payments create, no LLM)."""
from __future__ import annotations

import os
import subprocess

KEY = os.path.expanduser("~/.ssh/astro_tma_deploy")
HOST = "194.99.21.53"


def ssh(cmd: str, timeout: int = 300) -> str:
    r = subprocess.run(
        [
            "ssh",
            "-i",
            KEY,
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            f"root@{HOST}",
            cmd,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
    return out.strip()


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    if os.environ.get("ALLOW_PRODUCTION_LOAD") != "1":
        raise SystemExit(
            "Refusing the hard-coded production target. "
            "Set ALLOW_PRODUCTION_LOAD=1 only during an approved load-test window."
        )

    section("0. Preflight — hey + docker stats")
    print(ssh("hey -n 1 -c 1 http://127.0.0.1:8000/health 2>&1 | tail -20"))
    print(ssh("docker stats --no-stream --format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}'"))

    # Backend direct — finds real Uvicorn capacity without nginx limit_req
    section("1. Backend DIRECT /health — 2000 req, c=50")
    print(ssh("hey -n 2000 -c 50 -t 10 http://127.0.0.1:8000/health 2>&1"))

    section("2. Backend DIRECT /health — 5000 req, c=100")
    print(ssh("hey -n 5000 -c 100 -t 10 http://127.0.0.1:8000/health 2>&1"))

    section("3. Backend DIRECT /api/payments/return — 1000 req, c=40")
    print(ssh("hey -n 1000 -c 40 -t 10 http://127.0.0.1:8000/api/payments/return 2>&1"))

    # Auth middleware cost (valid JSON 401 responses)
    section("4. Backend DIRECT /api/users/me (expected 401) — 2000 req, c=50")
    print(
        ssh(
            "hey -n 2000 -c 50 -m POST -T 'application/json' "
            "-d '{}' http://127.0.0.1:8000/api/users/me 2>&1"
        )
    )

    # Through nginx from VPS (same host IP — rate limit applies to remote addr)
    section("5. Via nginx HTTPS /health — 1000 req, c=30")
    print(
        ssh(
            "hey -n 1000 -c 30 -t 15 "
            "https://ip-194-99-21-53-142250.vps.hosted-by-mvps.net/health 2>&1"
        )
    )

    # Stress rate limiter on API
    section("6. Via nginx /api/glossary (401 + rate limit) — 200 req, c=40")
    print(
        ssh(
            "hey -n 200 -c 40 -t 15 "
            "https://ip-194-99-21-53-142250.vps.hosted-by-mvps.net/api/glossary 2>&1"
        )
    )

    section("7. Postflight — health + docker stats + recent errors")
    print(ssh("curl -s http://127.0.0.1:8000/health"))
    print(ssh("docker stats --no-stream --format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}'"))
    print(
        ssh(
            "docker logs astro-tma-backend-1 --since 5m 2>&1 | "
            "grep -E 'error|Error|Traceback|503|502' | tail -20 || echo '(no errors)'"
        )
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
