from services.astro.transits import get_current_sky
import json
sky = get_current_sky()
print(json.dumps({k: {"sign": v.get("sign"), "deg": round(float(v.get("degree", 0)) % 30, 1)} for k, v in sky.items()}, ensure_ascii=False, indent=2))
