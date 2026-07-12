"""Semantic guardrails for generated astrology and divination text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_PLANET_STEMS = {
    "sun": r"солнц\w*",
    "moon": r"лун\w*",
    "mercury": r"меркур\w*",
    "venus": r"венер\w*",
    "mars": r"марс\w*",
    "jupiter": r"юпитер\w*|юпитер",
    "saturn": r"сатурн\w*",
    "uranus": r"уран\w*",
    "neptune": r"нептун\w*",
    "pluto": r"плутон\w*",
}
_ASPECT_STEMS = {
    "conjunction": r"соединени\w*",
    "trine": r"трин\w*",
    "square": r"квадрат\w*",
    "opposition": r"оппозиц\w*",
    "sextile": r"секстил\w*",
}
_SIGN_ALIASES = {
    "aries": ("aries", "овен", "овне"),
    "taurus": ("taurus", "телец", "тельце"),
    "gemini": ("gemini", "близнецы", "близнецах"),
    "cancer": ("cancer", "рак", "раке"),
    "leo": ("leo", "лев", "льве"),
    "virgo": ("virgo", "дева", "деве"),
    "libra": ("libra", "весы", "весах"),
    "scorpio": ("scorpio", "скорпион", "скорпионе"),
    "sagittarius": ("sagittarius", "стрелец", "стрельце"),
    "capricorn": ("capricorn", "козерог", "козероге"),
    "aquarius": ("aquarius", "водолей", "водолее"),
    "pisces": ("pisces", "рыбы", "рыбах"),
}
_HOUSE_RE = re.compile(r"\b(1[0-2]|[1-9])(?:-?[а-я]*)?\s+дом\w*", re.IGNORECASE)
_TIME_DEPENDENT_RE = re.compile(
    r"\b(?:асцендент\w*|asc\b|mc\b|середин\w*\s+неб\w*|"
    r"куспид\w*|десцендент\w*|imum\s+coeli)\b",
    re.IGNORECASE,
)

_UNSAFE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "medical_diagnosis",
        re.compile(
            r"\b(?:у вас|вы страдаете|вам грозит|у тебя|ты страдаешь)\s+"
            r"(?:диабет|депресси\w*|рак\w*|болезн\w*|расстройств\w*|диагноз\w*)|"
            r"\b(?:бол(?:и|ь)\s+в\s+(?:спине|животе)|спин\w*\s+(?:даст|может дать)\s+отказ|"
            r"тревог\w*\s+проявля\w*\s+физически)",
            re.IGNORECASE,
        ),
    ),
    (
        "guaranteed_event",
        re.compile(
            r"\b(?:точно|гарантированно|неизбежно|обязательно)\s+"
            r"(?:произойд\w*|случ\w*|получ\w*|встрет\w*|заболе\w*)",
            re.IGNORECASE,
        ),
    ),
    (
        "invented_biography",
        re.compile(
            r"\b(?:в детстве (?:вы|ты)|ваш[аи]? (?:мать|отец|семья) (?:был|была)|"
            r"твоя? (?:мать|отец|семья) (?:был|была)|у (?:вас|тебя) зависимость|"
            r"(?:вы|ты) (?:пережили|недавно пережили) (?:предательство|разрыв|горе)|"
            r"недавн\w* (?:предательств\w*|разрыв\w*)|"
            r"в прошл(?:ой жизни|ом воплощении) (?:вы|ты))\b",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class AstroFactContext:
    """Facts the model is allowed to turn into an interpretation."""

    birth_time_known: bool = True
    planet_signs: dict[str, str] = field(default_factory=dict)
    planet_houses: dict[str, int] = field(default_factory=dict)
    aspects: frozenset[tuple[str, str, str]] = frozenset()

    @classmethod
    def from_chart(
        cls,
        *,
        planets: dict,
        aspects: list[dict],
        birth_time_known: bool,
    ) -> AstroFactContext:
        houses = {
            str(name).lower(): int(data["house"])
            for name, data in planets.items()
            if data.get("house") is not None
        }
        known_aspects: set[tuple[str, str, str]] = set()
        for aspect in aspects:
            p1 = str(aspect.get("p1", "")).lower()
            p2 = str(aspect.get("p2", "")).lower()
            kind = str(aspect.get("aspect", "")).lower()
            first, second = sorted((p1, p2))
            known_aspects.add((first, second, kind))
        return cls(
            birth_time_known=birth_time_known,
            planet_signs={
                str(name).lower(): str(data.get("sign", ""))
                for name, data in planets.items()
                if data.get("sign")
            },
            planet_houses=houses,
            aspects=frozenset(known_aspects),
        )


FactContext = AstroFactContext


@dataclass(frozen=True)
class TarotCardFact:
    position: int
    card_id: int
    reversed: bool


@dataclass(frozen=True)
class TarotFactContext:
    cards: tuple[TarotCardFact, ...]

    @classmethod
    def from_cards(cls, cards: list[dict[str, Any]]) -> TarotFactContext:
        return cls(
            cards=tuple(
                TarotCardFact(
                    position=index,
                    card_id=int(card["card_id"]),
                    reversed=bool(card.get("reversed")),
                )
                for index, card in enumerate(cards, start=1)
            )
        )


@dataclass(frozen=True)
class MatrixFactContext:
    allowed_arcana: frozenset[int]
    karmic_program: tuple[int, int, int]

    @classmethod
    def from_positions(cls, positions: dict[str, Any]) -> MatrixFactContext:
        def _numbers(value: Any) -> list[int]:
            if isinstance(value, bool):
                return []
            if isinstance(value, int):
                return [value] if 1 <= value <= 22 else []
            if isinstance(value, dict):
                return [n for item in value.values() for n in _numbers(item)]
            if isinstance(value, (list, tuple)):
                return [n for item in value for n in _numbers(item)]
            return []

        program = positions.get("karmic_program") or {}
        arcana = tuple(int(n) for n in program.get("arcana", ()))
        if len(arcana) != 3:
            arcana = (
                int(positions["specials"]["love"]),
                int(positions["channels"]["karmic_tail"][0]),
                int(positions["personality"]["bottom"]),
            )
        return cls(frozenset(_numbers(positions)), arcana)


def validate_generated_text(text: str, context: AstroFactContext) -> list[str]:
    """Return stable, human-readable validation errors."""
    errors: list[str] = []
    lowered = text.lower()

    if not context.birth_time_known:
        if _TIME_DEPENDENT_RE.search(text):
            errors.append("time-dependent points are forbidden without birth time")
        if _HOUSE_RE.search(text):
            errors.append("houses are forbidden without birth time")
    else:
        for match in _HOUSE_RE.finditer(text):
            mentioned_house = int(match.group(1))
            sentence_start = max(lowered.rfind(".", 0, match.start()), 0)
            sentence_end = lowered.find(".", match.end())
            sentence = lowered[sentence_start : sentence_end if sentence_end >= 0 else None]
            mentioned_planets = [
                key for key, pattern in _PLANET_STEMS.items() if re.search(pattern, sentence)
            ]
            for planet in mentioned_planets:
                actual = context.planet_houses.get(planet)
                if actual is not None and actual != mentioned_house:
                    errors.append(
                        f"wrong house for {planet}: stated {mentioned_house}, actual {actual}"
                    )

    for sentence in re.split(r"(?<=[.!?])\s+", lowered):
        planets = [key for key, pattern in _PLANET_STEMS.items() if re.search(pattern, sentence)]
        mentioned_signs = [
            key
            for key, aliases in _SIGN_ALIASES.items()
            if any(re.search(rf"\b{re.escape(alias)}\b", sentence) for alias in aliases)
        ]
        if len(planets) == 1 and len(mentioned_signs) == 1:
            actual_sign = context.planet_signs.get(planets[0], "").lower()
            if actual_sign and actual_sign != mentioned_signs[0]:
                errors.append(
                    f"wrong sign for {planets[0]}: stated {mentioned_signs[0]}, actual {actual_sign}"
                )
        aspect_types = [
            kind for kind, pattern in _ASPECT_STEMS.items() if re.search(pattern, sentence)
        ]
        if len(planets) == 2 and len(aspect_types) == 1:
            fact = (*sorted(planets), aspect_types[0])
            if fact not in context.aspects:
                errors.append(
                    f"unknown aspect: {planets[0]} {aspect_types[0]} {planets[1]}"
                )

    for code, pattern in _UNSAFE_PATTERNS:
        if pattern.search(text):
            errors.append(code)

    if re.search(r"\b(?:на|у)\s+куспид\w*\b", text, re.IGNORECASE):
        errors.append("unsupported cusp claim")

    return list(dict.fromkeys(errors))


def validate_tarot_payload(payload: dict[str, Any], context: TarotFactContext) -> list[str]:
    """Validate that structured Tarot output echoes the saved spread exactly."""
    errors: list[str] = []
    positions = payload.get("positions")
    if not isinstance(positions, list) or len(positions) != len(context.cards):
        return ["tarot position count mismatch"]
    expected = {card.position: card for card in context.cards}
    seen: set[int] = set()
    texts: list[str] = [str(payload.get("summary", ""))]
    for item in positions:
        if not isinstance(item, dict):
            errors.append("tarot position must be an object")
            continue
        raw_n = item.get("n")
        raw_card_id = item.get("card_id")
        if raw_n is None or raw_card_id is None:
            errors.append("tarot position/card_id missing")
            continue
        try:
            n = int(raw_n)
            card_id = int(raw_card_id)
        except (TypeError, ValueError):
            errors.append("tarot position/card_id missing")
            continue
        seen.add(n)
        fact = expected.get(n)
        if fact is None:
            errors.append(f"unknown tarot position: {n}")
            continue
        if card_id != fact.card_id:
            errors.append(f"wrong tarot card at position {n}")
        if item.get("reversed") is not fact.reversed:
            errors.append(f"wrong tarot orientation at position {n}")
        texts.append(str(item.get("narrative", "")))
    if seen != set(expected):
        errors.append("tarot positions are incomplete")
    errors.extend(validate_generated_text(" ".join(texts), AstroFactContext()))
    return list(dict.fromkeys(errors))


def validate_matrix_text(text: str, context: MatrixFactContext) -> list[str]:
    """Reject invented arcana/program references and unsafe factual claims."""
    from services.destiny_matrix.arcana_names import ARCANA_NAMES_RU

    errors = validate_generated_text(text, AstroFactContext())
    for match in re.finditer(r"\bаркан\w*\s+(\d{1,2})\b", text, re.I):
        number = int(match.group(1))
        if number not in context.allowed_arcana:
            errors.append(f"unknown matrix arcana: {number}")
    named_arcana = re.compile(
        r"\bаркан\w*\s+(\d{1,2})\s*(?:[—-]\s*([^\n,.;:()]+)|\(([^)]+)\))",
        re.I,
    )
    for match in named_arcana.finditer(text):
        number = int(match.group(1))
        stated_name = (match.group(2) or match.group(3) or "").strip().lower()
        canonical = ARCANA_NAMES_RU.get(number, "").lower()
        if stated_name and canonical and canonical not in stated_name:
            errors.append(f"wrong name for arcana {number}: {stated_name}")
    for match in re.finditer(r"\b(\d{1,2})\s*[-–—]\s*(\d{1,2})\s*[-–—]\s*(\d{1,2})\b", text):
        triple = tuple(int(match.group(i)) for i in range(1, 4))
        if "карми" in text[max(0, match.start() - 80):match.start()].lower() and triple != context.karmic_program:
            errors.append(f"wrong karmic program: {triple}")
    return list(dict.fromkeys(errors))


def safe_natal_fallback(sun_sign: str, moon_sign: str) -> str:
    return (
        "**Основа личности**\n"
        f"Солнце в знаке {sun_sign} символически описывает волевой и творческий "
        f"вектор, а Луна в знаке {moon_sign} — эмоциональные потребности. Эти "
        "положения показывают возможные темы для самонаблюдения, а не заранее "
        "определённые события.\n\n"
        "**Аспекты планет**\n"
        "Аспекты карты можно рассматривать как сочетания внутренних качеств. "
        "Их проявление зависит от решений человека и жизненного контекста.\n\n"
        "**Заключительный синтез**\n"
        "Используйте этот разбор как символическую подсказку для размышления, "
        "не как медицинский, финансовый или фактический прогноз."
    )


def safe_symbolic_fallback(subject: str) -> str:
    return (
        f"{subject} можно рассматривать как символическую тему для "
        "самонаблюдения. Она не доказывает события биографии и не определяет "
        "будущее. Сопоставляйте образ только с собственным опытом и решениями. "
        "Это развлекательная интерпретация, не медицинский, финансовый или "
        "фактический прогноз."
    )
