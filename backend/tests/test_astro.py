"""Unit tests for astro calculation services."""

from datetime import datetime, timedelta

import pytest

from services.astro.moon import get_moon_phase
from services.astro.natal import calculate_natal, chart_to_json
from services.astro.synastry import calculate_synastry
from services.astro.transits import build_energy_scores


def test_natal_calculation_scorpio():
    chart = calculate_natal(
        name="Test",
        birth_dt=datetime(1990, 11, 5, 14, 30),
        lat=55.7558,
        lng=37.6176,
        tz_str="Europe/Moscow",
        birth_time_known=True,
    )
    assert chart.sun.sign == "Scorpio"
    assert chart.moon is not None
    assert len(chart.houses) == 12
    assert chart.ascendant_sign is not None


def test_natal_no_birth_time():
    """Should fall back to noon, no ascendant in strict mode."""
    chart = calculate_natal(
        name="Test",
        birth_dt=datetime(1985, 3, 21, 0, 0),
        lat=48.8566,
        lng=2.3522,
        tz_str="Europe/Paris",
        birth_time_known=False,
    )
    assert chart.sun.sign == "Aries"


def test_chart_to_json_serialisable():
    chart = calculate_natal(
        name="Test",
        birth_dt=datetime(1990, 6, 15, 12, 0),
        lat=51.5074,
        lng=-0.1278,
        tz_str="Europe/London",
    )
    data = chart_to_json(chart)
    import json

    json.dumps(data)  # must not raise


def test_natal_aspects_match_reference_planet_only_style():
    chart = calculate_natal(
        name="Dev",
        birth_dt=datetime(2000, 10, 20, 12, 0),
        lat=53.9023,
        lng=27.5619,
        tz_str="Europe/Minsk",
    )

    aspects = {(a.aspect, a.p1, a.p2): a.orb for a in chart.aspects}
    assert ("square", "Sun", "Moon") in aspects
    assert ("square", "Sun", "Neptune") in aspects
    assert ("sextile", "Moon", "Mars") in aspects
    assert ("trine", "Jupiter", "Uranus") in aspects
    assert all("Node" not in a.p1 + a.p2 for a in chart.aspects)
    assert all("Lilith" not in a.p1 + a.p2 for a in chart.aspects)


def test_synastry_manual_like_calculation():
    """Manual synastry should handle Cyrillic names and unknown partner time."""
    result = calculate_synastry(
        user_a={
            "name": "Андрей",
            "birth_dt": datetime(1998, 7, 1, 12, 0),
            "lat": 53.9,
            "lng": 27.5667,
            "tz_str": "Europe/Minsk",
            "birth_time_known": False,
        },
        user_b={
            "name": "миша",
            "birth_dt": datetime(2000, 4, 18, 12, 0),
            "lat": 55.6026007,
            "lng": 37.3479176,
            "tz_str": "Europe/Moscow",
            "birth_time_known": False,
        },
    )

    assert result["total_aspects"] > 0
    assert 15 <= result["scores"]["overall"] <= 95


def test_synastry_timezone_fallback_without_coordinates():
    import asyncio

    from api.routes.synastry import _resolve_synastry_timezone

    assert asyncio.run(_resolve_synastry_timezone("Bad/Timezone", None, None)) == "UTC"


def test_synastry_manual_input_rejects_under_14_partner():
    from api.schemas.synastry import (
        MIN_SYNASTRY_AGE,
        SynastryManualInput,
        _date_years_ago,
    )

    birthday_too_young = _date_years_ago(MIN_SYNASTRY_AGE) + timedelta(days=1)

    with pytest.raises(ValueError, match="не меньше 14 лет"):
        SynastryManualInput(
            partner_name="Анна",
            birth_date=birthday_too_young,
            birth_time="12:00",
            birth_time_known=False,
            birth_city="Минск",
        )


def test_synastry_manual_input_allows_14_plus_partner():
    from api.schemas.synastry import (
        MIN_SYNASTRY_AGE,
        SynastryManualInput,
        _date_years_ago,
    )

    birthday_14_plus = _date_years_ago(MIN_SYNASTRY_AGE)

    payload = SynastryManualInput(
        partner_name="Анна",
        birth_date=birthday_14_plus,
        birth_time="12:00",
        birth_time_known=False,
        birth_city="Минск",
    )

    assert payload.birth_date == birthday_14_plus


def test_energy_scores_clamped():
    scores = build_energy_scores([], "scorpio")
    for v in scores.values():
        assert 20 <= v <= 95


def test_moon_phase_returns():
    phase = get_moon_phase()
    assert phase.phase_name
    assert 0.0 <= phase.illumination <= 1.0
    assert phase.emoji


def test_tarot_engine():
    from services.tarot.engine import draw_spread

    card_ids = list(range(1, 79))
    result = draw_spread("three_card", card_ids, seed=42)
    assert len(result.cards) == 3
    # All drawn cards are unique
    drawn_ids = [c.card_id for c in result.cards]
    assert len(set(drawn_ids)) == 3


