#!/bin/bash
# First-time server setup script. Run as root on a fresh Ubuntu 24.04 VPS.
set -euo pipefail

echo "=== Astro TMA — Server Setup ==="

# Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker $SUDO_USER

# Certbot (SSL)
apt-get install -y certbot python3-certbot-nginx

# Clone repo (replace with your repo URL)
# git clone https://github.com/YOUR_USER/astro-tma.git /opt/astro-tma
# cd /opt/astro-tma

echo "Next steps:"
echo "1. Copy .env.example to .env and fill in all values"
echo "2. certbot --nginx -d api.yourdomain.com"
echo "3. docker compose up -d"
echo "4. docker compose exec backend alembic upgrade head"
echo "5. docker compose exec backend python -m services.tarot.seed  (seed tarot cards)"
echo "6. Set Telegram webhook: https://api.telegram.org/botTOKEN/setWebhook?url=WEBHOOK_URL&secret_token=SECRET"
