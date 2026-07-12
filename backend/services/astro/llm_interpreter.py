"""
Provider-neutral LLM-based natal chart interpretation.

Generates a holistic, personal reading in Russian from raw chart data.
Result is cached by the caller — this function always calls the API.
"""

from __future__ import annotations

from core.logging import get_logger
from core.settings import settings
from services.llm_client import create_llm_client
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
    birth_time_known = ascendant_sign is not None
    planet_lines: list[str] = []
    for key, ru_name in _PLANET_RU.items():
        if key in planets:
            p = planets[key]
            retro = " (ретроградный)" if p.get("retrograde") else ""
            house = p.get("house")
            house_suffix = f", {house}-й дом" if house is not None else ""
            planet_lines.append(
                f"- {ru_name}: {p.get('sign_ru') or p.get('sign', '?')} "
                f"{p.get('sign_degree', 0):.0f}°{house_suffix}{retro}"
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
            house = p.get("house")
            house_suffix = f", {house}-й дом" if house is not None else ""
            nodes_line += (
                f"\n{label}: {p.get('sign_ru') or p.get('sign', '?')}{house_suffix}"
            )

    node_section = ""
    if nodes_line:
        nodes_directive = (
            "Раху (Северный узел) — задача этой жизни, направление развития. "
            "Кету (Южный узел) — прошлый опыт, от чего уходить. Положения узлов "
            "даны во входных данных выше («Раху …», «Кету …») — опиши их по знаку "
            f"{'и дому ' if birth_time_known else ''}конкретно, как символический "
            "вектор роста и точку опоры. 1 абзац. "
            "Это платный отчёт: НЕ пиши, что узлы «не рассчитаны» — данные есть."
        )
        node_section = (
            "\n**Лунные узлы**\n"
            f"{nodes_directive}\n"
        )

    foundation = (
        "Опиши триаду Асцендент + Солнце + Луна. Асцендент — маска и стиль "
        "поведения. Солнце — ядро личности, Луна — эмоциональная природа."
        if birth_time_known
        else "Опиши только Солнце и Луну. Время рождения неизвестно: не упоминай "
        "Асцендент, MC, дома, куспиды, внешность или управителя карты. Луна "
        "рассчитана приблизительно на 12:00."
    )
    ruler_section = "" if not birth_time_known else """
**Управитель гороскопа**
Определи управителя Асцендента и опиши только по указанным знаку и дому. 1 абзац.
"""
    houses_section = "" if not birth_time_known else """
**Дома гороскопа**
Опиши только занятые планетами дома из входных данных. 2–3 предложения на ключевой дом.
"""
    section_count = 7 if birth_time_known else 5
    if nodes_line:
        section_count += 1
    node_heading_rule = (
        f"Используй РОВНО {section_count} разделов и только указанные ниже заголовки."
    )

    return f"""Ты — опытный астролог. Напиши развёрнутое описание натальной карты только на основе входных данных, используя понятную структуру разделов в духе geocult, но без копирования текста.
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
{foundation}
{ruler_section}

**Личные планеты**
Меркурий, Венера и Марс: интерпретируй указанные знаки{', затем указанные дома' if birth_time_known else ''}. 2–3 предложения на планету.

**Высшие планеты**
Юпитер, Сатурн, Уран, Нептун и Плутон: интерпретируй только указанные положения. Кратко, один абзац.
{houses_section}
{node_section}

**Аспекты планет**
Разбери 3–4 главных аспекта. Гармоничные (трин, секстиль) — таланты, лёгкий поток. Напряжённые (квадрат, оппозиция) — вызовы, уроки. Соединение — усиление планет. Конкретно, с примером жизненной ситуации. 1–2 абзаца.

**Заключительный синтез**
Главная тема судьбы, ключевые сильные стороны, основные вызовы. 3–4 практических совета. 1–2 абзаца.

--- СТИЛЬ ---
- Пиши по-русски, живым образным языком, чередуя конкретику и метафоры («актёры в театре жизни», «амплуа»). Авторитетно, но не пугающе.
- Человека можно нейтрально называть «натив», не приписывая ему факты биографии.
- Формулируй трактовки как возможности и вопросы для самонаблюдения, не как доказанные факты биографии.
- Не выдумывай события детства, семью, зависимости, диагнозы и прошлые жизни. Не гарантируй будущие события.
- Упоминай только аспекты из входного списка. {"Упоминай только явно указанные дома." if birth_time_known else "Запрещены любые упоминания ASC, MC, домов и куспидов."}
- Объём — около {"1050–1350" if birth_time_known else "750–1000"} слов."""


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
    Call the configured LLM to generate a natal chart reading in Russian.
    Raises on API error — caller should catch and handle gracefully.

    ``gender`` ('male' / 'female' / None) anchors the grammatical forms in
    the generated text. Caller is responsible for storing the value next
    to the cached reading so future requests can detect a stale gender.
    """
    from services.astro.fact_context import (
        FactContext,
        safe_natal_fallback,
        validate_generated_text,
    )
    from services.llm_pool import llm_semaphore
    from services.quality_validator import Severity, TextValidator, ValidationContext
    from services.rate_limiter import LLMLimiter

    prompt = _build_prompt(
        sun_sign, moon_sign, ascendant_sign, planets, aspects, gender, nodes=nodes
    )

    client = create_llm_client(api_key)
    validator = TextValidator(use_spellchecker=False)
    ctx = ValidationContext(section_kind="synthesis", subject="Натальный разбор")

    async def _call(
        max_tokens: int, request_prompt: str = prompt
    ) -> tuple[str, str | None]:
        # 9000 (было 7000): на 8-разделочном ~1200-1500-словном тексте 7k токенов
        # упирались в потолок и обрывали последнюю секцию на полуслове («…строите карь»).
        async with llm_semaphore, LLMLimiter(max_tokens):
            message = await client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": request_prompt}],
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

    fact_context = FactContext.from_chart(
        planets=planets,
        aspects=aspects,
        birth_time_known=ascendant_sign is not None,
    )
    fact_errors = validate_generated_text(text, fact_context)
    if fact_errors:
        correction = (
            prompt
            + "\n\nПРЕДЫДУЩИЙ ОТВЕТ ОТКЛОНЁН. Исправь все ошибки и верни весь текст заново:\n- "
            + "\n- ".join(fact_errors)
        )
        log.warning("llm_interpreter.fact_retry", errors=fact_errors)
        retry_text, retry_stop = await _call(9000, correction)
        retry_errors = validate_generated_text(retry_text, fact_context)
        if retry_errors:
            log.error("llm_interpreter.fact_fallback", errors=retry_errors)
            text = safe_natal_fallback(sun_sign, moon_sign)
            stop_reason = "fact_validation_fallback"
        else:
            text, stop_reason = retry_text, retry_stop

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

    format_sections = """
**Солнце**
Ядро личности, воля, призвание — через знак Солнца. 2–3 предложения.

**Луна**
Эмоциональная природа, интуиция, внутренние потребности — через знак Луны. 2–3 предложения.
"""
    if ascendant_sign:
        format_sections += """
**Восходящий**
Маска, стиль поведения, первое впечатление — через знак Асцендента. 2–3 предложения.
"""
    section_count = 3 if ascendant_sign else 2

    return f"""Ты — опытный астролог. Напиши КОРОТКОЕ ознакомительное описание натальной карты по доступным данным.
{gender_directive}
--- ВХОДНЫЕ ДАННЫЕ ---
Солнце: {sun_sign}
Луна: {moon_sign}
{asc_line}

--- ФОРМАТ ВЫВОДА (ВАЖНО) ---
Ровно {section_count} раздела, каждый начинается с названия в **двойных звёздочках**. Никакого другого markdown. Используй только эти заголовки:
{format_sections}

--- СТИЛЬ ---
- Пиши по-русски, живым образным языком. Называй человека «натив».
- Это символические возможности для самонаблюдения, не факты биографии и не гарантии.
- Не выдумывай семью, детство, диагнозы или события будущего.
- {"Используй Асцендент только из входных данных." if ascendant_sign else "Не упоминай ASC, MC, дома, куспиды и время рождения."}
- Это ТИЗЕР: всего ~120–220 слов."""


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
    from services.astro.fact_context import (
        FactContext,
        safe_natal_fallback,
        validate_generated_text,
    )
    from services.llm_pool import llm_semaphore
    from services.rate_limiter import LLMLimiter

    prompt = _build_mini_prompt(sun_sign, moon_sign, ascendant_sign, gender)

    client = create_llm_client(api_key)

    async def _call(request_prompt: str) -> str:
        async with llm_semaphore, LLMLimiter(700):
            message = await client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=700,
                messages=[{"role": "user", "content": request_prompt}],
            )
        return first_text_block(message.content)

    text = await _call(prompt)
    context = FactContext(birth_time_known=ascendant_sign is not None)
    errors = validate_generated_text(text, context)
    if errors:
        text = await _call(
            prompt + "\n\nИсправь отклонённый ответ:\n- " + "\n- ".join(errors)
        )
        if validate_generated_text(text, context):
            text = safe_natal_fallback(sun_sign, moon_sign)
    from services.astro.text_polish import polish_natal_text
    text, typo_fixes = polish_natal_text(text)
    log.info(
        "llm_interpreter.mini_done", chars=len(text), typo_fixes=typo_fixes,
    )
    return text
