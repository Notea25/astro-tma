import asyncio
import json
from datetime import date

from core.cache import cache_get, key_horoscope

SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]
RU = {
    "aries": "Овен", "taurus": "Телец", "gemini": "Близнецы",
    "cancer": "Рак", "leo": "Лев", "virgo": "Дева",
    "libra": "Весы", "scorpio": "Скорпион", "sagittarius": "Стрелец",
    "capricorn": "Козерог", "aquarius": "Водолей", "pisces": "Рыбы",
}


async def main() -> None:
    today = date.today().isoformat()
    out: dict = {"date": today, "signs": {}}
    for s in SIGNS:
        v = await cache_get(key_horoscope(s, today, "today"))
        text = ""
        if isinstance(v, dict):
            text = v.get("text_ru") or ""
        out["signs"][s] = {"ru": RU[s], "text_ru": text, "len": len(text)}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
