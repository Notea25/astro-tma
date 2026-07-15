#!/usr/bin/env python3
"""Fetch today's cached daily horoscopes from production Redis."""
from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from datetime import datetime, timezone

KEYS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]
SIGN_RU = {
    "aries": "Овен", "taurus": "Телец", "gemini": "Близнецы",
    "cancer": "Рак", "leo": "Лев", "virgo": "Дева",
    "libra": "Весы", "scorpio": "Скорпион", "sagittarius": "Стрелец",
    "capricorn": "Козерог", "aquarius": "Водолей", "pisces": "Рыбы",
}


def main() -> None:
    import paramiko

    host = "194.99.21.53"
    key = os.path.expanduser("~/.ssh/astro_tma_deploy")
    today = date.today().isoformat()

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username="root", key_filename=key, timeout=30)

    def run(cmd: str) -> str:
        _, out, err = c.exec_command(cmd, timeout=60)
        return out.read().decode("utf-8", errors="replace") + err.read().decode(
            "utf-8", errors="replace"
        )

    print(f"=== TODAY={today} UTC now={datetime.now(timezone.utc).isoformat()} ===\n")

    # Redis keys — match backend key_horoscope format
    print("=== Redis keys present ===")
    print(
        run(
            f'docker exec astro-tma-redis-1 redis-cli --scan --pattern "*{today}*" | head -50'
        )
    )

    # Pull via python inside backend (uses same key builder)
    script = f"""
import asyncio, json
from datetime import date
from core.cache import cache_get, key_horoscope

SIGNS = {KEYS!r}
RU = {SIGN_RU!r}

async def main():
    today = date.today().isoformat()
    out = {{}}
    for s in SIGNS:
        k = key_horoscope(s, today, "today")
        v = await cache_get(k)
        out[s] = {{"key": k, "cached": v is not None, "payload": v}}
    print(json.dumps({{"date": today, "signs": out}}, ensure_ascii=False, default=str))

asyncio.run(main())
"""
    run("cat > /tmp/dump_horoscopes.py << 'EOF'\n" + script + "\nEOF")
    raw = run(
        "docker compose -f /opt/astro-tma/docker-compose.yml exec -T backend "
        "python /tmp/dump_horoscopes.py 2>/dev/null || "
        "docker compose -f /opt/astro-tma/docker-compose.yml exec -T -w /app backend "
        "python -c \"import pathlib; pathlib.Path('/tmp/dump_horoscopes.py').write_text(open('/tmp/dump_horoscopes.py').read())\" 2>&1; "
        "docker cp /tmp/dump_horoscopes.py astro-tma-backend-1:/tmp/dump_horoscopes.py && "
        "docker exec -w /app astro-tma-backend-1 python /tmp/dump_horoscopes.py"
    )
    # save full dump
    pathlib_write = "/tmp/astro_horoscopes_today.json"
    # extract JSON line
    lines = [ln for ln in raw.splitlines() if ln.strip().startswith("{")]
    if lines:
        open(pathlib_write.replace("/tmp/", "C:/Users/Anton/AppData/Local/Temp/"), "w", encoding="utf-8").write(lines[-1])
        print("JSON dumped locally via print below\n")
        data = json.loads(lines[-1])
        for s, info in data["signs"].items():
            print(f"\n--- {RU[s]} ({s}) cached={info['cached']} ---")
            p = info.get("payload") or {}
            if isinstance(p, dict):
                text = p.get("text_ru") or p.get("text") or ""
            else:
                text = str(p)
            print(text[:800] if text else "(empty)")
        open(
            r"C:\Users\Anton\Projects\astro-tma\scripts\_horoscopes_today.json",
            "w",
            encoding="utf-8",
        ).write(json.dumps(data, ensure_ascii=False, indent=2))
        print("\nSaved scripts/_horoscopes_today.json")
    else:
        print("RAW OUTPUT:\n", raw[:3000])

    print("\n=== Recent scheduler logs ===")
    print(
        run(
            "docker logs astro-tma-backend-1 --since 24h 2>&1 | "
            "grep -E 'horoscope|daily_push|scheduler\\.daily' | tail -40"
        )
    )
    c.close()


if __name__ == "__main__":
    main()
