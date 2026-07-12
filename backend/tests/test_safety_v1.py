from datetime import datetime
from pathlib import Path

import pytest

from api.schemas.horoscope import HoroscopeResponse
from api.schemas.synastry import SynastryResult
from api.schemas.tarot import TarotCardDetail
from api.schemas.transits import TransitsResponse
from core.cache import key_horoscope, key_personal_horoscope
from services.astro.fact_context import (
    FactContext,
    MatrixFactContext,
    TarotFactContext,
    validate_generated_text,
    validate_matrix_text,
    validate_tarot_payload,
)
from services.astro.natal import calculate_natal
from services.astro.synastry import calculate_synastry
from services.destiny_matrix.calculator import calculate_matrix
from services.tarot.interpreter import _build_prompt as build_tarot_prompt


def test_fact_context_rejects_false_aspect_and_wrong_house() -> None:
    context = FactContext.from_chart(
        planets={
            "mercury": {"house": 3, "sign": "Pisces"},
            "uranus": {"house": 7, "sign": "Aquarius"},
            "neptune": {"house": 7, "sign": "Aquarius"},
        },
        aspects=[{"p1": "mercury", "p2": "uranus", "aspect": "trine"}],
        birth_time_known=True,
    )
    errors = validate_generated_text(
        "Меркурий в 10 доме. Уран образует соединение с Нептуном.", context
    )
    assert any("wrong house for mercury" in error for error in errors)
    assert any("unknown aspect" in error for error in errors)
    assert "wrong sign for mercury: stated aries, actual pisces" in validate_generated_text(
        "Меркурий в Овне.", context
    )


@pytest.mark.parametrize(
    "text,code",
    [
        ("У вас диабет.", "medical_diagnosis"),
        ("Гарантированно произойдёт свадьба.", "guaranteed_event"),
        ("В детстве вы часто были одни.", "invented_biography"),
        ("В прошлой жизни вы были врачом.", "invented_biography"),
        ("В прошлом вы могли полагаться только на друзей.", "invented_biography"),
        ("Вам предстоит научиться доверять интуиции.", "guaranteed_future_wording"),
        ("Недавнее предательство изменило вас.", "invented_biography"),
        ("Боли в спине станут сильнее.", "medical_diagnosis"),
    ],
)
def test_fact_context_rejects_unsafe_claims(text: str, code: str) -> None:
    assert code in validate_generated_text(text, FactContext())


def test_cusp_validator_rejects_planet_claim_but_allows_cusp_theme() -> None:
    context = FactContext(birth_time_known=True)
    assert "unsupported cusp claim" in validate_generated_text(
        "Меркурий находится на куспиде.", context
    )
    assert "unsupported cusp claim" not in validate_generated_text(
        "Знак на куспиде задаёт символическую тему этой сферы.", context
    )


def test_unknown_birth_time_has_no_angles_houses_or_planet_houses() -> None:
    chart = calculate_natal(
        name="date-only",
        birth_dt=datetime(2000, 2, 20, 14, 30),
        lat=55.7558,
        lng=37.6173,
        tz_str="Europe/Moscow",
        birth_time_known=False,
    )
    assert chart.ascendant_sign is None
    assert chart.mc_sign is None
    assert chart.houses == []
    assert all(
        getattr(chart, planet).house is None
        for planet in (
            "sun", "moon", "mercury", "venus", "mars",
            "jupiter", "saturn", "uranus", "neptune", "pluto",
        )
    )
    errors = validate_generated_text(
        "Асцендент в Раке, Меркурий в 10 доме.",
        FactContext(birth_time_known=False),
    )
    assert len(errors) == 2


def test_geocult_golden_2000_02_20_moscow() -> None:
    """Saved Placidus reference, tolerance mandated by the comparison plan."""
    chart = calculate_natal(
        name="golden",
        birth_dt=datetime(2000, 2, 20, 14, 30),
        lat=55.7558,
        lng=37.6173,
        tz_str="Europe/Moscow",
        birth_time_known=True,
    )
    expected_planets = {
        "sun": 331.1316539,
        "moon": 161.6031127,
        "mercury": 347.0842686,
        "venus": 302.8165456,
        "mars": 6.4131346,
        "jupiter": 30.9389416,
        "saturn": 41.6876585,
        "uranus": 317.6177348,
        "neptune": 305.0456457,
        "pluto": 252.7374170,
    }
    expected_houses = {
        1: 120.1862761, 2: 134.5335141, 3: 153.0943465, 4: 179.8216659,
        5: 219.8320996, 6: 266.4545719, 7: 300.1862761, 8: 314.5335141,
        9: 333.0943465, 10: 359.8216659, 11: 39.8320996, 12: 86.4545719,
    }
    for planet, expected in expected_planets.items():
        assert getattr(chart, planet).degree == pytest.approx(expected, abs=0.001)
    for house in chart.houses:
        assert house["degree"] == pytest.approx(expected_houses[house["number"]], abs=0.001)


