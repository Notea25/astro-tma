"""Tests for natal PDF generation and temporary download links."""

import sys
from types import SimpleNamespace

import pytest

from services import natal_pdf, natal_pdf_html
from services.astro import llm_interpreter, natal_descriptions
from services.astro.sign_cases import sign_ru
from services.natal_pdf import generate_natal_pdf


def _sample_chart():
    planets = {
        "sun": {
            "sign": "Scorpio",
            "sign_ru": "Скорпион",
            "degree": 224.1,
            "sign_degree": 14.1,
            "house": 9,
            "retrograde": False,
        },
        "moon": {
            "sign": "Aquarius",
            "sign_ru": "Водолей",
            "degree": 309.2,
            "sign_degree": 9.2,
            "house": 1,
            "retrograde": False,
        },
        "mercury": {
            "sign": "Sagittarius",
            "sign_ru": "Стрелец",
            "degree": 241.0,
            "sign_degree": 1.0,
            "house": 10,
            "retrograde": False,
        },
    }
    houses = [
        {"number": number, "sign": "Aries", "sign_ru": "Овен", "degree": number * 30.0}
        for number in range(1, 13)
    ]
    aspects = [{"p1": "Sun", "p2": "Moon", "aspect": "square", "orb": 1.2}]
    return planets, houses, aspects


def test_generate_natal_pdf_returns_pdf_with_incomplete_descriptions():
    planets, houses, aspects = _sample_chart()

    pdf = generate_natal_pdf(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        descriptions={
            "planets": {"sun": {"full": "Полное описание Солнца. " * 20}},
            "houses": {},
            "aspects": [],
        },
    )

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 10_000


def test_generate_natal_pdf_does_not_require_dejavu_bold(monkeypatch):
    planets, houses, aspects = _sample_chart()
    monkeypatch.setattr(natal_pdf.os.path, "exists", lambda _path: False)
    monkeypatch.setattr(natal_pdf, "_FONT_REGISTERED", False)
    monkeypatch.setattr(natal_pdf, "FONT", "Helvetica")
    monkeypatch.setattr(natal_pdf, "FONT_BOLD", "Helvetica-Bold")

    pdf = generate_natal_pdf(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
    )

    assert pdf.startswith(b"%PDF-")


def test_generate_natal_pdf_handles_long_reading_and_many_aspects():
    planets, houses, _aspects = _sample_chart()
    planets.update(
        {
            "venus": {"sign": "Cancer", "sign_ru": "Рак", "degree": 91.0, "house": 8},
            "mars": {"sign": "Libra", "sign_ru": "Весы", "degree": 183.0, "house": 11},
            "jupiter": {
                "sign": "Gemini",
                "sign_ru": "Близнецы",
                "degree": 73.0,
                "house": 7,
                "retrograde": True,
            },
            "saturn": {"sign": "Gemini", "sign_ru": "Близнецы", "degree": 77.0, "house": 7},
            "uranus": {"sign": "Aquarius", "sign_ru": "Водолей", "degree": 318.0, "house": 5},
            "neptune": {"sign": "Aquarius", "sign_ru": "Водолей", "degree": 309.0, "house": 5},
            "pluto": {"sign": "Sagittarius", "sign_ru": "Стрелец", "degree": 252.0, "house": 2},
        }
    )
    aspects = [
        {"p1": "Sun", "p2": "Venus", "aspect": "conjunction", "orb": 6.9},
        {"p1": "Sun", "p2": "Jupiter", "aspect": "trine", "orb": 6.3},
        {"p1": "Sun", "p2": "Uranus", "aspect": "trine", "orb": 0.3},
        {"p1": "Moon", "p2": "Mercury", "aspect": "trine", "orb": 1.2},
        {"p1": "Jupiter", "p2": "Uranus", "aspect": "trine", "orb": 6.0},
        {"p1": "Jupiter", "p2": "Neptune", "aspect": "trine", "orb": 7.2},
        {"p1": "Saturn", "p2": "Neptune", "aspect": "trine", "orb": 3.5},
        {"p1": "Sun", "p2": "Pluto", "aspect": "sextile", "orb": 6.5},
        {"p1": "Mercury", "p2": "Mars", "aspect": "sextile", "orb": 2.4},
        {"p1": "Venus", "p2": "Mars", "aspect": "sextile", "orb": 4.5},
        {"p1": "Uranus", "p2": "Pluto", "aspect": "sextile", "orb": 6.2},
        {"p1": "Moon", "p2": "Jupiter", "aspect": "square", "orb": 6.0},
        {"p1": "Moon", "p2": "Pluto", "aspect": "square", "orb": 0.2},
        {"p1": "Mercury", "p2": "Uranus", "aspect": "square", "orb": 4.8},
        {"p1": "Venus", "p2": "Uranus", "aspect": "square", "orb": 2.1},
        {"p1": "Mars", "p2": "Jupiter", "aspect": "square", "orb": 3.6},
        {"p1": "Mars", "p2": "Pluto", "aspect": "square", "orb": 3.8},
        {"p1": "Moon", "p2": "Mars", "aspect": "opposition", "orb": 3.6},
        {"p1": "Jupiter", "p2": "Pluto", "aspect": "opposition", "orb": 0.2},
    ]
    reading = "\n".join(
        [
            "**Ядро личности**",
            "Вы человек противоречивый, и это ваша изюминка. " * 18,
            "**Ум и общение**",
            "Меркурий показывает точность речи, наблюдательность и умение держать фокус. " * 16,
            "**Любовь и ценности**",
            "Венера описывает глубину привязанностей, осторожность и сильные чувства. " * 16,
            "**Удача и вызовы**",
            "Юпитер и Сатурн требуют дисциплины, повторного изучения и взрослой настройки. " * 18,
        ]
    )

    pdf = generate_natal_pdf(
        user_name="Andrey",
        birth_date="2000-10-10 12:00:00",
        birth_time=None,
        birth_city="Санкт-Петербург, Россия",
        sun_sign="Libra",
        moon_sign="Pisces",
        asc_sign="Scorpio",
        planets=planets,
        houses=houses,
        aspects=aspects,
        reading=reading,
    )

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 10_000


def test_build_natal_pdf_html_contains_reference_layout_sections():
    planets, houses, aspects = _sample_chart()

    document = natal_pdf_html.build_natal_pdf_html(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
    )

    assert "Натальная карта" in document
    assert "Содержание" in document
    assert "Натальное колесо" in document
    assert "Баланс стихий" in document
    assert "Планеты в знаках" in document
    assert "Дома гороскопа" in document
    assert "Персональная интерпретация" in document
    assert "wheel-svg" in document
    assert 'r="36"' not in document
    assert "@page" in document


def test_build_natal_pdf_html_keeps_full_reading_text_without_empty_page():
    planets, houses, aspects = _sample_chart()
    long_paragraph = " ".join(f"слово{i}" for i in range(120)) + " ФИНАЛЬНЫЙ_МАРКЕР"
    reading = f"**Ядро личности**\n{long_paragraph}"

    document = natal_pdf_html.build_natal_pdf_html(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        reading=reading,
    )

    assert "ФИНАЛЬНЫЙ_МАРКЕР" in document
    assert '<div class="reading"></div>' not in document


