from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services.astro import natal_report


def _chart() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    signs = (
        ("Pisces", "Рыбы"),
        ("Virgo", "Дева"),
        ("Pisces", "Рыбы"),
        ("Aquarius", "Водолей"),
        ("Aries", "Овен"),
        ("Taurus", "Телец"),
        ("Taurus", "Телец"),
        ("Aquarius", "Водолей"),
        ("Aquarius", "Водолей"),
        ("Sagittarius", "Стрелец"),
    )
    planets = {
        key: {
            "sign": sign,
            "sign_ru": sign_ru,
            "sign_degree": float(index + 1),
            "degree": float(index * 30 + 1),
            "house": index % 12 + 1,
            "retrograde": False,
        }
        for index, (key, (sign, sign_ru)) in enumerate(
            zip(natal_report._PLANET_ORDER, signs, strict=True)
        )
    }
    house_signs = (
        ("Leo", "Лев"),
        ("Virgo", "Дева"),
        ("Libra", "Весы"),
        ("Scorpio", "Скорпион"),
        ("Sagittarius", "Стрелец"),
        ("Capricorn", "Козерог"),
        ("Aquarius", "Водолей"),
        ("Pisces", "Рыбы"),
        ("Aries", "Овен"),
        ("Taurus", "Телец"),
        ("Gemini", "Близнецы"),
        ("Cancer", "Рак"),
    )
    houses = [
        {
            "number": index,
            "sign": sign,
            "sign_ru": sign_ru,
            "degree": float((index - 1) * 30 + 1),
        }
        for index, (sign, sign_ru) in enumerate(house_signs, start=1)
    ]
    aspect_specs = (
        ("sun", "jupiter", "sextile"),
        ("moon", "mercury", "opposition"),
        ("moon", "saturn", "trine"),
        ("moon", "pluto", "square"),
        ("mercury", "saturn", "sextile"),
        ("mercury", "pluto", "square"),
        ("venus", "mars", "sextile"),
        ("venus", "jupiter", "square"),
        ("venus", "neptune", "conjunction"),
        ("mars", "neptune", "sextile"),
        ("jupiter", "neptune", "square"),
        ("saturn", "uranus", "square"),
        ("uranus", "pluto", "sextile"),
    )
    aspects = [
        {"p1": p1, "p2": p2, "aspect": kind, "orb": index / 10 + 0.1}
        for index, (p1, p2, kind) in enumerate(aspect_specs, start=1)
    ]
    return planets, houses, aspects


def _narrative(group: str, item_id: str) -> str:
    word_counts = {
        "core": {
            "foundation": 100,
            "dominants": 75,
            "lunar_nodes": 65,
            "synthesis": 130,
            "recommendations": 75,
        },
        "planets": 65,
        "houses": 55,
        "aspects": 65,
    }
    if group == "core":
        count = word_counts[group].get(item_id, 80)  # type: ignore[union-attr]
    else:
        count = int(word_counts[group])
    return f"Сюжет{item_id} " + " ".join("наблюдение" for _ in range(count - 1)) + "."


def _response(group: str, facts: list[Any]) -> Any:
    return natal_report._NarrativeResponse(
        items=[
            natal_report._NarrativeItem(
                id=fact.id,
                narrative=_narrative(group, fact.id),
            )
            for fact in facts
        ]
    )


@pytest.mark.asyncio
async def test_full_report_uses_four_groups_and_covers_complete_chart(monkeypatch):
    planets, houses, aspects = _chart()
    calls: list[str] = []
    all_started = asyncio.Event()

    async def fake_call(_client, group, facts, _gender, repair_errors=None):
        assert repair_errors is None
        calls.append(group)
        if len(calls) == 4:
            all_started.set()
        await asyncio.wait_for(all_started.wait(), timeout=0.5)
        return _response(group, facts)

    monkeypatch.setattr(natal_report, "_call_group", fake_call)
    generated = await natal_report.generate_natal_report(
        sun_sign="Рыбы",
        moon_sign="Дева",
        ascendant_sign="Лев",
        planets=planets,
        houses=houses,
        aspects=aspects,
        api_key="test-key",
        gender="male",
    )

    payload = natal_report.NatalReportPayload.model_validate(generated.payload)
    assert set(calls) == {"core", "planets", "houses", "aspects"}
    assert len(calls) == 4
    assert len(payload.planets) == 10
    assert len(payload.houses) == 12
    assert len(payload.aspects) == 13
    assert len({item.id for item in payload.planets}) == 10
    assert len({item.id for item in payload.houses}) == 12
    assert len({item.id for item in payload.aspects}) == 13
    assert generated.status == "ready"
    assert generated.input_hash
    assert "**Солнце в Рыбах, I дом**" in generated.text
    descriptions = natal_report.report_descriptions(payload)
    assert len(descriptions["planets"]) == 10
    assert len(descriptions["houses"]) == 12
    assert len(descriptions["aspects"]) == 13