def test_removed_contract_fields_stay_removed() -> None:
    horoscope_fields = HoroscopeResponse.model_fields
    transit_fields = TransitsResponse.model_fields
    synastry_fields = SynastryResult.model_fields
    tarot_fields = TarotCardDetail.model_fields
    assert "energy" not in horoscope_fields
    assert "energy" not in transit_fields
    assert "scores" not in synastry_fields
    assert "position_meaning_ru" not in tarot_fields


def test_generic_and_personal_horoscope_cache_keys_do_not_cross_users() -> None:
    generic_a = key_horoscope("pisces", "2026-07-12", "today")
    generic_b = key_horoscope("pisces", "2026-07-12", "today")
    personal_a = key_personal_horoscope(777777777, "2026-07-12", "today")
    personal_b = key_personal_horoscope(888888888, "2026-07-12", "today")
    assert generic_a == generic_b
    assert personal_a != personal_b
    assert generic_a not in (personal_a, personal_b)


def test_reference_synastry_has_only_classic_planets_and_expected_aspects() -> None:
    def subject(name: str, birth_dt: datetime) -> dict:
        return {
            "name": name,
            "birth_dt": birth_dt,
            "lat": 55.7558,
            "lng": 37.6173,
            "tz_str": "Europe/Moscow",
            "birth_time_known": True,
        }

    result = calculate_synastry(
        subject("Astro QA", datetime(2000, 2, 20, 14, 30)),
        subject("Partner", datetime(1995, 8, 15, 9, 30)),
    )
    triples = {
        (item["p1_name"].lower(), item["p2_name"].lower(), item["aspect"])
        for item in result["aspects"]
    }
    assert ("venus", "pluto", "sextile") in triples
    assert ("pluto", "moon", "trine") in triples
    # GeoCult confirms this aspect at 2.59° for the historical +04:00 offset.
    assert ("saturn", "mercury", "trine") in triples
    assert all(
        body in {
            "sun", "moon", "mercury", "venus", "mars",
            "jupiter", "saturn", "uranus", "neptune", "pluto",
        }
        for p1, p2, _ in triples
        for body in (p1, p2)
    )


def test_tarot_prompt_anchors_reversed_meaning() -> None:
    prompt = build_tarot_prompt(
        "three_card",
        [
            {
                "card_id": index,
                "name_ru": name,
                "reversed": index == 1,
                "meaning_ru": "задержка и внутреннее сомнение" if index == 1 else "ясность",
                "keywords_ru": ["символ"],
            }
            for index, name in enumerate(("Мир", "Солнце", "Звезда"), start=1)
        ],
    )
    assert "Мир (перевёрнута)" in prompt
    assert "задержка и внутреннее сомнение" in prompt
    assert "не противоречь указанному значению" in prompt


def test_tarot_structured_output_must_echo_saved_cards() -> None:
    cards = [
        {"card_id": 10, "reversed": False},
        {"card_id": 20, "reversed": True},
        {"card_id": 30, "reversed": False},
    ]
    payload = {
        "positions": [
            {"n": 1, "card_id": 10, "reversed": False, "narrative": "Тема."},
            {"n": 2, "card_id": 99, "reversed": False, "narrative": "Тема."},
            {"n": 3, "card_id": 30, "reversed": False, "narrative": "Тема."},
        ],
        "summary": "Итог.",
    }
    errors = validate_tarot_payload(payload, TarotFactContext.from_cards(cards))
    assert "wrong tarot card at position 2" in errors
    assert "wrong tarot orientation at position 2" in errors


def test_matrix_program_is_canonical_and_ray_stays_separate() -> None:
    positions = calculate_matrix(datetime(2000, 2, 20).date())
    assert positions["karmic_program"] == {"key": "9-15-6", "arcana": [9, 15, 6]}
    assert positions["channels"]["karmic_tail"] == [15, 9, 12]
    context = MatrixFactContext.from_positions(positions)
    assert "wrong karmic program" in " ".join(
        validate_matrix_text("Кармическая программа 15-9-12.", context)
    )


def test_tarot_markdown_parser_does_not_leak_service_headings() -> None:
    from scripts.update_tarot_meanings import compose_upright, parse_cards

    source = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "tarot"
        / "tarot_full.md"
    ).read_text(encoding="utf-8")
    cards = parse_cards(source)
    for name in ("The World", "King of Wands", "King of Cups", "King of Swords"):
        text = compose_upright(cards[name])
        assert "# ЧАСТЬ" not in text
