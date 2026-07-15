#!/usr/bin/env bash
# Run on VPS from /opt/astro-tma: harden prod compose + smoke checks.
set -euo pipefail
cd /opt/astro-tma

TS="$(date -u +%Y%m%d_%H%M%S)"
BACKUP_DIR="/opt/astro-tma/backups"
mkdir -p "$BACKUP_DIR" /root/astro-backups

echo "=== 1) pg_dump ==="
PGPASS="$(grep -E '^POSTGRES_PASSWORD=' .env | head -1 | cut -d= -f2-)"
docker exec -e PGPASSWORD="$PGPASS" astro-tma-postgres-1 \
  pg_dump -U astro -d astro_tma --no-owner --no-acl \
  > "$BACKUP_DIR/pre_launch_${TS}.sql"
gzip -f "$BACKUP_DIR/pre_launch_${TS}.sql"
cp -f "$BACKUP_DIR/pre_launch_${TS}.sql.gz" "/root/astro-backups/pre_launch_${TS}.sql.gz"
ls -lh "$BACKUP_DIR/pre_launch_${TS}.sql.gz" "/root/astro-backups/pre_launch_${TS}.sql.gz"

echo "=== 2) disable override on VPS ==="
if [[ -f docker-compose.override.yml ]]; then
  mv -f docker-compose.override.yml "docker-compose.override.yml.disabled_${TS}"
  echo "renamed override -> docker-compose.override.yml.disabled_${TS}"
else
  echo "override already absent"
fi

echo "=== 3) patch compose: drop bind mounts ==="
python3 - <<'PY'
from pathlib import Path
p = Path("docker-compose.yml")
text = p.read_text()
needle = "./backend:/app"
if needle not in text:
    print("bind mounts already absent")
else:
    out = []
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        # drop a 2-line volumes block that only mounts ./backend:/app
        if (
            lines[i].strip() == "volumes:"
            and i + 1 < len(lines)
            and "./backend:/app" in lines[i + 1]
        ):
            # skip volumes: and the mount line (and blank line after if any)
            i += 2
            if i < len(lines) and lines[i].strip() == "":
                i += 1
            continue
        out.append(lines[i])
        i += 1
    new = "".join(out)
    if needle in new:
        raise SystemExit("bind mount still present after patch — abort")
    p.write_text(new)
    print("removed ./backend:/app volumes from docker-compose.yml")
PY

echo "=== 4) rebuild + recreate (compose file only) ==="
docker compose -f docker-compose.yml build backend worker
docker compose -f docker-compose.yml up -d --force-recreate backend worker
docker compose -f docker-compose.yml up -d nginx
echo "waiting for backend..."
for i in $(seq 1 30); do
  if curl -skf https://127.0.0.1/health >/dev/null 2>&1; then
    echo "backend up after ${i}s"
    break
  fi
  sleep 2
  if [[ "$i" -eq 30 ]]; then
    echo "backend did not become healthy"
    docker compose -f docker-compose.yml logs --tail=80 backend
    exit 1
  fi
done

echo "=== 5) container sanity ==="
docker compose -f docker-compose.yml ps
echo "--- mounts backend ---"
docker inspect astro-tma-backend-1 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}' || true
echo "--- published host ports (db/redis should be empty) ---"
ss -tlnp | grep -E ':(5432|5433|6379|6380|8018)\s' || echo "OK: no db/redis/dev ports"

echo "=== 6) smoke checks ==="
docker exec astro-tma-backend-1 sh -c 'echo APP_ENV=$APP_ENV; echo APP_DEBUG=$APP_DEBUG; echo AUTH_BYPASS=${AUTH_BYPASS:-unset}'

curl -sk https://127.0.0.1/health -o /tmp/health.json
python3 - <<'PY'
import json
h = json.load(open("/tmp/health.json"))
assert h.get("status") == "ok", h
assert h.get("env") == "production", h
pay = h.get("payments") or {}
assert pay.get("yukassa_configured") is True, h
assert pay.get("yukassa_receipt_ready") is True, h
print("health OK:", h)
PY

