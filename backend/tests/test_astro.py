"""Unit tests for astro calculation services."""
from datetime import datetime

from services.astro.compatibility import calculate_compatibility
from services.astro.moon import get_moon_phase
from services.astro.natal import calculate_natal, chart_to_json
from services.astro.synastry import calculate_synastry
from services.astro.transits import build_energy_scores


def test_natal_calculation_scorpio():
    chart = calculate_natal(
        name="Test",
        birth_dt=datetime(1990, 11, 5, 14, 30),
        lat=55.7558, lng=37.6176,
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
        lat=48.8566, lng=2.3522,
        tz_str="Europe/Paris",
        birth_time_known=False,
    )
    assert chart.sun.sign == "Aries"


def test_chart_to_json_serialisable():
    chart = calculate_natal(
        name="Test", birth_dt=datetime(1990, 6, 15, 12, 0),
        lat=51.5074, lng=-0.1278, tz_str="Europe/London",
    )
    data = chart_to_json(chart)
    import json
    json.dumps(data)  # must not raise


def test_compatibility_trine():
    result = calculate_compatibility("aries", "leo")
    assert result.overall >= 80
    assert result.tier == "high"


def test_compatibility_square():
    result = calculate_compatibility("aries", "cancer")
    assert result.overall < 75


def test_compatibility_normalised_key():
    """(a, b) and (b, a) should return same result."""
    ab = calculate_compatibility("cancer", "scorpio")
    ba = calculate_compatibility("scorpio", "cancer")
    assert ab.overall == ba.overall


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

    assert (
        asyncio.run(_resolve_synastry_timezone("Bad/Timezone", None, None))
        == "UTC"
    )


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
