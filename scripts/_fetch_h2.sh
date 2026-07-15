#!/bin/bash
set -euo pipefail
docker cp /tmp/dump_h.py astro-tma-backend-1:/tmp/dump_h.py
docker exec -w /app -e PYTHONPATH=/app astro-tma-backend-1 python /tmp/dump_h.py > /tmp/horoscopes_today.json
wc -c /tmp/horoscopes_today.json
python3 <<'PY'
import json
d=json.load(open("/tmp/horoscopes_today.json", encoding="utf-8"))
print("date", d["date"])
print("cached", sum(1 for v in d["signs"].values() if v["len"] > 0), "/12")
for s,v in d["signs"].items():
    print(f"\n=== {v['ru']} ({s}) len={v['len']} ===")
    print(v["text_ru"])
PY
echo
echo "=== LOGS ==="
docker logs astro-tma-backend-1 --since 48h 2>&1 | grep -E 'horoscopes_generating|horoscope_ok|horoscope_failed|horoscopes_done|daily_push_done' | tail -60 || true
echo "=== PUSH DB ==="
docker exec astro-tma-postgres-1 psql -U astro -d astro_tma -c "SELECT type, status, count(*) FROM notification_logs WHERE created_at >= CURRENT_DATE GROUP BY 1,2 ORDER BY 1,2;"
