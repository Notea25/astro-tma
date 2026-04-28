"""
Zodiac compatibility engine.
Two-level: fast sign-level matrix + deep natal synastry (premium).
"""

from dataclasses import dataclass

from core.logging import get_logger

log = get_logger(__name__)


@dataclass
class CompatibilityResult:
    sign_a: str
    sign_b: str
    overall: int          # 0–100
    love: int
    communication: int
    trust: int
    passion: int
    tier: str             # "high" | "medium" | "low"
    description_ru: str
    strengths_ru: list[str]
    challenges_ru: list[str]


# ── Element & modality tables ──────────────────────────────────────────────────
_ELEMENT: dict[str, str] = {
    "aries": "fire", "leo": "fire", "sagittarius": "fire",
    "taurus": "earth", "virgo": "earth", "capricorn": "earth",
    "gemini": "air", "libra": "air", "aquarius": "air",
    "cancer": "water", "scorpio": "water", "pisces": "water",
}
_MODALITY: dict[str, str] = {
    "aries": "cardinal", "cancer": "cardinal", "libra": "cardinal", "capricorn": "cardinal",
    "taurus": "fixed", "leo": "fixed", "scorpio": "fixed", "aquarius": "fixed",
    "gemini": "mutable", "virgo": "mutable", "sagittarius": "mutable", "pisces": "mutable",
}
_ELEMENT_COMPAT: dict[tuple[str, str], int] = {
    ("fire", "fire"): 85, ("earth", "earth"): 82, ("air", "air"): 80, ("water", "water"): 82,
    ("fire", "air"): 78, ("air", "fire"): 78,
    ("earth", "water"): 75, ("water", "earth"): 75,
    ("fire", "earth"): 52, ("earth", "fire"): 52,
    ("fire", "water"): 45, ("water", "fire"): 45,
    ("air", "water"): 55, ("water", "air"): 55,
    ("air", "earth"): 50, ("earth", "air"): 50,
}

# Precomputed sign-to-sign scores for the 12×12 matrix
_SIGN_SCORES: dict[tuple[str, str], dict[str, int]] = {
    # Full matrix omitted for brevity — computed algorithmically below
    # Override specific pairs where astrology tradition says something specific
    ("aries", "leo"):       {"love": 90, "comm": 82, "trust": 75, "passion": 92},
    ("aries", "sagittarius"):{"love": 88, "comm": 85, "trust": 80, "passion": 88},
    ("taurus", "virgo"):    {"love": 85, "comm": 82, "trust": 90, "passion": 72},
    ("taurus", "capricorn"):{"love": 84, "comm": 78, "trust": 92, "passion": 70},
    ("gemini", "libra"):    {"love": 87, "comm": 95, "trust": 72, "passion": 78},
    ("gemini", "aquarius"): {"love": 82, "comm": 90, "trust": 75, "passion": 75},
    ("cancer", "scorpio"):  {"love": 90, "comm": 78, "trust": 88, "passion": 85},
    ("cancer", "pisces"):   {"love": 88, "comm": 80, "trust": 85, "passion": 82},
    ("leo", "sagittarius"): {"love": 87, "comm": 85, "trust": 78, "passion": 88},
    ("virgo", "capricorn"): {"love": 84, "comm": 80, "trust": 90, "passion": 68},
    ("libra", "aquarius"):  {"love": 85, "comm": 88, "trust": 75, "passion": 78},
    ("scorpio", "pisces"):  {"love": 90, "comm": 80, "trust": 85, "passion": 88},
    # Opposition pairs (challenging but magnetic)
    ("aries", "libra"):     {"love": 72, "comm": 70, "trust": 65, "passion": 85},
    ("taurus", "scorpio"):  {"love": 75, "comm": 60, "trust": 68, "passion": 90},
    ("gemini", "sagittarius"):{"love": 70, "comm": 75, "trust": 62, "passion": 80},
    ("cancer", "capricorn"):{"love": 65, "comm": 58, "trust": 72, "passion": 72},
}

