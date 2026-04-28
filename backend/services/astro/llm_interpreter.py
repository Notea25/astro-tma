"""
LLM-based natal chart interpretation via Anthropic Claude.

Generates a holistic, personal reading in Russian from raw chart data.
Result is cached by the caller — this function always calls the API.
"""

from core.logging import get_logger
from services.llm_utils import first_text_block

log = get_logger(__name__)

_PLANET_RU: dict[str, str] = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий",
    "venus": "Венера", "mars": "Марс", "jupiter": "Юпитер",
    "saturn": "Сатурн", "uranus": "Уран", "neptune": "Нептун",
    "pluto": "Плутон",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение", "trine": "трин",
    "square": "квадрат", "opposition": "оппозиция", "sextile": "секстиль",
}


def _build_prompt(
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    planets: dict,
    aspects: list,
) -> str:
    planet_lines: list[str] = []
    for key, ru_name in _PLANET_RU.items():
        if key in planets:
            p = planets[key]
            retro = " (ретроградный)" if p.get("retrograde") else ""
            planet_lines.append(
                f"- {ru_name}: {p.get('sign_ru') or p.get('sign', '?')} "
                f"{p.get('sign_degree', 0):.0f}°, {p.get('house', '?')}-й дом{retro}"
            )

    sorted_aspects = sorted(aspects, key=lambda a: a.get("orb", 99))[:6]
    aspect_lines: list[str] = []
    for a in sorted_aspects:
        p1 = _PLANET_RU.get(a.get("p1", "").lower(), a.get("p1", ""))
        p2 = _PLANET_RU.get(a.get("p2", "").lower(), a.get("p2", ""))
        asp = _ASPECT_RU.get(a.get("aspect", ""), a.get("aspect", ""))
        orb = a.get("orb", 0)
        aspect_lines.append(f"- {p1} — {asp} — {p2} (орб {orb:.1f}°)")

    asc_line = f"Асцендент: {ascendant_sign}" if ascendant_sign else ""

    return f"""Ты — опытный астролог, составляющий натальные карты. Отвечай только на русском языке.

Данные натальной карты:
Солнце: {sun_sign}
Луна: {moon_sign}
{asc_line}

Планеты:
{chr(10).join(planet_lines)}

Ключевые аспекты:
{chr(10).join(aspect_lines) if aspect_lines else '— нет данных'}

Напиши личную интерпретацию натальной карты (350–500 слов). Структура:
1. Ядро личности (Солнце, Луна, Асцендент) — 2–3 предложения
2. Ум и коммуникация (Меркурий) — 1–2 предложения
3. Любовь и ценности (Венера) — 1–2 предложения
4. Энергия и воля (Марс) — 1–2 предложения
5. Удача и вызовы (Юпитер, Сатурн) — 2 предложения
6. Ключевые аспекты и их влияние — 2–3 предложения
7. Совет и жизненный путь — 1–2 предложения

Пиши тепло, образно, конкретно. Говори от второго лица («вы», «ваш»). Избегай банальных фраз."""


async def generate_natal_reading(
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    planets: dict,
    aspects: list,
    api_key: str,
) -> str:
    """
    Call Claude to generate a natal chart reading in Russian.
    Raises on API error — caller should catch and handle gracefully.
    """
    import anthropic

    prompt = _build_prompt(sun_sign, moon_sign, ascendant_sign, planets, aspects)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    text = first_text_block(message.content)
    log.info("llm_interpreter.done", chars=len(text))
    return text