@pytest.mark.asyncio
async def test_date_only_uses_three_groups_and_never_mentions_houses(monkeypatch):
    planets, houses, aspects = _chart()
    calls: list[str] = []

    async def fake_call(_client, group, facts, _gender, repair_errors=None):
        calls.append(group)
        return _response(group, facts)

    monkeypatch.setattr(natal_report, "_call_group", fake_call)
    generated = await natal_report.generate_natal_report(
        sun_sign="Рыбы",
        moon_sign="Дева",
        ascendant_sign=None,
        planets={key: {**value, "house": None} for key, value in planets.items()},
        houses=houses,
        aspects=aspects,
        api_key="test-key",
    )

    payload = natal_report.NatalReportPayload.model_validate(generated.payload)
    assert set(calls) == {"core", "planets", "aspects"}
    assert payload.chart_mode == "date_only"
    assert payload.houses == []
    assert "асцендент" not in generated.text.lower()
    assert " дом" not in generated.text.lower()


@pytest.mark.asyncio
async def test_only_missing_item_is_repaired(monkeypatch):
    planets, houses, aspects = _chart()
    planet_requests: list[list[str]] = []

    async def fake_call(_client, group, facts, _gender, repair_errors=None):
        if group != "planets":
            return _response(group, facts)
        planet_requests.append([fact.id for fact in facts])
        if len(planet_requests) == 1:
            return natal_report._NarrativeResponse(
                items=[
                    natal_report._NarrativeItem(
                        id=fact.id,
                        narrative=_narrative(group, fact.id),
                    )
                    for fact in facts
                    if fact.id != "moon"
                ]
            )
        assert repair_errors == {"moon": ["missing item"]}
        return _response(group, facts)

    monkeypatch.setattr(natal_report, "_call_group", fake_call)
    generated = await natal_report.generate_natal_report(
        sun_sign="Рыбы",
        moon_sign="Дева",
        ascendant_sign="Лев",
        planets=planets,
        houses=houses,
        aspects=aspects,
        api_key="test-key",
    )

    assert planet_requests[0] == list(natal_report._PLANET_ORDER)
    assert planet_requests[1] == ["moon"]
    assert generated.status == "ready"


@pytest.mark.asyncio
async def test_second_invalid_item_becomes_local_ready_fallback(monkeypatch):
    planets, houses, aspects = _chart()

    async def fake_call(_client, group, facts, _gender, repair_errors=None):
        if group == "aspects":
            return natal_report._NarrativeResponse(items=[])
        return _response(group, facts)

    monkeypatch.setattr(natal_report, "_call_group", fake_call)
    generated = await natal_report.generate_natal_report(
        sun_sign="Рыбы",
        moon_sign="Дева",
        ascendant_sign="Лев",
        planets=planets,
        houses=houses,
        aspects=aspects,
        api_key="test-key",
    )

    payload = natal_report.NatalReportPayload.model_validate(generated.payload)
    assert generated.status == "ready_with_fallback"
    assert payload.used_fallback is True
    assert all(item.fallback for item in payload.aspects)
    assert all(not item.fallback for item in payload.planets)
    assert "не медицинский" in generated.text


def test_report_hash_changes_with_birth_facts_and_not_provider():
    planets, houses, aspects = _chart()
    kwargs = dict(
        sun_sign="Рыбы",
        moon_sign="Дева",
        ascendant_sign="Лев",
        planets=planets,
        houses=houses,
        aspects=aspects,
        gender="male",
    )
    original = natal_report.build_natal_report_input_hash(**kwargs)
    assert original == natal_report.build_natal_report_input_hash(**kwargs)
    changed = {**planets, "moon": {**planets["moon"], "sign_degree": 3.5}}
    assert original != natal_report.build_natal_report_input_hash(
        **{**kwargs, "planets": changed}
    )


def test_validator_rejects_repeated_fact_and_medical_claim():
    context = natal_report.AstroFactContext(birth_time_known=True)
    text = "Солнце в Рыбах показывает характер. У вас диабет. " + " ".join(
        "наблюдение" for _ in range(60)
    ) + "."
    errors = natal_report._quality_errors("planets", "sun", text, context)
    assert "narrative repeats or invents an astrology fact" in errors
    assert "medical_diagnosis" in errors


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_error",
    [TimeoutError("timeout"), RuntimeError("429 rate limit"), RuntimeError("500 upstream")],
)
async def test_provider_errors_fallback_only_failed_group(monkeypatch, provider_error):
    planets, houses, aspects = _chart()

    async def fake_call(_client, group, facts, _gender, repair_errors=None):
        if group == "aspects":
            raise provider_error
        return _response(group, facts)

    monkeypatch.setattr(natal_report, "_call_group", fake_call)
    generated = await natal_report.generate_natal_report(
        sun_sign="Рыбы",
        moon_sign="Дева",
        ascendant_sign="Лев",
        planets=planets,
        houses=houses,
        aspects=aspects,
        api_key="test-key",
    )

    payload = natal_report.NatalReportPayload.model_validate(generated.payload)
    assert generated.status == "ready_with_fallback"
    assert all(item.fallback for item in payload.aspects)
    assert all(not item.fallback for item in payload.planets + payload.houses)


def test_malformed_json_response_is_rejected():
    message = type("Message", (), {"content": [type("Block", (), {"text": "{bad"})()]})()
    with pytest.raises(ValueError):
        natal_report._extract_response(message, "submit_core")
