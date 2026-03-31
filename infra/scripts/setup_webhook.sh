#!/bin/bash
# Reads .env and registers the Telegram webhook automatically
set -euo pipefail

# Load .env
export $(grep -v '^#' .env | grep -v '^$' | xargs)

echo "=== Registering Telegram webhook ==="
echo "Bot token: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "Webhook URL: $TELEGRAM_WEBHOOK_URL"
echo "Secret: ${TELEGRAM_WEBHOOK_SECRET:0:8}..."
echo ""

RESPONSE=$(curl -s -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${TELEGRAM_WEBHOOK_URL}\",
    \"secret_token\": \"${TELEGRAM_WEBHOOK_SECRET}\",
    \"allowed_updates\": [\"message\", \"pre_checkout_query\", \"callback_query\"]
  }")

echo "Telegram response: $RESPONSE"

# Verify
echo ""
echo "=== Verifying bot info ==="
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" | python3 -m json.tool