def test_build_natal_pdf_html_adds_continuation_pages_for_long_reading():
    planets, houses, aspects = _sample_chart()
    paragraph = " ".join(f"текст{i}" for i in range(240))
    reading = "\n".join(
        [
            "**Ядро личности**",
            paragraph,
            "**Ум и общение**",
            paragraph,
            "**Любовь и ценности**",
            paragraph,
            "**Энергия и воля**",
            paragraph,
            "**Удача и вызовы**",
            paragraph,
            "**Ключевые аспекты**",
            paragraph,
            "**Совет и путь**",
            paragraph,
        ]
    )

    document = natal_pdf_html.build_natal_pdf_html(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        reading=reading,
    )

    total_pages = document.count('<section class="page')
    assert total_pages > 13
    assert f"{total_pages} / {total_pages}" in document


def test_build_natal_pdf_html_packs_multiple_aspects_per_page():
    planets, houses, _aspects = _sample_chart()
    aspects = [
        {"p1": "Sun", "p2": "Moon", "aspect": "square", "orb": 1.2},
        {"p1": "Sun", "p2": "Mercury", "aspect": "conjunction", "orb": 2.0},
        {"p1": "Moon", "p2": "Mercury", "aspect": "trine", "orb": 3.1},
        {"p1": "Mercury", "p2": "Sun", "aspect": "sextile", "orb": 4.0},
    ]
    descriptions = {
        "aspects": [
            {
                "p1": a["p1"].lower(),
                "p2": a["p2"].lower(),
                "type": a["aspect"],
                "full": " ".join(f"аспект{i}" for i in range(45)),
            }
            for a in aspects
        ]
    }

    document = natal_pdf_html.build_natal_pdf_html(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        descriptions=descriptions,
    )

    aspect_page_count = document.count("<h2>Аспекты</h2>")
    assert aspect_page_count < len(aspects)


def test_natal_reading_prompt_requests_expanded_interpretation():
    planets, _houses, aspects = _sample_chart()

    prompt = llm_interpreter._build_prompt("Scorpio", "Aquarius", "Aries", planets, aspects)

    assert "geocult" in prompt
    assert "полноценными абзацами" in prompt
    assert "**Основа личности**" in prompt
    assert "**Управитель гороскопа**" in prompt
    assert "**Заключительный синтез**" in prompt
    assert "**Лунные узлы**" not in prompt
    assert "не рассчитаны" not in prompt
    assert "натив" in prompt


def test_natal_reading_prompt_includes_nodes_only_when_positions_exist():
    planets, _houses, aspects = _sample_chart()
    prompt = llm_interpreter._build_prompt(
        "Scorpio",
        "Aquarius",
        "Aries",
        planets,
        aspects,
        nodes={
            "true_north_lunar_node": {"sign_ru": "Дева", "house": 2},
            "true_south_lunar_node": {"sign_ru": "Рыбы", "house": 8},
        },
    )

    assert "**Лунные узлы**" in prompt
    assert "Раху (Северный узел): Дева, 2-й дом" in prompt
    assert "Кету (Южный узел): Рыбы, 8-й дом" in prompt
    assert "НЕ пиши, что узлы" in prompt


def test_natal_reading_strips_lunar_nodes_fallback_block_without_positions():
    reading = "\n".join(
        [
            "**Основа личности**",
            "Текст основы.",
            "**Лунные узлы**",
            "Расчёт лунных узлов в предоставленных данных отсутствует.",
            "**Аспекты планет**",
            "Текст аспектов.",
        ]
    )

    cleaned = llm_interpreter._strip_lunar_nodes_block(reading)

    assert "**Лунные узлы**" not in cleaned
    assert "отсутствует" not in cleaned
    assert "**Основа личности**" in cleaned
    assert "**Аспекты планет**" in cleaned


def test_cached_pdf_reading_requires_current_version_and_expanded_text():
    from api.routes import natal

    old_cached = {
        "reading": "\n".join(
            [
                "**Основа личности**",
                "слово " * 200,
                "**Лунные узлы**",
                "Расчёт лунных узлов в предоставленных данных отсутствует.",
                "**Аспекты планет**",
                "слово " * 200,
            ]
        ),
        "reading_gender": None,
    }
    fresh_cached = {
        "reading": "\n".join(
            [
                "**Основа личности**",
                "слово " * 160,
                "**Управитель гороскопа**",
                "слово " * 160,
                "**Личные планеты**",
                "слово " * 160,
                "**Высшие планеты**",
                "слово " * 160,
                "**Дома гороскопа**",
                "слово " * 160,
                "**Аспекты планет**",
                "слово " * 160,
                "**Заключительный синтез**",
                "слово " * 160,
            ]
        ),
        "reading_gender": None,
        "reading_version": natal.NATAL_READING_VERSION,
    }

    assert natal._reading_is_fresh(old_cached, None) is None
    assert natal._reading_is_fresh(fresh_cached, None) == fresh_cached["reading"]


@pytest.mark.asyncio
async def test_generate_natal_reading_uses_expanded_token_budget(monkeypatch):
    planets, _houses, aspects = _sample_chart()
    calls = {}

    class FakeMessages:
        async def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text="Развёрнутое чтение.")])

    class FakeAnthropic:
        def __init__(self, api_key):
            calls["api_key"] = api_key
            self.messages = FakeMessages()

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(AsyncAnthropic=FakeAnthropic))

    reading = await llm_interpreter.generate_natal_reading(
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        ascendant_sign="Aries",
        planets=planets,
        aspects=aspects,
        api_key="test-key",
    )

    assert reading == "Развёрнутое чтение."
    assert calls["api_key"] == "test-key"
    assert calls["max_tokens"] >= 6000


def test_planet_description_prompt_prioritises_sign_over_house():
    prompt = natal_descriptions._planet_one_prompt(
        "sun",
        {"sign": "Capricorn", "sign_ru": "Козерог", "house": 10, "retrograde": False},
    )

    assert "Планеты в знаках" in prompt
    assert "центр разбора — связка планета + знак" in prompt
    assert "Солнце в Козероге" in prompt
    assert "в знаке Козерога" in prompt
    assert "80-100 слов" in prompt
    assert "роль планеты как архетип" in prompt
    assert "проявления в отношениях и работе/делах" in prompt
    assert "без воды" in prompt
    assert "Подробнее" in prompt
    assert "уникальное первое и последнее предложение" in prompt
    assert "full" in prompt
    assert "6-9 предложений" not in prompt


def test_sign_declensions_for_common_pdf_phrases():
    assert f"Солнце в {sign_ru('scorpio', 'prep')}" == "Солнце в Скорпионе"
    assert f"Луна в {sign_ru('aquarius', 'prep')}" == "Луна в Водолее"
    assert f"Меркурий в {sign_ru('sagittarius', 'prep')}" == "Меркурий в Стрельце"
    assert f"в знаке {sign_ru('scorpio', 'gen')}" == "в знаке Скорпиона"
    assert f"в знаке {sign_ru('aries', 'gen')}" == "в знаке Овна"
    assert f"дом в {sign_ru('libra', 'prep')}" == "дом в Весах"


def test_house_description_prompt_requests_scenarios_and_declension():
    prompt = natal_descriptions._house_one_prompt(7, "Весы")

    assert "знак на куспиде — Весы" in prompt
    assert "дом в Весах" in prompt
    assert "110-150 слов" in prompt
    assert "типичные жизненные сценарии" in prompt
    assert "сильная сторона" in prompt
    assert "без воды" in prompt
    assert "уникальное первое и последнее предложение" in prompt


