#!/bin/bash
set -euo pipefail
docker cp /tmp/dump_h.py astro-tma-backend-1:/tmp/dump_h.py
docker exec -w /app astro-tma-backend-1 python /tmp/dump_h.py > /tmp/horoscopes_today.json
echo "=== JSON ==="
cat /tmp/horoscopes_today.json
echo
echo "=== LOGS ==="
docker logs astro-tma-backend-1 --since 48h 2>&1 | grep -E 'scheduler.horoscope|horoscopes_generating|horoscopes_done|daily_push_done|llm_horoscope|horoscope_ok|horoscope_failed' | tail -60
echo "=== PUSH DB ==="
docker exec astro-tma-postgres-1 psql -U astro -d astro_tma -c "SELECT type, status, count(*) FROM notification_logs WHERE created_at >= CURRENT_DATE GROUP BY 1,2 ORDER BY 1,2;"
