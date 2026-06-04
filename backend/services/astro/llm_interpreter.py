"""
LLM-based natal chart interpretation via Anthropic Claude.

Generates a holistic, personal reading in Russian from raw chart data.
Result is cached by the caller — this function always calls the API.
"""

from __future__ import annotations

from core.logging import get_logger
from services.llm_utils import first_text_block

log = get_logger(__name__)

from services.astro.planet_names import PLANET_RU as _PLANET_RU  # noqa: E402

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение",
    "trine": "трин",
    "square": "квадрат",
    "opposition": "оппозиция",
    "sextile": "секстиль",
}


def _build_prompt(
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    planets: dict,
    aspects: list,
    gender: str | None = None,
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
    gender_directive = ""
    if gender in ("male", "female"):
        ru = "мужчина" if gender == "male" else "женщина"
        forms = (
            "все формы глаголов прошедшего времени, прилагательных и причастий — в мужском роде"
            if gender == "male"
            else "все формы глаголов прошедшего времени, прилагательных и причастий — в женском роде"
        )
        gender_directive = (
            f"\nПол читателя: {ru.upper()}. {forms.upper()} "
            "(например: «вы сделали», «вы сильный/сильная», «настоящий/настоящая»).\n"
        )

    nodes_line = ""
    for key, label in (
        ("true_north_lunar_node", "Раху (Северный узел)"),
        ("mean_north_lunar_node", "Раху (Северный узел)"),
        ("true_south_lunar_node", "Кету (Южный узел)"),
        ("mean_south_lunar_node", "Кету (Южный узел)"),
    ):
        p = planets.get(key)
        if p and label not in nodes_line:
            nodes_line += (
                f"\n{label}: {p.get('sign_ru') or p.get('sign', '?')}, {p.get('house', '?')}-й дом"
            )

    return f"""Ты — опытный астролог, пишущий интерпретации натальной карты в стиле российского астрологического портала geocult.ru. Твоя задача — написать развёрнутое описание натальной карты на основе входных данных.
{gender_directive}
--- ВХОДНЫЕ ДАННЫЕ ---
Солнце: {sun_sign}
Луна: {moon_sign}
{asc_line}

Планеты:
{chr(10).join(planet_lines)}{nodes_line}

Основные аспекты:
{chr(10).join(aspect_lines) if aspect_lines else "— нет данных"}

--- ФОРМАТ ВЫВОДА (ВАЖНО) ---
Каждый раздел начинай с его названия, обёрнутого в **двойные звёздочки**, на отдельной строке, затем обычный текст полноценными абзацами. Парсер разбивает текст по `**Название**` — без звёздочек всё схлопнется в один блок. Кроме `**Заголовка**` никакого markdown: ни решёток (#), ни списков, ни звёздочек внутри текста. Используй РОВНО эти восемь заголовков и строго в этом порядке.

**Основа личности**
Опиши триаду Асцендент + Солнце + Луна. Асцендент — маска, стиль поведения, внешность. Солнце — ядро личности, воля, призвание, отец. Луна — эмоциональная природа, интуиция, мать, детство. По 1 абзацу на каждый элемент.

**Управитель гороскопа**
Определи планету-управитель Асцендента (Овен→Марс, Телец→Венера, Близнецы→Меркурий, Рак→Луна, Лев→Солнце, Дева→Меркурий, Весы→Венера, Скорпион→Плутон, Стрелец→Юпитер, Козерог→Сатурн, Водолей→Уран, Рыбы→Нептун). Опиши её положение в знаке и доме и что это значит для судьбы натива. 1 абзац.

**Личные планеты**
Меркурий (ум, общение), Венера (любовь, красота, деньги), Марс (действие, энергия). Для каждой — как качества проявляются через знак и в какой сфере жизни (дом) реализуется влияние. Образно, но кратко: 2–3 предложения на планету.

**Высшие планеты**
Юпитер (удача, расширение, статус) и Сатурн (ограничения, дисциплина, карьера) — влияние на карьеру и социальный статус. Уран, Нептун, Плутон — в контексте дома размещения. Кратко: 2–3 предложения на планету, один абзац на всё.

**Дома гороскопа**
Опиши занятые планетами дома. Названия: 1 «Точка Я», 2 «Точка возможностей», 3 «Точка коммуникации», 4 «Точка происхождения», 5 «Точка влечений», 6 «Точка силы», 7 «Точка Ты», 8 «Точка границ», 9 «Точка духа», 10 «Точка цели», 11 «Точка социальности», 12 «Точка одиночества». 2–3 предложения на ключевой дом с планетами, без воды.

**Лунные узлы**
Раху (Северный узел) — задача этой жизни, направление развития. Кету (Южный узел) — прошлый опыт, от чего уходить. В знаке и доме. 1 абзац. Если данных по узлам нет — одной фразой отметь, что узлы в этом разборе не рассчитаны, и переходи дальше.

**Аспекты планет**
Разбери 3–4 главных аспекта. Гармоничные (трин, секстиль) — таланты, лёгкий поток. Напряжённые (квадрат, оппозиция) — вызовы, уроки. Соединение — усиление планет. Конкретно, с примером жизненной ситуации. 1–2 абзаца.

**Заключительный синтез**
Главная тема судьбы, ключевые сильные стороны, основные вызовы. 3–4 практических совета. 1–2 абзаца.

--- СТИЛЬ ---
- Пиши по-русски, живым образным языком, чередуя конкретику и метафоры («актёры в театре жизни», «амплуа»). Авторитетно, но не пугающе.
- Называй человека «натив». Используй термины: куспид дома, управитель, поражённая планета, гармоничный аспект.
- Каждое предложение несёт факт об ЭТОМ нативе. Без абстрактных наполнителей ради объёма («просто баланс», «работа над собой»), без вступлений-подводок — сразу по сути.
- Объём — около 1200–1500 слов: каждый раздел плотный и по делу, без воды ради длины."""


async def generate_natal_reading(
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    planets: dict,
    aspects: list,
    api_key: str,
    gender: str | None = None,
) -> str:
    """
    Call Claude to generate a natal chart reading in Russian.
    Raises on API error — caller should catch and handle gracefully.

    ``gender`` ('male' / 'female' / None) anchors the grammatical forms in
    the generated text. Caller is responsible for storing the value next
    to the cached reading so future requests can detect a stale gender.
    """
    import anthropic

    from services.llm_pool import llm_semaphore

    prompt = _build_prompt(sun_sign, moon_sign, ascendant_sign, planets, aspects, gender)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    async with llm_semaphore:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=7000,
            messages=[{"role": "user", "content": prompt}],
        )

    text = first_text_block(message.content)
    log.info("llm_interpreter.done", chars=len(text))
    return text
