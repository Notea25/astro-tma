#!/bin/bash
set -euo pipefail
NET=$(docker inspect astro-tma-backend-1 --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')
echo "NETWORK=$NET"

run_probe() {
  docker run --rm --network "$NET" \
    -v /tmp/load_test_async.py:/load.py:ro \
    python:3.12-slim python /load.py \
    --base http://backend:8000 --allow-remote "$@"
}

echo "=== 1. /health c=50 n=2000 ==="
run_probe --path /health -n 2000 -c 50 --expect 200

echo "=== 2. /health c=100 n=5000 ==="
run_probe --path /health -n 5000 -c 100 --expect 200

echo "=== 3. /health sustained c=150 n=10000 ==="
run_probe --path /health -n 10000 -c 150 --expect 200

echo "=== 4. /api/payments/return c=40 n=1000 ==="
run_probe --path /api/payments/return -n 1000 -c 40 --expect 200

echo "=== 5. POST /api/users/me without auth c=50 n=2000 ==="
run_probe --path /api/users/me --method POST --body '{}' -n 2000 -c 50 --expect 401

echo "=== 6. GET /api/glossary without auth c=50 n=2000 ==="
run_probe --path /api/glossary -n 2000 -c 50 --expect 401

echo "=== 7. GET /api/news without auth c=80 n=3000 ==="
run_probe --path /api/news -n 3000 -c 80 --expect 401

echo "=== AFTER STATS ==="
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'
curl -s https://ip-194-99-21-53-142250.vps.hosted-by-mvps.net/health || true
