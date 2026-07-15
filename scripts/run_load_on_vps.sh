#!/bin/bash
set -euo pipefail
NET=$(docker inspect astro-tma-backend-1 --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')
echo "NETWORK=$NET"

# Patch targets: backend service on compose network
sed 's|http://127.0.0.1:8000|http://backend:8000|g' /tmp/load_test_async.py > /tmp/load_direct.py

# Only run direct backend scenarios (1-5) + skip broken public postflight
python3 - <<'PY'
from pathlib import Path
src = Path("/tmp/load_direct.py").read_text()
# trim scenarios to direct-only by editing the list start marker
old = '''scenarios = [
        ("1. Direct /health c=50 n=2000", f"{BASE}/health", 2000, 50, "GET", None),
        ("2. Direct /health c=100 n=5000", f"{BASE}/health", 5000, 100, "GET", None),
        ("3. Direct /api/payments/return c=40 n=1000", f"{BASE}/api/payments/return", 1000, 40, "GET", None),
        ("4. Direct POST /api/users/me (401) c=50 n=2000", f"{BASE}/api/users/me", 2000, 50, "POST", b"{}"),
        ("5. Direct GET /api/glossary (401) c=50 n=2000", f"{BASE}/api/glossary", 2000, 50, "GET", None),
        ("6. Nginx HTTPS /health c=30 n=1000", f"{PUBLIC}/health", 1000, 30, "GET", None),
        ("7. Nginx HTTPS /api/glossary (rate-limit) c=40 n=200", f"{PUBLIC}/api/glossary", 200, 40, "GET", None),
    ]'''
new = '''scenarios = [
        ("1. Direct /health c=50 n=2000", f"{BASE}/health", 2000, 50, "GET", None),
        ("2. Direct /health c=100 n=5000", f"{BASE}/health", 5000, 100, "GET", None),
        ("3. Direct /health sustained c=150 n=10000", f"{BASE}/health", 10000, 150, "GET", None),
        ("4. Direct /api/payments/return c=40 n=1000", f"{BASE}/api/payments/return", 1000, 40, "GET", None),
        ("5. Direct POST /api/users/me (401) c=50 n=2000", f"{BASE}/api/users/me", 2000, 50, "POST", b"{}"),
        ("6. Direct GET /api/glossary (401) c=50 n=2000", f"{BASE}/api/glossary", 2000, 50, "GET", None),
        ("7. Direct GET /api/news (401) c=80 n=3000", f"{BASE}/api/news", 3000, 80, "GET", None),
    ]'''
if old not in src:
    raise SystemExit("scenario block not found")
Path("/tmp/load_direct.py").write_text(src.replace(old, new))
print("scenarios patched")
PY

echo "=== RUNNING IN-NETWORK LOAD ==="
docker run --rm --network "$NET" -v /tmp/load_direct.py:/load.py:ro python:3.12-slim python /load.py

echo "=== AFTER STATS ==="
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'
curl -s https://ip-194-99-21-53-142250.vps.hosted-by-mvps.net/health || true
