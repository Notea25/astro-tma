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

Напиши личную интерпретацию натальной карты (550–800 слов) в семи разделах. Каждый раздел начни с названия, обёрнутого в **двойные звёздочки**, на отдельной строке, и затем продолжи обычным текстом (2-4 предложения). Это критически важно: парсер на фронте разбивает текст по `**Название**`, и без них всё валится в один блок.

Используй ровно эти семь заголовков:

**Ядро личности**
2–3 предложения о Солнце, Луне и Асценденте — какой у вас тип энергии, эмоциональный мир, первое впечатление.

**Ум и коммуникация**
1–2 предложения о Меркурии — стиль мышления, обучение, общение.

**Любовь и ценности**
1–2 предложения о Венере — что вы любите, как притягиваете людей, ваша эстетика.

**Энергия и воля**
1–2 предложения о Марсе — как вы действуете, отстаиваете границы, идёте к целям.

**Удача и вызовы**
2 предложения о Юпитере (рост, везение) и Сатурне (дисциплина, уроки).

**Ключевые аспекты**
2–3 предложения о двух-трёх важнейших аспектах из списка выше — как они окрашивают характер.

**Совет и путь**
1–2 предложения с практическим советом и направлением развития.

Пиши тепло, образно, конкретно. Говори от второго лица («вы», «ваш»). Избегай банальных фраз. Кроме `**заголовка раздела**` другую markdown-разметку не используй — никаких #, списков, кода."""


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
