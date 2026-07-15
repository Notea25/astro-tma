#!/bin/bash
set -euo pipefail
TODAY=$(date -u +%F)
VERSION="2026-07-safety-v1"
SIGNS="aries taurus gemini cancer leo virgo libra scorpio sagittarius capricorn aquarius pisces"
declare -A RU=(
  [aries]=Овен [taurus]=Телец [gemini]=Близнецы [cancer]=Рак
  [leo]=Лев [virgo]=Дева [libra]=Весы [scorpio]=Скорпион
  [sagittarius]=Стрелец [capricorn]=Козерог [aquarius]=Водолей [pisces]=Рыбы
)

echo "TODAY=$TODAY"
echo "=== TEXTS ==="
python3 - <<PY
import json, subprocess
today = "$TODAY"
version = "$VERSION"
signs = """$SIGNS""".split()
ru = {
  "aries":"Овен","taurus":"Телец","gemini":"Близнецы","cancer":"Рак",
  "leo":"Лев","virgo":"Дева","libra":"Весы","scorpio":"Скорпион",
  "sagittarius":"Стрелец","capricorn":"Козерог","aquarius":"Водолей","pisces":"Рыбы",
}
out = {"date": today, "signs": {}}
for s in signs:
    key = f"horoscope:{version}:{s}:{today}:today"
    raw = subprocess.check_output(["docker","exec","astro-tma-redis-1","redis-cli","GET",key], text=True)
    raw = raw.strip()
    text = ""
    if raw and raw != "(nil)":
        try:
            payload = json.loads(raw)
            text = payload.get("text_ru") or ""
        except Exception:
            text = raw
    out["signs"][s] = {"ru": ru[s], "text_ru": text, "len": len(text), "key": key}
    print(f"\\n=== {ru[s]} ({s}) len={len(text)} ===")
    print(text or "(empty)")
open("/tmp/horoscopes_today.json","w",encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
print("\\nSaved /tmp/horoscopes_today.json")
print("cached", sum(1 for v in out["signs"].values() if v["len"]>0), "/12")
PY

echo "=== LOGS ==="
docker logs astro-tma-backend-1 --since 48h 2>&1 | grep -E 'horoscopes_generating|horoscope_ok|horoscope_failed|horoscopes_done|daily_push_done' | tail -60 || true
echo "=== PUSH DB ==="
docker exec astro-tma-postgres-1 psql -U astro -d astro_tma -c "SELECT type, status, count(*) FROM notification_logs WHERE created_at >= CURRENT_DATE GROUP BY 1,2 ORDER BY 1,2;"