def test_tarot_premium_spread():
    from services.tarot.engine import draw_spread

    card_ids = list(range(1, 79))
    result = draw_spread("celtic_cross", card_ids, seed=99)
    assert len(result.cards) == 10


def test_lunar_nodes_in_chart_json():
    """P1-2: лунные узлы (Раху/Кету) попадают в chart_data["nodes"], НЕ в planets."""
    chart = calculate_natal(
        name="AN",
        birth_dt=datetime(1997, 4, 30, 12, 55),
        lat=53.9023,
        lng=27.5667,
        tz_str="Europe/Minsk",
    )
    data = chart_to_json(chart)
    planets = data["planets"]
    nodes = data["nodes"]
    # Узлы — отдельный канал, НЕ среди планет (иначе ломают подсчёт стихий/hero).
    assert "true_north_lunar_node" not in planets
    assert "true_south_lunar_node" not in planets
    assert "true_north_lunar_node" in nodes
    assert "true_south_lunar_node" in nodes
    north = nodes["true_north_lunar_node"]
    assert north.get("sign")
    assert 1 <= int(north.get("house") or 0) <= 12
    # Узлы НЕ участвуют в аспектах и не считаются планетами в круге.
    assert all("Node" not in a.p1 + a.p2 for a in chart.aspects)
    classical = {
        "sun",
        "moon",
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
        "pluto",
    }
    assert set(planets) == classical


def test_nodes_do_not_affect_element_counts():
    """Регрессия: узлы не должны влиять на подсчёт стихий (AN = 50/30/20/0)."""
    from services.natal_pdf_html import _element_percentages

    chart = calculate_natal(
        name="AN",
        birth_dt=datetime(1997, 4, 30, 12, 55),
        lat=53.9023,
        lng=27.5667,
        tz_str="Europe/Minsk",
    )
    planets = chart_to_json(chart)["planets"]
    perc = _element_percentages(planets)
    # Эталон astro-online по 10 классическим планетам.
    assert perc.get("earth") == 50
    assert perc.get("air") == 30
    assert perc.get("fire") == 20
    assert perc.get("water", 0) == 0


def test_house_descriptions_keys_match_house_numbers():
    """P0-1: при чанк-генерации домов ключи остаются реальными номерами 1..12.

    Мокаем LLM-вызов так, чтобы он возвращал ответы, ключованные ИМЕННО по тем
    номерам, что перечислены в промпте (как сделал бы корректный LLM). Раньше
    промпт всегда просил «1..count», и чанки 5-8 / 9-12 перетирали 1-4.
    """
    import asyncio
    import re

    import services.astro.natal_descriptions as nd

    houses = [
        {"number": n, "sign_ru": "Овен", "sign": "aries", "degree": 0.0} for n in range(1, 13)
    ]
    planets = {
        "sun": {"sign": "taurus", "sign_ru": "Телец", "house": 10, "sign_degree": 9.0},
    }

    async def fake_call_tool_chunk(client, prompt, tool_name, keys, max_tokens):
        # Корректный LLM возвращает ровно те ключи, которые перечислены в промпте.
        nums = re.findall(r'"(\d+)"', prompt.split("Используй ИМЕННО эти номера")[-1])
        return {
            num: {"short": f"short {num}", "full": f"full дом {num} " + "слово " * 120}
            for num in (nums or keys)
        }

    async def run():
        # Узлы/аспекты не нужны для этого теста.
        return await nd.generate_natal_descriptions(
            planets=planets,
            houses=houses,
            aspects=[],
            api_key="test",
            gender=None,
        )

    orig_chunk = nd._call_tool_chunk
    orig_repair = nd._repair_entries
    nd._call_tool_chunk = fake_call_tool_chunk

    async def no_repair(client, entries, labels, section, chart_context):
        return entries

    nd._repair_entries = no_repair
    try:
        result = asyncio.run(run())
    finally:
        nd._call_tool_chunk = orig_chunk
        nd._repair_entries = orig_repair

    house_keys = set(result["houses"].keys())
    assert house_keys == {str(n) for n in range(1, 13)}, house_keys
    # Дом 1 содержит свой текст, не текст дома 4.
    assert "дом 1" in result["houses"]["1"]["full"]
    assert "дом 4" in result["houses"]["4"]["full"]


def test_aspect_fallback_unique_per_pair():
    """P1-3: разные пары планет одного типа аспекта дают разный fallback-текст."""
    from services.natal_pdf import _aspect_fallback

    a1 = {"p1": "jupiter", "p2": "saturn", "aspect": "opposition", "orb": 5.0}
    a2 = {"p1": "saturn", "p2": "uranus", "aspect": "opposition", "orb": 5.0}
    t1 = _aspect_fallback(a1)
    t2 = _aspect_fallback(a2)
    assert t1 and t2
    assert t1 != t2