USER="$(grep -E '^ADMIN_USERNAME=' .env | head -1 | cut -d= -f2-)"
PASS="$(grep -E '^ADMIN_PASSWORD=' .env | head -1 | cut -d= -f2-)"
curl -sk -u "${USER}:${PASS}" https://127.0.0.1/api/admin/products -o /tmp/products.json
python3 - <<'PY'
import json
expected = {
  "natal_full": (149, 490),
  "destiny_matrix_full": (199, 690),
  "synastry": (99, 390),
  "subscription_month": (249, 790),
  "subscription_year": (1990, 5900),
}
data = json.load(open("/tmp/products.json"))
by = {p["id"]: p for p in data["products"]}
for pid, (stars, rub) in expected.items():
    p = by[pid]
    assert p["current_stars"] == stars, (pid, p)
    assert p["current_rub"] == rub, (pid, p)
print("prices OK")
PY

TOKEN="$(grep -E '^TELEGRAM_BOT_TOKEN=' .env | head -1 | cut -d= -f2-)"
curl -sS "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" -o /tmp/webhook.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/webhook.json"))
assert d.get("ok") is True, d
r = d["result"]
assert "/api/payments/webhook" in r.get("url", ""), r
assert r.get("pending_update_count", 0) == 0, r
print("telegram webhook OK:", r["url"])
PY

docker exec astro-tma-postgres-1 pg_isready -U astro -d astro_tma
docker exec astro-tma-redis-1 redis-cli ping | grep -qi pong

CODE="$(curl -sk -o /tmp/me.json -w '%{http_code}' -X POST https://127.0.0.1/api/users/me -H 'Content-Type: application/json' -d '{}')"
echo "POST /api/users/me no auth -> HTTP $CODE"
[[ "$CODE" == "401" || "$CODE" == "403" ]]

CODE2="$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1/api/glossary)"
echo "GET /api/glossary -> HTTP $CODE2"
[[ "$CODE2" == "200" || "$CODE2" == "401" || "$CODE2" == "403" ]]

FCODE="$(curl -sS -o /dev/null -w '%{http_code}' https://astro-tma.vercel.app/)"
echo "frontend vercel -> HTTP $FCODE"
[[ "$FCODE" == "200" ]]

# signed-initData smoke via in-container python if BOT token available
python3 - <<'PY'
"""Minimal authenticated API smoke: forge Telegram WebApp initData."""
import hashlib, hmac, json, ssl, time, urllib.parse, urllib.request
from pathlib import Path

env = {}
for line in Path("/opt/astro-tma/.env").read_text().splitlines():
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip()

bot_token = env["TELEGRAM_BOT_TOKEN"]
user = {"id": 900001015, "first_name": "Smoke", "username": "smoke_prod_check"}
auth_date = str(int(time.time()))
pairs = {
    "auth_date": auth_date,
    "query_id": "AAsmoke",
    "user": json.dumps(user, separators=(",", ":")),
}
data_check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
pairs["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
init_data = urllib.parse.urlencode(pairs)

ctx = ssl._create_unverified_context()
req = urllib.request.Request(
    "https://127.0.0.1/api/users/me",
    data=b"{}",
    headers={
        "Content-Type": "application/json",
        "X-Init-Data": init_data,
    },
    method="POST",
)
with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
    body = json.loads(resp.read().decode())
    assert resp.status == 200, body
    print("auth users/me OK:", {"tg_id": body.get("telegram_id") or body.get("tg_id") or body.get("id"), "keys": list(body)[:8]})

req2 = urllib.request.Request(
    "https://127.0.0.1/api/horoscope/today",
    headers={"X-Init-Data": init_data},
)
with urllib.request.urlopen(req2, context=ctx, timeout=60) as resp:
    body = json.loads(resp.read().decode())
    assert resp.status == 200, body
    print("horoscope/today OK:", list(body)[:10])

req3 = urllib.request.Request(
    "https://127.0.0.1/api/payments/products",
    headers={"X-Init-Data": init_data},
)
with urllib.request.urlopen(req3, context=ctx, timeout=30) as resp:
    body = json.loads(resp.read().decode())
    assert resp.status == 200, body
    products = body.get("products") or body
    print("payments/products OK, count=", len(products) if isinstance(products, list) else type(products))
PY

docker exec -e PGPASSWORD="$PGPASS" astro-tma-postgres-1 \
  psql -U astro -d astro_tma -c "SELECT (SELECT count(*) FROM users) AS users, (SELECT count(*) FROM purchases) AS purchases;"

echo "=== ALL SMOKE CHECKS PASSED ==="
