#!/bin/bash
# ── First-time deploy script ───────────────────────────────────────────────────
# Run this on your VPS after cloning the repo.
# Prerequisites: Ubuntu 24.04, root access, domain pointed to this IP.
set -euo pipefail

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
  echo "Usage: bash deploy_first_time.sh api.your-domain.com"
  exit 1
fi

echo "=== [1/6] Installing Docker ==="
apt-get update -qq
apt-get install -y docker.io docker-compose-v2 certbot python3-certbot-nginx git curl

echo "=== [2/6] Getting SSL certificate ==="
certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos -m admin@"$DOMAIN" || \
  echo "⚠️  certbot failed — make sure port 80 is open and domain points here"

echo "=== [3/6] Updating nginx config ==="
sed -i "s/api.YOUR_DOMAIN.com/$DOMAIN/g" infra/nginx/conf.d/astro.conf

echo "=== [4/6] Updating .env webhook URL ==="
sed -i "s|https://api.YOUR_DOMAIN.com|https://$DOMAIN|g" .env

echo "=== [5/6] Starting services ==="
docker compose up -d

echo "=== [6/6] Waiting for postgres and running migrations ==="
sleep 8
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python infra/scripts/seed_tarot.py

echo ""
echo "✅ Deploy complete!"
echo "   Backend API: https://$DOMAIN/health"
echo ""
echo "Now register the Telegram webhook:"
echo "   bash infra/scripts/setup_webhook.sh"