def test_aspect_description_prompt_requests_full_interaction():
    prompt = natal_descriptions._aspect_one_prompt("sun", "moon", "square")

    assert "Солнце — квадрат — Луна" in prompt
    assert "130-170 слов" in prompt
    assert "взаимодействуют" in prompt
    assert "сочетаются эти две темы" in prompt
    assert "отношениях и делах" in prompt
    assert "зона роста" in prompt
    assert "уникальное первое и последнее предложение" in prompt


def test_description_batch_prompts_include_full_chart_context():
    planets, houses, aspects = _sample_chart()
    context = natal_descriptions._chart_context(planets, houses, aspects)

    prompt = natal_descriptions._build_planets_prompt(
        {"sun": planets["sun"]},
        chart_context=context,
    )

    assert "Контекст всей натальной карты" in prompt
    assert "Луна:" in prompt
    assert "Все дома:" in prompt
    assert "Планеты в домах:" in prompt
    assert "Связанные аспекты по планетам:" in prompt
    assert "sun_moon_square" in prompt
    assert "ВЕРХНИЙ ориентир" in prompt
    assert "КОНКРЕТНО, БЕЗ ВОДЫ" in prompt
    assert "Запрещены абстрактные наполнители" in prompt
    assert "Читать далее" in prompt


def test_html_pdf_uses_full_description_before_short():
    planets, houses, aspects = _sample_chart()
    document = natal_pdf_html.build_natal_pdf_html(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        descriptions={
            "planets": {
                "sun": {
                    "short": "КОРОТКИЙ_ТЕКСТ",
                    "full": "ПОЛНЫЙ_ТЕКСТ для проверки приоритета.",
                }
            },
            "houses": {},
            "aspects": [],
        },
    )

    assert "ПОЛНЫЙ_ТЕКСТ" in document
    assert "КОРОТКИЙ_ТЕКСТ" not in document


def test_key_point_blurbs_do_not_end_with_dangling_preposition():
    text = (
        "Вы умеете заранее рассчитать ходы, взвесить за и против, заметить скрытый "
        "мотив собеседника, удержать паузу, остановиться в нужный момент и не "
        "поддаться чужому давлению. Второе предложение."
    )

    html_blurb = natal_pdf_html._first_sentences(text, max_chars=82)
    reportlab_blurb = natal_pdf._compact_description({"full": text}, "", words=16)

    assert html_blurb.endswith("…")
    assert reportlab_blurb.endswith("…")
    assert not html_blurb.endswith((" в…", " в."))
    assert not reportlab_blurb.endswith((" в…", " в."))


def test_key_point_blurbs_do_not_end_with_dangling_negation():
    text = (
        "Солнце в Тельце в 10-м доме делает карьеру вашей основной жизненной "
        "задачей — не потому, что вы честолюбивы, а потому что вам важно видеть "
        "плотный результат своих усилий. Второе предложение."
    )

    html_blurb = natal_pdf_html._first_sentences(text, max_chars=70)
    reportlab_blurb = natal_pdf._first_sentences(text, max_chars=70)

    assert html_blurb.endswith("…")
    assert reportlab_blurb.endswith("…")
    assert "— не" not in html_blurb
    assert "— не" not in reportlab_blurb


def test_aspect_fallback_not_verbatim_dup_for_same_type():
    """P1-3: два разных квадрата без записи в PAIR_TEXTS не должны давать
    байт-в-байт одинаковый текст (Юпитер□Нептун vs Сатурн□Уран в карте Andrey)."""
    a1 = {"p1": "jupiter", "p2": "neptune", "aspect": "square", "orb": 7.3}
    a2 = {"p1": "saturn", "p2": "uranus", "aspect": "square", "orb": 5.5}
    t1 = natal_pdf._aspect_fallback(a1)
    t2 = natal_pdf._aspect_fallback(a2)
    assert t1 != t2
    # Обе планеты названы в своём тексте — fallback персонализирован по паре.
    assert "Юпитер" in t1 and "Нептун" in t1
    assert "Сатурн" in t2 and "Уран" in t2


def test_aspect_fallback_avoids_repeated_orb_frame():
    text = natal_pdf._aspect_fallback(
        {"p1": "jupiter", "p2": "neptune", "aspect": "square", "orb": 7.3}
    )

    assert "Орб широкий" not in text
    assert "орбе 7.3°" in text


def test_aspect_fallback_orb_tail_not_identical_across_aspects():
    """P1-3: «включается волнами» не должно повторяться дословно во многих
    аспектах — хвост про орб варьируется по типу аспекта (карта Andrey 2002:
    4 широких аспекта с персональной планетой давали идентичный хвост)."""
    aspects = [
        {"p1": "venus", "p2": "neptune", "aspect": "conjunction", "orb": 3.6},
        {"p1": "mercury", "p2": "pluto", "aspect": "sextile", "orb": 3.8},
        {"p1": "mars", "p2": "saturn", "aspect": "sextile", "orb": 5.4},
        {"p1": "mars", "p2": "neptune", "aspect": "square", "orb": 5.4},
    ]
    tails = [natal_pdf._aspect_fallback(a).split(". ")[-1] for a in aspects]
    # Ни одна универсальная фраза-штамп не повторяется во всех четырёх.
    assert "включается волнами" not in " ".join(tails) or len({t for t in tails}) == len(tails)
    # Полные тексты уникальны (дословных дублей нет).
    full = [natal_pdf._aspect_fallback(a) for a in aspects]
    assert len(set(full)) == len(full)


def test_planet_fallback_avoids_case_error_after_na():
    venus = natal_pdf._planet_fallback("venus", {"sign_ru": "Рак", "house": 10})
    uranus = natal_pdf._planet_fallback("uranus", {"sign_ru": "Водолей", "house": 6})

    joined = f"{venus} {uranus}"

    assert "направлено на карьера" not in joined
    assert "направлено на режим" not in joined
    assert "работает в сфере: карьера, статус" in joined
    assert "работает в сфере: режим, здоровье" in joined


def test_reportlab_aspect_colors_match_html_semantics():
    assert natal_pdf._aspect_color("square") != natal_pdf._aspect_color("opposition")
    assert natal_pdf._aspect_dash("square") == ()
    assert natal_pdf._aspect_dash("opposition") == (2, 3)


def test_element_symbols_match_between_renderers():
    expected = {
        "fire": "△",
        "earth": "▽",
        "air": "▵",
        "water": "▿",
    }

    assert natal_pdf.ELEMENT_SYMBOLS == expected
    assert natal_pdf_html.ELEMENT_SYMBOLS == expected


def test_reportlab_retro_badge_draws_pill():
    class FakeCanvas:
        def __init__(self):
            self.calls = []

        def __getattr__(self, name):
            if name not in {
                "setStrokeColor",
                "setFillColor",
                "roundRect",
                "setFont",
                "drawCentredString",
            }:
                raise AttributeError(name)

            def record(*args, **kwargs):
                self.calls.append((name, args, kwargs))

            return record

    fake = FakeCanvas()

    natal_pdf._draw_retro_badge(fake, 58, 120)

    assert any(call[0] == "roundRect" for call in fake.calls)
    assert any(call[0] == "drawCentredString" and "℞ РЕТРО" in call[1] for call in fake.calls)


