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

_NODE_KEYS = (
    "true_north_lunar_node",
    "mean_north_lunar_node",
    "true_south_lunar_node",
    "mean_south_lunar_node",
)


def _has_lunar_nodes(nodes: dict | None, planets: dict | None = None) -> bool:
    node_source = nodes if nodes else planets or {}
    return any(bool(node_source.get(key)) for key in _NODE_KEYS)


def _strip_lunar_nodes_block(text: str) -> str:
    lines = str(text or "").splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if stripped == "**Лунные узлы**":
            skipping = True
            continue
        if skipping and stripped.startswith("**") and stripped.endswith("**"):
            skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out).strip()


def _build_prompt(
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    planets: dict,
    aspects: list,
    gender: str | None = None,
    nodes: dict | None = None,
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

    # Узлы приходят отдельным каналом (chart_data["nodes"]), НЕ в planets — иначе
    # их посчитали бы планетой в стихиях/hero. Fallback на planets оставлен для
    # обратной совместимости со старыми кешами, где узлы могли лежать в planets.
    node_source = nodes if nodes else planets
    nodes_line = ""
    for key, label in (
        ("true_north_lunar_node", "Раху (Северный узел)"),
        ("mean_north_lunar_node", "Раху (Северный узел)"),
        ("true_south_lunar_node", "Кету (Южный узел)"),
        ("mean_south_lunar_node", "Кету (Южный узел)"),
    ):
        p = node_source.get(key)
        if p and label not in nodes_line:
            nodes_line += (
                f"\n{label}: {p.get('sign_ru') or p.get('sign', '?')}, {p.get('house', '?')}-й дом"
            )

    node_section = ""
    node_heading_count = "семь"
    node_heading_rule = "Используй РОВНО эти семь заголовков и строго в этом порядке."
    if nodes_line:
        node_heading_count = "восемь"
        node_heading_rule = "Используй РОВНО эти восемь заголовков и строго в этом порядке."
        nodes_directive = (
            "Раху (Северный узел) — задача этой жизни, направление развития. "
            "Кету (Южный узел) — прошлый опыт, от чего уходить. Положения узлов "
            "даны во входных данных выше («Раху …», «Кету …») — опиши их по знаку "
            "и дому конкретно, как вектор роста и точку опоры из прошлого. 1 абзац. "
            "Это платный отчёт: НЕ пиши, что узлы «не рассчитаны» — данные есть."
        )
        node_section = (
            "\n**Лунные узлы**\n"
            f"{nodes_directive}\n"
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
Каждый раздел начинай с его названия, обёрнутого в **двойные звёздочки**, на отдельной строке, затем обычный текст полноценными абзацами. Парсер разбивает текст по `**Название**` — без звёздочек всё схлопнется в один блок. Кроме `**Заголовка**` никакого markdown: ни решёток (#), ни списков, ни звёздочек внутри текста. {node_heading_rule}

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
{node_section}

**Аспекты планет**
Разбери 3–4 главных аспекта. Гармоничные (трин, секстиль) — таланты, лёгкий поток. Напряжённые (квадрат, оппозиция) — вызовы, уроки. Соединение — усиление планет. Конкретно, с примером жизненной ситуации. 1–2 абзаца.

**Заключительный синтез**
Главная тема судьбы, ключевые сильные стороны, основные вызовы. 3–4 практических совета. 1–2 абзаца.

--- СТИЛЬ ---
- Пиши по-русски, живым образным языком, чередуя конкретику и метафоры («актёры в театре жизни», «амплуа»). Авторитетно, но не пугающе.
- Называй человека «натив». Используй термины: куспид дома, управитель, поражённая планета, гармоничный аспект.
- Каждое предложение несёт факт об ЭТОМ нативе. Без абстрактных наполнителей ради объёма («просто баланс», «работа над собой»), без вступлений-подводок — сразу по сути.
- Объём — около {"1200–1500" if nodes_line else "1050–1350"} слов: каждый из {node_heading_count} разделов плотный и по делу, без воды ради длины."""


async def generate_natal_reading(
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    planets: dict,
    aspects: list,
    api_key: str,
    gender: str | None = None,
    nodes: dict | None = None,
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
    from services.quality_validator import Severity, TextValidator, ValidationContext
    from services.rate_limiter import AnthropicLimiter

    prompt = _build_prompt(
        sun_sign, moon_sign, ascendant_sign, planets, aspects, gender, nodes=nodes
    )

    client = anthropic.AsyncAnthropic(api_key=api_key)
    validator = TextValidator(use_spellchecker=False)
    ctx = ValidationContext(section_kind="synthesis", subject="Натальный разбор")

    async def _call(max_tokens: int) -> tuple[str, str | None]:
        # 9000 (было 7000): на 8-разделочном ~1200-1500-словном тексте 7k токенов
        # упирались в потолок и обрывали последнюю секцию на полуслове («…строите карь»).
        async with llm_semaphore, AnthropicLimiter(max_tokens):
            message = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        return first_text_block(message.content), getattr(message, "stop_reason", None)

    text, stop_reason = await _call(9000)

    # Финальный разбор обрезанным/коротким уходить не должен (Layer 3). Если
    # модель упёрлась в лимит или валидатор увидел обрыв/критическую короткость —
    # один повтор с увеличенным лимитом. Чаще всего хватает: обрыв был из-за
    # max_tokens, а не из-за контента.
    issues = validator.validate(text, ctx)
    truncated = any(i.code == "TRUNCATED" for i in issues)
    too_short = any(
        i.code == "TOO_SHORT_CRITICAL" and i.severity == Severity.CRITICAL for i in issues
    )
    if stop_reason == "max_tokens" or truncated or too_short:
        log.warning(
            "llm_interpreter.synthesis_defect_retry",
            chars=len(text),
            stop_reason=stop_reason,
            truncated=truncated,
            too_short=too_short,
        )
        retry_text, retry_stop = await _call(12000)
        retry_issues = validator.validate(retry_text, ctx)
        retry_bad = any(i.code in ("TRUNCATED", "TOO_SHORT_CRITICAL") for i in retry_issues)
        # Берём повтор, если он не хуже исходного (иначе оставляем что было).
        if not retry_bad or retry_stop != "max_tokens":
            text, stop_reason = retry_text, retry_stop

    if not _has_lunar_nodes(nodes, planets):
        text = _strip_lunar_nodes_block(text)

    from services.astro.text_polish import polish_natal_text
    text, typo_fixes = polish_natal_text(text)
    log.info(
        "llm_interpreter.done",
        chars=len(text), stop_reason=stop_reason, typo_fixes=typo_fixes,
    )
    return text


def _build_mini_prompt(
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    gender: str | None = None,
) -> str:
    asc_line = f"Восходящий знак (Асцендент): {ascendant_sign}" if ascendant_sign else ""
    gender_directive = ""
    if gender in ("male", "female"):
        ru = "мужчина" if gender == "male" else "женщина"
        forms = (
            "все формы глаголов прошедшего времени, прилагательных и причастий — в мужском роде"
            if gender == "male"
            else "все формы глаголов прошедшего времени, прилагательных и причастий — в женском роде"
        )
        gender_directive = f"\nПол читателя: {ru.upper()}. {forms.upper()}.\n"

    return f"""Ты — опытный астролог, пишущий в стиле российского портала geocult.ru. Напиши КОРОТКОЕ ознакомительное описание натальной карты по триаде Солнце / Луна / Асцендент.
{gender_directive}
--- ВХОДНЫЕ ДАННЫЕ ---
Солнце: {sun_sign}
Луна: {moon_sign}
{asc_line}

--- ФОРМАТ ВЫВОДА (ВАЖНО) ---
Ровно три раздела, каждый начинается с названия в **двойных звёздочках** на отдельной строке, затем один абзац обычного текста. Никакого другого markdown: ни решёток, ни списков, ни звёздочек внутри текста. Используй РОВНО эти три заголовка в этом порядке:

**Солнце**
Ядро личности, воля, призвание — через знак Солнца. 2–3 предложения.

**Луна**
Эмоциональная природа, интуиция, внутренние потребности — через знак Луны. 2–3 предложения.

**Восходящий**
{"Маска, стиль поведения, первое впечатление — через знак Асцендента. 2–3 предложения." if ascendant_sign else "Асцендент в этом разборе не рассчитан (нет точного времени рождения) — одной фразой отметь это и кратко опиши общий вектор личности по Солнцу и Луне."}

--- СТИЛЬ ---
- Пиши по-русски, живым образным языком. Называй человека «натив».
- Каждое предложение несёт факт об ЭТОМ нативе, без абстрактных наполнителей и вступлений.
- Это ТИЗЕР: всего ~150–220 слов на все три раздела. Заверши лёгким намёком, что полный разбор раскрывает планеты, дома и аспекты подробнее."""


async def generate_natal_mini_reading(
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    api_key: str,
    gender: str | None = None,
) -> str:
    """
    Cheap teaser reading (Sun/Moon/Ascendant triad only, ~700 max_tokens).
    Shown on the natal screen before the user requests the full PDF reading.
    Raises on API error — caller should catch and handle gracefully.
    """
    import anthropic

    from services.llm_pool import llm_semaphore
    from services.rate_limiter import AnthropicLimiter

    prompt = _build_mini_prompt(sun_sign, moon_sign, ascendant_sign, gender)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    async with llm_semaphore, AnthropicLimiter(700):
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )

    text = first_text_block(message.content)
    from services.astro.text_polish import polish_natal_text
    text, typo_fixes = polish_natal_text(text)
    log.info(
        "llm_interpreter.mini_done", chars=len(text), typo_fixes=typo_fixes,
    )
    return text
