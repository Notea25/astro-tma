"""Repeated contract tests for LLM fact validation and safe fallbacks.

These tests deliberately avoid a real provider: the first answer is invalid and
the second one is corrected.  Running every domain three times protects the
retry/fallback contract without spending tokens or depending on network state.
"""

from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from services.astro import llm_interpreter, synastry_interpreter, transit_interpreter
from services.destiny_matrix import interpreter as matrix_interpreter
from services.destiny_matrix.calculator import calculate_matrix
from services.tarot import interpreter as tarot_interpreter


class _QueuedMessages:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("unexpected extra LLM request")
        return self.responses.pop(0)


def _text_message(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
    )


def _tool_message(payload: dict[str, str]) -> SimpleNamespace:
    return SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use",
                name="publish_reading",
                input=payload,
            )
        ]
    )


def _long_safe_natal() -> str:
    body = " ".join(f"наблюдение{i}" for i in range(260))
    return f"**Основа личности**\n{body}."


def _tarot_cards() -> list[dict[str, Any]]:
    return [
        {
            "card_id": index,
            "name_ru": name,
            "reversed": index == 2,
            "meaning_ru": "пауза и переоценка" if index == 2 else "ясность выбора",
            "keywords_ru": ["размышление", "выбор"],
        }
        for index, name in enumerate(("Мир", "Солнце", "Звезда"), start=1)
    ]


def _tarot_payload(cards: list[dict[str, Any]], *, wrong: bool) -> dict[str, Any]:
    positions = [
        {
            "n": index,
            "card_id": 999 if wrong and index == 2 else card["card_id"],
            "reversed": bool(card["reversed"]),
            "narrative": "Карта предлагает спокойно сопоставить образ с ситуацией.",
        }
        for index, card in enumerate(cards, start=1)
    ]
    return {
        "positions": positions,
        "summary": "Расклад оставляет пространство для самостоятельного размышления.",
    }


@pytest.mark.asyncio
async def test_three_natal_generations_retry_fact_error(monkeypatch: pytest.MonkeyPatch) -> None:
    safe = _long_safe_natal()
    invalid = safe + " У вас диабет."
    messages = _QueuedMessages(
        [response for _ in range(3) for response in (_text_message(invalid), _text_message(safe))]
    )
    monkeypatch.setattr(
        llm_interpreter,
        "create_llm_client",
        lambda _api_key: SimpleNamespace(messages=messages),
    )

    for _ in range(3):
        result = await llm_interpreter.generate_natal_reading(
            sun_sign="Рыбы",
            moon_sign="Дева",
            ascendant_sign=None,
            planets={
                "sun": {"sign": "Pisces", "sign_ru": "Рыбы", "house": None},
                "moon": {"sign": "Virgo", "sign_ru": "Дева", "house": None},
            },
            aspects=[],
            api_key="test-key",
        )
        assert result == safe
    assert len(messages.calls) == 6
    assert all(
        "medical_diagnosis" in call["messages"][0]["content"]
        for call in messages.calls[1::2]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "subject"),
    [
        (transit_interpreter, "Тема транзита"),
        (synastry_interpreter, "Аспект совместимости"),
    ],
)
async def test_three_aspect_batches_retry_fact_error(
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
    subject: str,
) -> None:
    invalid = json.dumps(["У вас диабет."], ensure_ascii=False)
    safe = json.dumps(
        ["Ситуация допускает несколько прочтений и оставляет место для спокойного выбора."],
        ensure_ascii=False,
    )
    messages = _QueuedMessages(
        [response for _ in range(3) for response in (_text_message(invalid), _text_message(safe))]
    )
    import services.llm_client as llm_client

    monkeypatch.setattr(
        llm_client,
        "create_llm_client",
        lambda _api_key: SimpleNamespace(messages=messages),
    )
    triple = ("venus", "mars", "trine")
    for _ in range(3):
        result = await module._llm_batch([triple], "test-key")
        assert result[triple].startswith("Ситуация допускает")
        assert subject not in result[triple]
    assert len(messages.calls) == 6