def test_reportlab_footer_does_not_print_estimated_total(monkeypatch):
    planets, houses, aspects = _sample_chart()
    totals = []
    real_footer = natal_pdf._page_footer

    def spy_footer(c, w, page, total=None):
        totals.append(total)
        real_footer(c, w, page, total)

    monkeypatch.setattr(natal_pdf, "_page_footer", spy_footer)

    pdf = generate_natal_pdf(
        user_name="AN",
        birth_date="1997-04-30",
        birth_time="12:55",
        birth_city="Минск",
        sun_sign="Taurus",
        moon_sign="Aquarius",
        asc_sign="Leo",
        planets=planets,
        houses=houses,
        aspects=aspects,
        reading="**Лунные узлы**\nРаху в Деве. Кету в Рыбах.",
    )

    assert pdf.startswith(b"%PDF-")
    assert totals
    assert all(total is None for total in totals)


def test_aspect_fallback_dedup_at_render(monkeypatch):
    """P1-3: даже если два аспекта дали одинаковый fallback, рендер не печатает
    его дважды дословно — второй дубль помечается/убирается."""
    seen = natal_pdf._dedup_aspect_texts(
        [
            "Одинаковый текст-заглушка про напряжение и действие.",
            "Одинаковый текст-заглушка про напряжение и действие.",
            "Другой текст.",
        ]
    )
    # Второй дословный дубль вычищен (None), первый и уникальный — остались.
    assert seen[0] is not None
    assert seen[1] is None
    assert seen[2] is not None


def test_key_card_keeps_whole_first_sentence():
    """P0-2: первый экран не режет первое предложение на полуслове.

    Реальный кейс карты Andrey: «…энергии вашего ядра прямо.» обрывалось,
    хотя полное предложение «…прямо в публичную сферу.» влезает в карточку.
    """
    full = (
        "Солнце в Козероге в десятом доме делает вас человеком цели и репутации, "
        "который годами и упорно направляет всю энергию своего ядра прямо в "
        "публичную сферу и видимый результат. Вы строите имя десятилетиями."
    )
    blurb = natal_pdf_html._card_blurb({"full": full}, "fallback")
    # Первое предложение целиком сохранено — обрыва на «прямо» нет, «…» тоже.
    assert "прямо в публичную сферу и видимый результат." in blurb
    assert not blurb.endswith("…")


def test_key_card_long_sentence_truncates_cleanly():
    """Очень длинное первое предложение всё же режется, но с «…», не битым хвостом."""
    full = (
        "Луна в Раке делает вас человеком, который остро и совершенно постоянно "
        "реагирует буквально на малейшее изменение общего настроения вокруг себя, "
        "впитывает любые чужие эмоции как губка без всякого фильтра, и оттого "
        "нуждается в по-настоящему надёжном тыле гораздо больше многих других "
        "окружающих его людей. Это и дар, и тяжёлая нагрузка."
    )
    blurb = natal_pdf_html._card_blurb({"full": full}, "fallback")
    assert blurb.endswith("…")
    # Не обрывается на висячем предлоге.
    assert not blurb.rstrip("…").endswith((" в", " на", " и", " с", " к"))


def test_aspect_without_description_not_rendered_no_template():
    """Аспект без персонального текста не рендерится (вместо шаблона), а аспект
    с текстом — рендерится. Так шаблонный _aspect_fallback не попадает в PDF."""
    planets, houses, _ = _sample_chart()
    aspects = [
        {"p1": "sun", "p2": "moon", "aspect": "square", "orb": 2.0},
        {"p1": "mars", "p2": "saturn", "aspect": "sextile", "orb": 5.4},
    ]
    document = natal_pdf_html.build_natal_pdf_html(
        user_name="Андрей",
        birth_date="2002-01-23",
        birth_time="12:00",
        birth_city="Москва",
        sun_sign="Aquarius",
        moon_sign="Taurus",
        asc_sign="Libra",
        planets=planets,
        houses=houses,
        aspects=aspects,
        descriptions={
            "planets": {},
            "houses": {},
            # описан только sun-moon; mars-saturn без текста
            "aspects": [
                {
                    "p1": "sun",
                    "p2": "moon",
                    "type": "square",
                    "full": " ".join(f"оwrite{i}" for i in range(60))
                    + " Уникальный разбор этого квадрата.",
                }
            ],
        },
        reading="",
    )
    assert "Уникальный разбор этого квадрата" in document
    # Шаблонные маркеры _aspect_fallback не должны просочиться.
    assert "Здесь встречаются" not in document
    assert "слиты в один импульс" not in document
    assert "не сцеплены жёстко" not in document


def test_aspect_title_css_keeps_orb_top_aligned():
    """Layout: орб привязан к верхней строке заголовка (flex-start), заголовок
    не переносится — иначе орб «уезжал» вниз при переносе на 2 строки."""
    css = natal_pdf_html._css()
    assert "align-items: flex-start" in css
    # .aspect-name не переносится (white-space: nowrap присутствует в блоке).
    assert ".aspect-title .aspect-name" in css
    name_rule = css.split(".aspect-title .aspect-name")[1].split("}")[0]
    assert "white-space: nowrap" in name_rule


def test_pdf_detail_descriptions_do_not_use_short_as_full_source():
    planets, houses, aspects = _sample_chart()
    document = natal_pdf_html.build_natal_pdf_html(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        descriptions={
            "planets": {"sun": {"short": "КОРОТКИЙ_НЕ_ДЛЯ_PDF"}},
            "houses": {"1": {"short": "КОРОТКИЙ_ДОМ_НЕ_ДЛЯ_PDF"}},
            "aspects": [
                {
                    "p1": "sun",
                    "p2": "moon",
                    "type": "square",
                    "short": "КОРОТКИЙ_АСПЕКТ_НЕ_ДЛЯ_PDF",
                }
            ],
        },
    )

    assert "КОРОТКИЙ_НЕ_ДЛЯ_PDF" not in document
    assert "КОРОТКИЙ_ДОМ_НЕ_ДЛЯ_PDF" not in document
    assert "КОРОТКИЙ_АСПЕКТ_НЕ_ДЛЯ_PDF" not in document
    assert natal_pdf._description({"short": "SHORT"}, "FALLBACK") == "FALLBACK"


def test_html_pdf_keeps_long_item_descriptions_untrimmed():
    planets, houses, aspects = _sample_chart()
    long_planet = " ".join(f"планета{i}" for i in range(180)) + " ПЛАНЕТА_ФИНАЛ"
    long_house = " ".join(f"дом{i}" for i in range(150)) + " ДОМ_ФИНАЛ"
    long_aspect = " ".join(f"аспект{i}" for i in range(190)) + " АСПЕКТ_ФИНАЛ"

    document = natal_pdf_html.build_natal_pdf_html(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        descriptions={
            "planets": {"sun": {"full": long_planet}},
            "houses": {"1": {"full": long_house}},
            "aspects": [{"p1": "sun", "p2": "moon", "type": "square", "full": long_aspect}],
        },
    )

    assert "ПЛАНЕТА_ФИНАЛ" in document
    assert "ДОМ_ФИНАЛ" in document
    assert "АСПЕКТ_ФИНАЛ" in document
    # Long descriptions must not be truncated (final markers above) and must
    # span beyond the fixed pages (cover/TOC/key-points/wheel/elements/final).
    assert document.count('<section class="page') >= 12


