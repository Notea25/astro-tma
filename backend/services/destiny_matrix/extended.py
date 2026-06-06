"""Extended calculations for V3 interpretation prompts.

Everything in here computes deterministic values that are NOT already in
the diagram-facing `positions` payload, so the frontend octagram stays
untouched. The V3 LLM prompts pull from this module to get:

  * `calculate_purposes_v3()` — the 8 canonical Ладини purposes as
    `(left, right, total)` triples. The totals already live in
    `positions["purposes"]` and `positions["purposes_full"]`; this
    function rebuilds the same numbers with their composition factors
    so prompts can say «арканы A+B=total».

  * `calculate_year_energy()` — current and upcoming year arcanas based
    on birth date and a reference date (defaults to today). Refreshed
    by a cron job on the user's birthday.

  * `karmic_program_key()` — `"3-22-19"` style string formed from the
    bottom-axis triple, used to look up the canonical karmic program
    name in the `karmic_programs` table.

Validated against the book example 01.05.1969 — 8/8 purposes match,
year-energy matches the standard numerological formula.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from services.destiny_matrix.calculator import reduce

# ── 8 предназначений ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PurposeTriple:
    """One of the 8 Ладини purposes. The `key` triple is
    `(left_component, right_component, total)` — V3 prompts cite the
    composition: «аркан 5 + аркан 13 = 18 (Магия)»."""
    name: str
    key: tuple[int, int, int]

    @property
    def total(self) -> int:
        return self.key[2]


_PURPOSE_NAMES: dict[str, str] = {
    "celestial_personal":  "Небесное личное (духовная жизнь)",
    "earthly_personal":    "Земное личное (материя)",
    "wholeness_personal":  "Целостное личное",
    "father_lineage":      "По роду Отца",
    "mother_lineage":      "По роду Матери",
    "wholeness_lineage":   "Примирение родов (соц. реализация)",
    "personal_divine":     "Личное Божественное",
    "divine_mission":      "Божественная миссия для людей",
}


def calculate_purposes_v3(positions: dict[str, Any]) -> dict[str, PurposeTriple]:
    """8 purposes with their composition triples. Reads from our existing
    `positions` payload (`personality`, `ancestral_square`, …) — same
    math as the calculator's `purpose_*` fields, just emitted in the
    `(left, right, total)` shape V3 prompts expect.

    Validated against Ладини book example 01.05.1969: all 8 triples
    match the published table."""
    pers = positions["personality"]
    sq = positions["ancestral_square"]
    M, B, D, Y = pers["month"], pers["bottom"], pers["day"], pers["year"]
    TL = sq["top_left"]; TR = sq["top_right"]
    BR = sq["bottom_right"]; BL = sq["bottom_left"]

    p1 = reduce(M + B)               # celestial_personal
    p2 = reduce(D + Y)               # earthly_personal
    p3 = reduce(p1 + p2)             # wholeness_personal
    p4 = reduce(TL + BR)             # father_lineage
    p5 = reduce(TR + BL)             # mother_lineage
    p6 = reduce(p4 + p5)             # wholeness_lineage
    p7 = reduce(p3 + p6)             # personal_divine
    p8 = reduce(p6 + p7)             # divine_mission

    return {
        "celestial_personal": PurposeTriple(_PURPOSE_NAMES["celestial_personal"], (M, B, p1)),
        "earthly_personal":   PurposeTriple(_PURPOSE_NAMES["earthly_personal"],   (D, Y, p2)),
        "wholeness_personal": PurposeTriple(_PURPOSE_NAMES["wholeness_personal"], (p1, p2, p3)),
        "father_lineage":     PurposeTriple(_PURPOSE_NAMES["father_lineage"],     (TL, BR, p4)),
        "mother_lineage":     PurposeTriple(_PURPOSE_NAMES["mother_lineage"],     (TR, BL, p5)),
        "wholeness_lineage":  PurposeTriple(_PURPOSE_NAMES["wholeness_lineage"],  (p4, p5, p6)),
        "personal_divine":    PurposeTriple(_PURPOSE_NAMES["personal_divine"],    (p3, p6, p7)),
        "divine_mission":     PurposeTriple(_PURPOSE_NAMES["divine_mission"],     (p6, p7, p8)),
    }


# ── Энергия года ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class YearEnergy:
    """Current and upcoming year arcanas.

    `current` is the arcana the reader is in *right now* — until their
    next birthday. `upcoming` is what kicks in after that birthday. The
    cron job refreshes the cached interpretation when the user's BD
    rolls around."""
    current: int
    upcoming: int


def _sum_digits(n: int) -> int:
    return sum(int(c) for c in str(abs(n)))


def calculate_year_energy(birth: date, on_date: date | None = None) -> YearEnergy:
    """Year energy by the standard numerology formula:

        E(year) = reduce(birth_day + birth_month + reduce(year_digits))

    `current` is computed for whichever calendar year contains the
    reader's most recent birthday — so a January reader has January's
    energy from Jan to Dec, while a June reader doesn't switch until
    June. `upcoming` is the same formula for the *next* such year.
    """
    if on_date is None:
        on_date = date.today()
    had_birthday = (on_date.month, on_date.day) >= (birth.month, birth.day)
    current_year = on_date.year if had_birthday else on_date.year - 1
    current = reduce(
        reduce(birth.day) + reduce(birth.month) + reduce(_sum_digits(current_year))
    )
    upcoming = reduce(
        reduce(birth.day) + reduce(birth.month) + reduce(_sum_digits(current_year + 1))
    )
    return YearEnergy(current=current, upcoming=upcoming)


# ── Кармическая программа ───────────────────────────────────────────────────


def karmic_program_key(positions: dict[str, Any]) -> str:
    """`"bottom_2-bottom_1-bottom"` triple for `karmic_programs` lookup.

    Canonical reading order is from the centre of the octagram outwards:
    bottom_2 (mid, partner-entry) → bottom_1 (near_corner, self-realisation)
    → bottom (B angle, main lesson from past life). Matches the format used
    in ``content/karmic_programs_canonical.json``.

    bottom_1 = near_corner of B = `channels.karmic_tail[0]` in our
    payload. bottom_2 = mid of B = `specials.love`."""
    bottom = positions["personality"]["bottom"]
    bottom_1 = positions["channels"]["karmic_tail"][0]
    bottom_2 = positions["specials"]["love"]
    return f"{bottom_2}-{bottom_1}-{bottom}"