_DESCRIPTIONS: dict[str, str] = {
    "high": "Редкое созвездие! Ваши знаки образуют гармоничный тандем — стихии взаимно усиливают друг друга. Глубокое понимание, общие ценности и взаимное притяжение делают эту связь по-настоящему особенной.",
    "medium": "Интересный союз с большим потенциалом. Разные энергии создают динамику и рост. Потребуется желание слышать друг друга — именно это различие может стать вашей силой.",
    "low": "Непростое сочетание стихий, но не безнадёжное. Напряжение между знаками способно стать источником роста и трансформации. Честность и уважение к различиям — ключи к гармонии.",
}


def _compute_base_scores(sign_a: str, sign_b: str) -> dict[str, int]:
    """Compute scores algorithmically from element/modality when no preset exists."""
    a, b = sign_a.lower(), sign_b.lower()
    elem_a, elem_b = _ELEMENT.get(a, "fire"), _ELEMENT.get(b, "fire")
    mod_a, mod_b = _MODALITY.get(a, "cardinal"), _MODALITY.get(b, "cardinal")

    # Base from element compatibility
    base = _ELEMENT_COMPAT.get((elem_a, elem_b), 60)

    # Modality modifier
    if mod_a == mod_b:
        mod_bonus = -5  # same modality = friction (both want to lead, etc.)
    elif {mod_a, mod_b} in [{"cardinal", "mutable"}, {"fixed", "mutable"}]:
        mod_bonus = 5
    else:
        mod_bonus = 0

    love = min(95, base + mod_bonus)
    comm = min(95, base + mod_bonus - 5 + (10 if elem_a == "air" or elem_b == "air" else 0))
    trust = min(95, base + (5 if elem_a == "earth" or elem_b == "earth" else 0))
    passion = min(95, base + (8 if elem_a == "fire" or elem_b == "fire" else 0))

    return {"love": love, "comm": comm, "trust": trust, "passion": passion}


def calculate_compatibility(sign_a: str, sign_b: str) -> CompatibilityResult:
    """
    Sign-level compatibility. No natal data required — fast, cacheable.
    """
    a, b = sign_a.lower(), sign_b.lower()
    # Normalise key order
    key = (a, b) if (a, b) in _SIGN_SCORES else (b, a) if (b, a) in _SIGN_SCORES else None

    if key:
        s = _SIGN_SCORES[key]
        scores = {"love": s["love"], "comm": s["comm"],
                  "trust": s["trust"], "passion": s["passion"]}
    else:
        scores = _compute_base_scores(a, b)

    overall = round(
        scores["love"] * 0.35
        + scores["comm"] * 0.25
        + scores["trust"] * 0.25
        + scores["passion"] * 0.15
    )

    tier = "high" if overall >= 78 else "medium" if overall >= 60 else "low"

    return CompatibilityResult(
        sign_a=sign_a,
        sign_b=sign_b,
        overall=overall,
        love=scores["love"],
        communication=scores["comm"],
        trust=scores["trust"],
        passion=scores["passion"],
        tier=tier,
        description_ru=_DESCRIPTIONS[tier],
        strengths_ru=_strengths(a, b, tier),
        challenges_ru=_challenges(a, b, tier),
    )


def _strengths(a: str, b: str, tier: str) -> list[str]:
    elem_a, elem_b = _ELEMENT.get(a, "?"), _ELEMENT.get(b, "?")
    base = []
    if elem_a == elem_b:
        base.append("Общая стихия создаёт интуитивное взаимопонимание")
    if tier == "high":
        base += ["Гармоничный баланс энергий", "Схожие жизненные ценности"]
    elif tier == "medium":
        base += ["Взаимодополняющие качества", "Потенциал для роста"]
    else:
        base += ["Магнетическое притяжение противоположностей"]
    return base[:3]


def _challenges(a: str, b: str, tier: str) -> list[str]:
    if tier == "low":
        return ["Разные взгляды на жизнь требуют принятия", "Важно учиться слышать друг друга"]
    if tier == "medium":
        return ["Периодические недопонимания", "Требуется осознанная работа над отношениями"]
    return ["Риск потери индивидуальности в союзе"]