def test_reportlab_pdf_uses_full_descriptions_without_compact_trimming(monkeypatch):
    planets, houses, aspects = _sample_chart()
    descriptions = {
        "planets": {"sun": {"full": " ".join(f"планета{i}" for i in range(160))}},
        "houses": {"1": {"full": " ".join(f"дом{i}" for i in range(130))}},
        "aspects": [
            {
                "p1": "sun",
                "p2": "moon",
                "type": "square",
                "full": " ".join(f"аспект{i}" for i in range(160)),
            }
        ],
    }

    def fail_compact(*_args, **_kwargs):
        raise AssertionError("PDF descriptions must not be word-trimmed")

    monkeypatch.setattr(natal_pdf, "_compact_description", fail_compact)

    pdf = generate_natal_pdf(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        descriptions=descriptions,
    )

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 10_000


def test_natal_description_batches_are_small_for_long_pdf_copy():
    assert natal_descriptions._BATCH_SIZE == 4
    # Compact 4-item batches keep request count low without bloating max_tokens.
    assert 1500 <= natal_descriptions._BATCH_MAX_TOKENS <= 2200


def test_natal_description_quality_does_not_repair_style_only_duplicates():
    good_body = " ".join(f"слово{i}" for i in range(340))
    repeated = " Повторяющийся финальный совет должен исчезнуть."
    entries = {
        "sun": {"short": "short", "full": good_body + repeated},
        "moon": {"short": "short", "full": good_body + repeated},
    }

    assert natal_descriptions._quality_repair_keys(entries, "planets") == set()


def test_natal_description_quality_keeps_duplicate_starts_without_extra_llm_calls():
    body = " ".join(f"слово{i}" for i in range(340))
    entries = {
        "sun": {
            "short": "short",
            "full": f"Одинаковое начало должно быть переписано. {body} Первый финал.",
        },
        "moon": {
            "short": "short",
            "full": f"Одинаковое начало должно быть переписано. {body} Второй финал.",
        },
    }

    assert natal_descriptions._quality_repair_keys(entries, "planets") == set()


def test_natal_description_quality_repairs_copy_markers_only():
    detailed = " ".join(f"слово{i}" for i in range(340))
    assert natal_descriptions._entry_needs_repair(
        {"short": "short", "full": f"{detailed} Читать далее..."},
        "planets",
    )
    assert not natal_descriptions._entry_needs_repair(
        {
            "short": "Это короткое описание почти целиком повторяется.",
            "full": "Это короткое описание почти целиком повторяется. "
            + " ".join(f"дополнение{i}" for i in range(250))
            + ".",
        },
        "houses",
    )


@pytest.mark.asyncio
async def test_natal_description_repair_replaces_bad_entries(monkeypatch):
    async def fake_one_entry(*_args, **_kwargs):
        return {
            "short": "Новый короткий текст.",
            "full": " ".join(f"новый{i}" for i in range(340)) + " Совершенно другой финал.",
        }

    monkeypatch.setattr(natal_descriptions, "_one_entry", fake_one_entry)
    repaired = await natal_descriptions._repair_entries(
        client=object(),
        entries={"sun": {"short": "Коротко.", "full": ""}},
        labels={"sun": "Солнце в Скорпионе"},
        section="planets",
        chart_context="Контекст всей натальной карты",
    )

    assert repaired["sun"]["full"].startswith("новый0")
    assert "Совершенно другой финал" in repaired["sun"]["full"]


