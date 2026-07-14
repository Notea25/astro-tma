#!/bin/bash
# Deploy nginx rate bump + run battle load (docker network).
set -euo pipefail
cd /opt/astro-tma

echo "== Pull nginx configs =="
git fetch origin main
git checkout origin/main -- infra/nginx/nginx.conf infra/nginx/conf.d/astro.conf

echo "== Reload nginx =="
docker compose -f docker-compose.yml exec -T nginx nginx -t
docker compose -f docker-compose.yml exec -T nginx nginx -s reload

NET=$(docker inspect astro-tma-backend-1 --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')
echo "NETWORK=$NET"

# Load bot token without printing secrets
set -a
# shellcheck disable=SC1091
source /opt/astro-tma/.env
set +a

cp /tmp/battle_load.py /tmp/battle_load_run.py

echo "== Battle load: 50 users, concurrency 20 (docker network) =="
docker run --rm --network "$NET" \
  -e TELEGRAM_BOT_TOKEN \
  -e LOAD_BASE=http://backend:8000 \
  -e LOAD_USERS=50 \
  -e LOAD_CONCURRENCY=20 \
  -e LOAD_USER_BASE=9100000000 \
  -v /tmp/battle_load_run.py:/battle.py:ro \
  python:3.12-slim python /battle.py

echo "== Battle load: 100 users, concurrency 40 =="
docker run --rm --network "$NET" \
  -e TELEGRAM_BOT_TOKEN \
  -e LOAD_BASE=http://backend:8000 \
  -e LOAD_USERS=100 \
  -e LOAD_CONCURRENCY=40 \
  -e LOAD_USER_BASE=9200000000 \
  -v /tmp/battle_load_run.py:/battle.py:ro \
  python:3.12-slim python /battle.py

echo "== Public HTTPS spot-check (10 users through nginx) =="
docker run --rm --network "$NET" \
  -e TELEGRAM_BOT_TOKEN \
  -e LOAD_BASE=https://ip-194-99-21-53-142250.vps.hosted-by-mvps.net \
  -e LOAD_USERS=10 \
  -e LOAD_CONCURRENCY=5 \
  -e LOAD_USER_BASE=9300000000 \
  -v /tmp/battle_load_run.py:/battle.py:ro \
  python:3.12-slim python /battle.py

echo "== Postflight =="
curl -s https://ip-194-99-21-53-142250.vps.hosted-by-mvps.net/health
echo
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'
docker logs astro-tma-backend-1 --since 10m 2>&1 | grep -E '"level": "error"|Traceback' | tail -20 || echo '(no errors)'