@pytest.mark.asyncio
async def test_three_tarot_generations_retry_card_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    cards = _tarot_cards()
    messages = _QueuedMessages(
        [
            response
            for _ in range(3)
            for response in (
                _text_message(json.dumps(_tarot_payload(cards, wrong=True), ensure_ascii=False)),
                _text_message(json.dumps(_tarot_payload(cards, wrong=False), ensure_ascii=False)),
            )
        ]
    )
    monkeypatch.setattr(
        tarot_interpreter,
        "create_llm_client",
        lambda _api_key: SimpleNamespace(messages=messages),
    )

    for _ in range(3):
        result = await tarot_interpreter.generate_spread_interpretation(
            "three_card", cards, "test-key"
        )
        assert len(result["positions"]) == 3
        assert all(position["narrative"] for position in result["positions"])
        assert result["summary"].startswith("Расклад оставляет")
    assert len(messages.calls) == 6


@pytest.mark.asyncio
async def test_three_matrix_generations_retry_unsafe_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    positions = calculate_matrix(date(2000, 2, 20))
    invalid = {key: "В прошлой жизни ты был врачом." for key in matrix_interpreter.SECTION_KEYS}
    safe = {
        key: "Этот символ предлагает вопрос для самонаблюдения и допускает разные прочтения."
        for key in matrix_interpreter.SECTION_KEYS
    }
    messages = _QueuedMessages(
        [response for _ in range(3) for response in (_tool_message(invalid), _tool_message(safe))]
    )
    monkeypatch.setattr(
        matrix_interpreter,
        "create_llm_client",
        lambda _api_key: SimpleNamespace(messages=messages),
    )

    for _ in range(3):
        sections, model = await matrix_interpreter.generate_interpretation(
            positions, "Astro QA", "test-key", "male"
        )
        assert model == matrix_interpreter._MODEL
        assert set(sections) == set(matrix_interpreter.SECTION_KEYS)
        assert all("прошлой жизни" not in text.lower() for text in sections.values())
    assert len(messages.calls) == 6


@pytest.mark.asyncio
async def test_all_domains_use_safe_fallback_after_second_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unsafe_text = _long_safe_natal() + " У вас диабет."

    natal_messages = _QueuedMessages([_text_message(unsafe_text), _text_message(unsafe_text)])
    monkeypatch.setattr(
        llm_interpreter,
        "create_llm_client",
        lambda _api_key: SimpleNamespace(messages=natal_messages),
    )
    natal = await llm_interpreter.generate_natal_reading(
        "Рыбы",
        "Дева",
        None,
        {"sun": {"sign": "Pisces", "house": None}},
        [],
        "test-key",
    )
    assert "медицинский" in natal and "диабет" not in natal

    import services.llm_client as llm_client

    for module, label in (
        (transit_interpreter, "Тема транзита"),
        (synastry_interpreter, "Аспект совместимости"),
    ):
        messages = _QueuedMessages(
            [_text_message(json.dumps([unsafe_text], ensure_ascii=False)) for _ in range(2)]
        )
        monkeypatch.setattr(
            llm_client,
            "create_llm_client",
            lambda _api_key, queued=messages: SimpleNamespace(messages=queued),
        )
        triple = ("venus", "mars", "trine")
        result = await module._llm_batch([triple], "test-key")
        assert result[triple].startswith(label)
        assert "не медицинский" in result[triple]

    cards = _tarot_cards()
    wrong_tarot = json.dumps(_tarot_payload(cards, wrong=True), ensure_ascii=False)
    tarot_messages = _QueuedMessages([_text_message(wrong_tarot), _text_message(wrong_tarot)])
    monkeypatch.setattr(
        tarot_interpreter,
        "create_llm_client",
        lambda _api_key: SimpleNamespace(messages=tarot_messages),
    )
    tarot = await tarot_interpreter.generate_spread_interpretation(
        "three_card", cards, "test-key"
    )
    assert "развлекательная" in tarot["summary"]

    positions = calculate_matrix(date(2000, 2, 20))
    unsafe_sections = {
        key: "В прошлой жизни ты был врачом." for key in matrix_interpreter.SECTION_KEYS
    }
    matrix_messages = _QueuedMessages(
        [_tool_message(unsafe_sections), _tool_message(unsafe_sections)]
    )
    monkeypatch.setattr(
        matrix_interpreter,
        "create_llm_client",
        lambda _api_key: SimpleNamespace(messages=matrix_messages),
    )
    matrix, _model = await matrix_interpreter.generate_interpretation(
        positions, "Astro QA", "test-key", "male"
    )
    assert all("не медицинский" in text for text in matrix.values())