@pytest.mark.asyncio
async def test_repair_runs_second_cycle_when_first_still_bad(monkeypatch):
    """Цикл repair: если 1-я регенерация вернула плохой текст, делается 2-я."""
    calls = {"n": 0}

    async def fake_one_entry(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            # 1-й repair — всё ещё слишком короткий (плохой).
            return {"short": "Коротко.", "full": "Очень короткий плохой текст."}
        # 2-й repair — годный длинный текст.
        return {
            "short": "Новый короткий текст про Солнце в знаке.",
            "full": " ".join(f"слово{i}" for i in range(340)) + " Уникальный финал.",
        }

    monkeypatch.setattr(natal_descriptions, "_one_entry", fake_one_entry)
    repaired = await natal_descriptions._repair_entries(
        client=object(),
        entries={"sun": {"short": "Коротко.", "full": ""}},
        labels={"sun": "Солнце в Козероге"},
        section="planets",
        chart_context="Контекст всей натальной карты",
    )

    # Должно было быть минимум 2 вызова (1-й плохой → 2-й годный).
    assert calls["n"] >= 2
    assert "Уникальный финал" in repaired["sun"]["full"]


@pytest.mark.asyncio
async def test_repair_keeps_good_text_does_not_downgrade(monkeypatch):
    """Цикл repair не заменяет уже годный текст на худший."""
    good_full = " ".join(f"хорошо{i}" for i in range(340)) + " Качественный финал."

    async def fake_one_entry(*_args, **_kwargs):
        return {"short": "Хуже.", "full": "Деградировавший короткий ответ."}

    monkeypatch.setattr(natal_descriptions, "_one_entry", fake_one_entry)
    repaired = await natal_descriptions._repair_entries(
        client=object(),
        entries={"sun": {"short": "Норм.", "full": good_full}},
        labels={"sun": "Солнце в Козероге"},
        section="planets",
        chart_context="Контекст",
    )
    # Годный текст не трогали — repair даже не запускался для него.
    assert repaired["sun"]["full"] == good_full


@pytest.mark.asyncio
async def test_get_or_generate_descriptions_regenerates_stale_cached_text(monkeypatch):
    from api.routes import natal

    chart = SimpleNamespace(
        chart_data={
            "planets": {"sun": {"sign": "Capricorn", "house": 10}},
            "houses": [],
            "aspects": [],
            "descriptions": {"planets": {"sun": {"full": "Старый короткий текст."}}},
        }
    )
    user = SimpleNamespace(id=1001, natal_chart=chart, gender=None)
    db = SimpleNamespace(committed=False)

    async def fake_commit():
        db.committed = True

    async def fake_generate_natal_descriptions(**_kwargs):
        return {
            "planets": {"sun": {"full": "Новый полный справочный текст."}},
            "houses": {},
            "aspects": [],
        }

    db.commit = fake_commit
    monkeypatch.setattr(natal.settings, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(natal, "generate_natal_descriptions", fake_generate_natal_descriptions)

    descriptions = await natal._get_or_generate_descriptions(db, user)

    assert descriptions["planets"]["sun"]["full"] == "Новый полный справочный текст."
    assert descriptions["_version"] == natal.NATAL_DESCRIPTIONS_VERSION
    assert chart.chart_data["descriptions"] == descriptions
    assert db.committed is True


@pytest.mark.asyncio
async def test_get_or_generate_descriptions_rejects_shifted_house_keys(monkeypatch):
    from api.routes import natal

    broken_houses = {str(i): {"full": f"Дом {i}"} for i in range(0, 12)}
    chart = SimpleNamespace(
        chart_data={
            "planets": {"sun": {"sign": "Capricorn", "house": 10}},
            "houses": [],
            "aspects": [],
            "descriptions": {
                "_version": natal.NATAL_DESCRIPTIONS_VERSION,
                "_gender_used": None,
                "planets": {"sun": {"full": "Старое Солнце."}},
                "houses": broken_houses,
                "aspects": [],
            },
        }
    )
    user = SimpleNamespace(id=1001, natal_chart=chart, gender=None)
    db = SimpleNamespace(committed=False)

    async def fake_commit():
        db.committed = True

    async def fake_generate_natal_descriptions(**_kwargs):
        return {
            "planets": {"sun": {"full": "Новый корректный текст."}},
            "houses": {},
            "aspects": [],
        }

    db.commit = fake_commit
    monkeypatch.setattr(natal.settings, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(natal, "generate_natal_descriptions", fake_generate_natal_descriptions)

    descriptions = await natal._get_or_generate_descriptions(db, user)

    assert descriptions["planets"]["sun"]["full"] == "Новый корректный текст."
    assert db.committed is True


def test_stored_descriptions_rejects_shifted_house_keys():
    from api.routes import natal

    broken_houses = {str(i): {"full": f"Дом {i}"} for i in range(0, 12)}
    user = SimpleNamespace(
        gender=None,
        natal_chart=SimpleNamespace(
            chart_data={
                "descriptions": {
                    "_version": natal.NATAL_DESCRIPTIONS_VERSION,
                    "_gender_used": None,
                    "planets": {"sun": {"full": "Солнце."}},
                    "houses": broken_houses,
                    "aspects": [],
                }
            }
        ),
    )

    assert natal._get_stored_descriptions(user) == natal._empty_descriptions()


@pytest.mark.asyncio
async def test_get_natal_full_refreshes_short_cached_reading(monkeypatch):
    from api.routes import natal

    chart = SimpleNamespace(
        chart_data={
            "planets": {"sun": {"sign": "Scorpio", "house": 9}},
            "aspects": [{"p1": "Sun", "p2": "Moon", "aspect": "square", "orb": 1.2}],
        },
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        ascendant_sign="Aries",
    )
    user = SimpleNamespace(id=1001, natal_chart=chart, gender=None)
    cached = {"reading": "**Ядро личности**\nКоротко.", "planets": chart.chart_data["planets"]}
    refreshed_text = "\n".join(
        [
            "**Ядро личности**",
            "слово " * 140,
            "**Ум и общение**",
            "слово " * 140,
            "**Любовь и ценности**",
            "слово " * 140,
            "**Энергия и воля**",
            "слово " * 140,
            "**Удача и вызовы**",
            "слово " * 140,
        ]
    )
    calls = {}

    async def fake_get_by_id(_db, user_id):
        assert user_id == 1001
        return user

    async def fake_true(_db, user_id, *_args):
        assert user_id == 1001
        return True

    async def fake_cache_get(key):
        assert key == "natal:1001"
        return cached

    async def fake_cache_set(key, value, ttl):
        calls["cache_set"] = (key, value, ttl)

    async def fake_generate_natal_reading(**kwargs):
        calls["reading_kwargs"] = kwargs
        return refreshed_text

    monkeypatch.setattr(natal.user_repo, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(natal.user_repo, "is_premium", fake_true)
    monkeypatch.setattr(natal.user_repo, "has_purchased", fake_true)
    monkeypatch.setattr(natal, "cache_get", fake_cache_get)
    monkeypatch.setattr(natal, "cache_set", fake_cache_set)
    monkeypatch.setattr(natal.settings, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(natal, "generate_natal_reading", fake_generate_natal_reading)

    result = await natal.get_natal_full(tg_user={"id": 1001}, db=object())

    assert result["reading"] == refreshed_text
    assert result["planets"] == chart.chart_data["planets"]
    assert calls["reading_kwargs"]["aspects"] == chart.chart_data["aspects"]
    assert calls["cache_set"][0] == "natal:1001"
    assert calls["cache_set"][1]["reading"] == refreshed_text
    assert calls["cache_set"][1]["reading_version"] == natal.NATAL_READING_VERSION


@pytest.mark.asyncio
async def test_create_natal_pdf_link_returns_temporary_download_payload(monkeypatch):
    from api.routes import natal

    async def fake_get_user(_db, user_id):
        return SimpleNamespace(id=user_id, tg_first_name="Андрей")

    calls = {}

    async def fake_cache_set(key, value, ttl):
        calls["key"] = key
        calls["value"] = value
        calls["ttl"] = ttl

    monkeypatch.setattr(natal, "_get_pdf_user_or_error", fake_get_user)
    monkeypatch.setattr(natal, "cache_set", fake_cache_set)
    monkeypatch.setattr(natal, "token_urlsafe", lambda _size: "token-123")

    payload = await natal.create_natal_pdf_link(tg_user={"id": 1001}, db=object())

    assert payload == {
        "download_url": "/natal/pdf-download/token-123",
        "filename": "natal_Андрей.pdf",
        "expires_in": 300,
    }
    assert calls == {
        "key": "natal:pdf-download:token-123",
        "value": {"user_id": 1001},
        "ttl": 300,
    }


@pytest.mark.asyncio
async def test_natal_pdf_token_download_does_not_require_telegram_auth(monkeypatch):
    from api.routes import natal

    async def fake_cache_get(key):
        assert key == "natal:pdf-download:token-123"
        return {"user_id": 1001}

    async def fake_get_user(_db, user_id):
        assert user_id == 1001
        return SimpleNamespace(id=user_id, tg_first_name="Андрей")

    async def fake_build_pdf(_db, user, *, require_ready_cache=False):
        assert user.id == 1001
        assert require_ready_cache is False
        return b"%PDF-test"

    monkeypatch.setattr(natal, "cache_get", fake_cache_get)
    monkeypatch.setattr(natal, "_get_pdf_user_or_error", fake_get_user)
    monkeypatch.setattr(natal, "_build_natal_pdf_bytes", fake_build_pdf)

    response = await natal.get_natal_pdf_by_token("token-123", db=object())

    assert response.body == b"%PDF-test"
    assert response.media_type == "application/pdf"


@pytest.mark.asyncio
async def test_ready_pdf_token_download_does_not_generate_llm(monkeypatch):
    from api.routes import natal

    async def fake_cache_get(key):
        assert key == "natal:pdf-download:token-123"
        return {"user_id": 1001, "ready": True}

    async def fake_get_user(_db, user_id):
        assert user_id == 1001
        return SimpleNamespace(id=user_id, tg_first_name="Андрей")

    async def fake_build_pdf(_db, user, *, require_ready_cache=False):
        assert user.id == 1001
        assert require_ready_cache is True
        return b"%PDF-ready"

    monkeypatch.setattr(natal, "cache_get", fake_cache_get)
    monkeypatch.setattr(natal, "_get_pdf_user_or_error", fake_get_user)
    monkeypatch.setattr(natal, "_build_natal_pdf_bytes", fake_build_pdf)

    response = await natal.get_natal_pdf_by_token("token-123", db=object())

    assert response.body == b"%PDF-ready"
    assert response.media_type == "application/pdf"


@pytest.mark.asyncio
async def test_send_natal_pdf_to_telegram_generates_and_sends_document(monkeypatch):
    from api.routes import natal

    user = SimpleNamespace(id=1001, tg_first_name="Андрей")
    calls = {}

    async def fake_get_user(_db, user_id):
        assert user_id == 1001
        return user

    async def fake_build_pdf(_db, pdf_user):
        assert pdf_user is user
        calls["generated"] = True
        return b"%PDF-test"

    async def fake_send(pdf_user, pdf_bytes):
        assert pdf_user is user
        calls["sent_bytes"] = pdf_bytes

    monkeypatch.setattr(natal, "_get_pdf_user_or_error", fake_get_user)
    monkeypatch.setattr(natal, "_build_natal_pdf_bytes", fake_build_pdf)
    monkeypatch.setattr(natal, "_send_natal_pdf_document", fake_send)

    payload = await natal.send_natal_pdf_to_telegram(tg_user={"id": 1001}, db=object())

    assert payload == {"status": "sent", "filename": "natal_Андрей.pdf"}
    assert calls == {"generated": True, "sent_bytes": b"%PDF-test"}


@pytest.mark.asyncio
async def test_build_natal_pdf_response_blocks_until_full_copy_ready(monkeypatch):
    # On-demand model: the download BLOCKS until personal descriptions and
    # reading are generated, then renders one complete PDF — no fallback-first.
    from api.routes import natal
    from services import natal_pdf, natal_pdf_html

    chart = SimpleNamespace(
        chart_data={
            "planets": {"sun": {"sign": "scorpio"}},
            "houses": [],
            "aspects": [],
        },
        sun_sign="scorpio",
        moon_sign="aries",
        ascendant_sign="capricorn",
    )
    user = SimpleNamespace(
        id=1001,
        tg_first_name="Андрей",
        birth_date=None,
        birth_time_known=False,
        birth_city="Минск",
        natal_chart=chart,
        gender=None,
    )
    calls = {}
    full_descriptions = {"planets": {"sun": {"short": "s", "full": "f"}}}

    async def fake_descriptions(_db, _user):
        calls["descriptions_called"] = True
        return full_descriptions

    async def fake_reading(_user, _chart, _planets, _aspects):
        calls["reading_called"] = True
        return "Полный персональный разбор."

    async def fake_cache_get(key):
        calls.setdefault("cache_keys", []).append(key)
        return None

    def fake_generate_natal_pdf(**kwargs):
        calls["pdf_kwargs"] = kwargs
        return b"%PDF-full"

    async def fake_generate_natal_pdf_html(**_kwargs):
        raise RuntimeError("chromium unavailable")

    monkeypatch.setattr(natal, "_get_or_generate_descriptions", fake_descriptions)
    monkeypatch.setattr(natal, "_get_or_generate_pdf_reading", fake_reading)
    monkeypatch.setattr(natal, "cache_get", fake_cache_get)
    monkeypatch.setattr(natal_pdf_html, "generate_natal_pdf_html", fake_generate_natal_pdf_html)
    monkeypatch.setattr(natal_pdf, "generate_natal_pdf", fake_generate_natal_pdf)

    response = await natal._build_natal_pdf_response(db=object(), user=user)

    assert response.body == b"%PDF-full"
    assert calls["descriptions_called"] is True
    assert calls["reading_called"] is True
    assert calls["pdf_kwargs"]["descriptions"] == full_descriptions
    assert calls["pdf_kwargs"]["reading"] == "Полный персональный разбор."


@pytest.mark.asyncio
async def test_pdf_reading_is_generated_when_full_chart_cache_is_cold(monkeypatch):
    from api.routes import natal

    calls = {}
    chart = SimpleNamespace(
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        ascendant_sign="Aries",
    )
    planets = {"sun": {"sign": "Scorpio"}}
    aspects = [{"p1": "Sun", "p2": "Moon", "aspect": "square", "orb": 1.2}]
    user = SimpleNamespace(id=1001, gender=None)

    async def fake_cache_get(key):
        calls["cache_get_key"] = key
        return None

    async def fake_cache_set(key, value, ttl):
        calls["cache_set"] = (key, value, ttl)

    async def fake_reading(**kwargs):
        calls["reading_kwargs"] = kwargs
        return "Полное итоговое чтение карты."

    monkeypatch.setattr(natal, "cache_get", fake_cache_get)
    monkeypatch.setattr(natal, "cache_set", fake_cache_set)
    monkeypatch.setattr(natal.settings, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(natal, "generate_natal_reading", fake_reading)

    reading = await natal._get_or_generate_pdf_reading(user, chart, planets, aspects)

    assert reading == "Полное итоговое чтение карты."
    assert calls["reading_kwargs"]["aspects"] == aspects
    assert calls["cache_set"][1]["reading_version"] == natal.NATAL_READING_VERSION


class _FakeRedis:
    """Minimal Redis stand-in for the dedup SET NX behaviour."""

    def __init__(self, store=None):
        self.store = dict(store or {})

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)


@pytest.mark.asyncio
async def test_start_pdf_fast_path_returns_ready_without_enqueue(monkeypatch):
    # Warm cache: descriptions fresh + reading fresh → mint token, status ready,
    # never touch the queue.
    from api.routes import natal

    user = SimpleNamespace(id=1001, tg_first_name="Андрей", gender=None)
    calls = {}

    async def fake_user(_db, _uid):
        return user

    async def fake_cache_get(_key):
        return {"reading": "x", "reading_gender": None}

    async def fake_cache_set(key, value, ttl):
        calls.setdefault("cache_set", []).append(key)

    def fail_enqueue():
        raise AssertionError("fast-path must not enqueue")

    monkeypatch.setattr(natal, "_get_pdf_user_or_error", fake_user)
    monkeypatch.setattr(natal, "_get_stored_descriptions", lambda u: {"planets": {"sun": {}}})
    monkeypatch.setattr(natal, "_reading_is_fresh", lambda c, g: "reading-text")
    monkeypatch.setattr(natal, "cache_get", fake_cache_get)
    monkeypatch.setattr(natal, "cache_set", fake_cache_set)
    monkeypatch.setattr("services.arq_pool.get_arq_pool", fail_enqueue)

    res = await natal.start_natal_pdf(tg_user={"id": 1001}, db=object())

    assert res.status == "ready"
    assert res.download_token
    assert any("pdf-download" in k for k in calls["cache_set"])


@pytest.mark.asyncio
async def test_start_pdf_dedups_concurrent_requests(monkeypatch):
    # Second call while a job lock is held returns the existing job, no 2nd enqueue.
    from api.routes import natal

    user = SimpleNamespace(id=1001, tg_first_name="Андрей", gender=None)
    redis = _FakeRedis()
    enqueue_count = {"n": 0}

    async def fake_user(_db, _uid):
        return user

    async def fake_cache_get(_key):
        return None  # reading not fresh → no fast-path

    async def fake_set_status(job_id, status, **fields):
        pass

    async def fake_get_status(job_id):
        return {"status": "processing"}

    class FakePool:
        async def enqueue_job(self, *a, **k):
            enqueue_count["n"] += 1

    monkeypatch.setattr(natal, "_get_pdf_user_or_error", fake_user)
    monkeypatch.setattr(natal, "_get_stored_descriptions", lambda u: {})
    monkeypatch.setattr(natal, "_reading_is_fresh", lambda c, g: None)
    monkeypatch.setattr(natal, "cache_get", fake_cache_get)
    monkeypatch.setattr(natal, "get_redis", lambda: redis)
    monkeypatch.setattr("services.job_status.set_job_status", fake_set_status)
    monkeypatch.setattr("services.job_status.get_job_status", fake_get_status)
    monkeypatch.setattr("services.arq_pool.get_arq_pool", lambda: FakePool())

    first = await natal.start_natal_pdf(tg_user={"id": 1001}, db=object())
    second = await natal.start_natal_pdf(tg_user={"id": 1001}, db=object())

    assert first.status == "queued"
    assert second.job_id == first.job_id  # same job returned
    assert enqueue_count["n"] == 1  # enqueued exactly once


# ── Generation-quality fixes (validator-driven) ────────────────────────


def test_outer_planet_fallback_drops_generational_label():
    """Уран/Нептун/Плутон в fallback не должны нести поколенческий ярлык —
    для индивидуального отчёта он одинаков для миллионов и читается как заглушка."""
    from services.quality_validator import (
        TextValidator,
        ValidationContext,
    )

    v = TextValidator(use_spellchecker=False)
    for sign_ru_name, house in [("Водолей", 6), ("Рыбы", 12)]:
        text = natal_pdf._planet_fallback("uranus", {"sign_ru": sign_ru_name, "house": house})
        assert "поколение" not in text.lower()
        assert "цифровое поколение" not in text.lower()
        codes = {i.code for i in v.validate(text, ValidationContext("planet_in_sign", "x"))}
        assert "GENERATIONAL_IN_INDIVIDUAL" not in codes
        # дом подаётся конкретной сферой жизни, а не «уточняет в какой сфере»
        assert f"В {house}-м доме" in text


def test_aspect_fallback_not_a_template_stub():
    """Generic-fallback аспекта больше не содержит фраз-болванок, которые ловит
    валидатор (аспект возможности / чем точнее орб)."""
    from services.quality_validator import TextValidator, ValidationContext

    v = TextValidator(use_spellchecker=False)
    text = natal_pdf._aspect_fallback(
        {"p1": "jupiter", "p2": "saturn", "aspect": "sextile", "orb": 4.0}
    )
    assert "аспект возможности" not in text.lower()
    assert "чем точнее орб" not in text.lower()
    codes = {i.code for i in v.validate(text, ValidationContext("aspect", "j-s"))}
    assert "TEMPLATE_PHRASE" not in codes


def test_hidden_aspect_dropped_from_pdf():
    """Аспект с флагом hide=True не рендерится в PDF (скрываем болванки)."""
    planets = {
        "sun": {"sign": "taurus", "sign_ru": "Телец", "house": 10, "degree": 12.0},
        "moon": {"sign": "aries", "sign_ru": "Овен", "house": 9, "degree": 5.0},
    }
    houses = [
        {"number": i, "sign": "aries", "sign_ru": "Овен", "degree": 0.0} for i in range(1, 13)
    ]
    aspects = [
        {"p1": "sun", "p2": "moon", "aspect": "trine", "orb": 2.0},
        {"p1": "sun", "p2": "mars", "aspect": "square", "orb": 1.0},
    ]
    descriptions = {
        "planets": {},
        "houses": {},
        "aspects": [
            {"p1": "sun", "p2": "mars", "type": "square", "full": "болванка", "hide": True},
        ],
    }
    aspect_desc = natal_pdf._aspect_description_map(descriptions)
    assert natal_pdf._aspect_hidden(aspects[1], aspect_desc) is True
    assert natal_pdf._aspect_hidden(aspects[0], aspect_desc) is False
    pdf = generate_natal_pdf(
        user_name="Тест",
        birth_date="2000-05-01",
        birth_time="12:00",
        birth_city="Москва",
        sun_sign="taurus",
        moon_sign="aries",
        asc_sign="aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        descriptions=descriptions,
    )
    assert pdf.startswith(b"%PDF-")


# ── Layer 1+2: секционные цели → thin-репейр без ложных срабатываний ────


def test_section_targets_aligned_with_prompts():
    """Цели согласованы с верхними ориентирами промптов (houses/aspects ~120/140)."""
    assert natal_descriptions._MIN_FULL_WORDS == {
        "planets": 90,
        "houses": 120,
        "aspects": 140,
    }


def test_thin_aspect_sent_to_repair():
    """Аспект ~90 слов при цели 140 (floor 112) → TOO_SHORT_THIN → repair."""
    text = (
        "Венера в трине к Марсу соединяет нежность и напор: натив умеет и "
        "желать, и заботиться, не теряя одно ради другого человека рядом. "
        "В отношениях он берёт инициативу мягко, без давления, и партнёр "
        "чувствует одновременно страсть и безопасность одновременно. В работе "
        "это придаёт обаяние переговорщика — он добивается своего, не наживая "
        "врагов вокруг себя. Сильная сторона — притягательность и лёгкость "
        "в сближении с новыми людьми. Зона роста — не путать лёгкость с "
        "поверхностностью, доводить близость до настоящей глубины чувств."
    )
    entry = {"short": "коротко", "full": text}
    assert natal_descriptions._entry_needs_repair(entry, "aspects") is True


def test_important_bad_aspect_gets_full_quality_fallback():
    text = natal_descriptions._aspect_quality_fallback("venus", "saturn", "opposition", 1.6)

    assert "Венера — оппозиция — Сатурн" in text
    assert "Орб 1.6°" in text
    assert len(text.split()) >= 100
    assert "не рассчитан" not in text


def test_compact_planet_not_sent_to_repair():
    """Планета в районе цели (≥floor 72) НЕ уходит в repair (anti-false-positive)."""
    body = " ".join(f"факт{i}" for i in range(85))
    entry = {"short": "коротко", "full": f"Меркурий в Близнецах. {body}."}
    assert natal_descriptions._entry_needs_repair(entry, "planets") is False


# ── Layer 3: финальный synthesis — обрыв → один повтор ─────────────────


@pytest.mark.asyncio
async def test_reading_retries_on_truncation(monkeypatch):
    """Обрыв на полуслове (stop_reason=max_tokens) → повтор с большим лимитом."""
    planets, _houses, aspects = _sample_chart()
    seq = [
        # 1-й вызов: текст оборван на полуслове + stop_reason max_tokens
        SimpleNamespace(
            content=[SimpleNamespace(text="Главное противоречие вашей карты — вы строите карь")],
            stop_reason="max_tokens",
        ),
        # 2-й вызов (retry): полноценный завершённый текст
        SimpleNamespace(
            content=[
                SimpleNamespace(text=" ".join(f"слово{i}" for i in range(200)) + " финал завершён.")
            ],
            stop_reason="end_turn",
        ),
    ]
    seen = []

    class FakeMessages:
        async def create(self, **kwargs):
            seen.append(kwargs["max_tokens"])
            return seq[len(seen) - 1]

    class FakeAnthropic:
        def __init__(self, api_key):
            self.messages = FakeMessages()

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(AsyncAnthropic=FakeAnthropic))

    reading = await llm_interpreter.generate_natal_reading(
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        ascendant_sign="Aries",
        planets=planets,
        aspects=aspects,
        api_key="k",
    )

    assert len(seen) == 2, "должен быть ровно один повтор"
    assert seen[1] > seen[0], "повтор с увеличенным лимитом токенов"
    assert reading.endswith("завершён.")


@pytest.mark.asyncio
async def test_reading_no_retry_when_complete(monkeypatch):
    """Полноценный завершённый разбор → ровно один вызов, без лишнего повтора."""
    planets, _houses, aspects = _sample_chart()
    full = " ".join(f"слово{i}" for i in range(300)) + " финал."
    seen = []

    class FakeMessages:
        async def create(self, **kwargs):
            seen.append(kwargs["max_tokens"])
            return SimpleNamespace(content=[SimpleNamespace(text=full)], stop_reason="end_turn")

    class FakeAnthropic:
        def __init__(self, api_key):
            self.messages = FakeMessages()

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(AsyncAnthropic=FakeAnthropic))

    reading = await llm_interpreter.generate_natal_reading(
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        ascendant_sign="Aries",
        planets=planets,
        aspects=aspects,
        api_key="k",
    )

    assert len(seen) == 1, "завершённый текст не должен вызывать повтор"
    assert reading == full
