"""
Destiny Matrix calculator — pure math, no I/O, no LLM.

All formulas come from DESTINY_MATRIX_PRD_ADDENDUM.md. The §3 ones are
cross-confirmed across public Russian calculators; the §4 ones are
hypotheses pending Week 0 validation against gadalkindom.ru. Each
hypothesis is marked with `# TODO: validate vs gadalkindom.ru`.

The matrix is indexed by **English code keys** (`A`, `B`, …, `chakra_sahasrara`)
so we never bake the marketed Russian names into the schema. The display
layer translates them via i18n.
"""

from __future__ import annotations

from datetime import date
from typing import Any

# ── Universal folding rule (§3.1) ─────────────────────────────────────────────


def fold_to_arcana(n: int) -> int:
    """Fold any positive integer into the 1..22 major arcana range.

    Rule (consensus across public sources):
    - If n <= 22: return n.
    - Else: n = sum of digits, repeat until n <= 22.
    - If the result is 0 → return 22 (the convention 0 ≡ XXII The Fool).
    """
    if n < 0:
        n = -n
    while n > 22:
        n = sum(int(d) for d in str(n))
    return n if n > 0 else 22


def _sum_digits(n: int) -> int:
    return sum(int(d) for d in str(abs(n)))


# ── §3.2 Large diamond (rhombus) — 4 corners + center ────────────────────────


def _big_diamond(birth_day: int, birth_month: int, birth_year: int) -> dict[str, int]:
    """A=day, B=month, C=sum-of-year-digits, D=A+B+C, E=A+B+C+D.

    Source: media.halvacard.ru/retrogradnyi-merkurii/matrica-sudby
    + consensus across at least three public calculators.
    """
    a = fold_to_arcana(birth_day)
    b = fold_to_arcana(birth_month)
    c = fold_to_arcana(_sum_digits(birth_year))
    d = fold_to_arcana(a + b + c)
    e = fold_to_arcana(a + b + c + d)
    return {"A": a, "B": b, "C": c, "D": d, "E": e}


# ── §3.3 Small (ancestral) square — F, G, H, I ───────────────────────────────


def _small_square(big: dict[str, int]) -> dict[str, int]:
    """Each ancestral-square corner is the fold of the two adjacent diamond
    corners. Source: §3.3."""
    a, b, c, d = big["A"], big["B"], big["C"], big["D"]
    return {
        "F": fold_to_arcana(a + b),   # top-left
        "G": fold_to_arcana(b + c),   # top-right
        "H": fold_to_arcana(c + d),   # bottom-right
        "I": fold_to_arcana(d + a),   # bottom-left
    }


# ── §3.4 Earth / Sky lines + Purpose triple ──────────────────────────────────


def _purpose_lines(big: dict[str, int], small: dict[str, int]) -> dict[str, int]:
    """line_earth = A+C, line_sky = B+D, plus three life-purpose layers.

    purpose_personal — your own mission up to ~40 y.o.
    purpose_social   — through male/female lineage anchors (~40–60 y.o.)
    purpose_spiritual — combined, the "after-60" arc / overall meaning.
    """
    a, b, c, d = big["A"], big["B"], big["C"], big["D"]
    f, g, h, i = small["F"], small["G"], small["H"], small["I"]

    line_earth = fold_to_arcana(a + c)
    line_sky = fold_to_arcana(b + d)
    purpose_personal = fold_to_arcana(line_earth + line_sky)

    # TODO: validate vs gadalkindom.ru — the male/female anchors are the
    # area with the widest variance between source calculators (§3.4 ⚠️).
    male_lineage_anchor = fold_to_arcana(f + i)     # left side of family square
    female_lineage_anchor = fold_to_arcana(g + h)   # right side

    purpose_social = fold_to_arcana(male_lineage_anchor + female_lineage_anchor)
    purpose_spiritual = fold_to_arcana(purpose_personal + purpose_social)

    return {
        "line_earth": line_earth,
        "line_sky": line_sky,
        "purpose_personal": purpose_personal,
        "male_lineage_anchor": male_lineage_anchor,
        "female_lineage_anchor": female_lineage_anchor,
        "purpose_social": purpose_social,
        "purpose_spiritual": purpose_spiritual,
    }


# ── §4.2 7 chakras × 3 columns (HYPOTHESIS) ──────────────────────────────────


# Chakra keys in the order shown on the diagram (top→bottom)
_CHAKRA_KEYS = (
    "sahasrara",      # 7 (crown)
    "ajna",           # 6 (third eye)
    "vishuddha",      # 5 (throat)
    "anahata",        # 4 (heart — center)
    "manipura",       # 3 (solar plexus)
    "svadhisthana",   # 2 (sacral)
    "muladhara",      # 1 (root)
)


def _chakras(
    big: dict[str, int], small: dict[str, int], purpose: dict[str, int],
) -> dict[str, dict[str, int]]:
    """Returns {chakra_key: {physics, energy, emotion}} for 7 chakras × 3.

    HYPOTHESIS (pending Week 0 validation against gadalkindom.ru):
    the physics column lives on the male (left) family-square axis, the
    energy column on the female (right) axis, the emotion column = fold
    of the two. The crown (sahasrara) reads the diamond axes (A=day,
    B=month) since that's the "head" of the figure.

    The "anahata" (heart) row reads the center E because the heart sits
    at the geometric center of the octagram in every source diagram.
    """
    a, b, c, d, e = big["A"], big["B"], big["C"], big["D"], big["E"]
    f, g, h, i = small["F"], small["G"], small["H"], small["I"]

    # TODO: validate vs gadalkindom.ru — chakras are §4.2 explicit hypothesis.
    rows = {
        "sahasrara":   (a, b, fold_to_arcana(a + b)),
        "ajna":        (i, g, fold_to_arcana(i + g)),
        "vishuddha":   (f, h, fold_to_arcana(f + h)),
        "anahata":     (e, e, e),                                 # heart / center
        "manipura":    (d, fold_to_arcana(d + e), fold_to_arcana(d + e + e)),
        "svadhisthana": (
            fold_to_arcana(a + d),
            fold_to_arcana(b + d),
            fold_to_arcana(a + b + d),
        ),
        "muladhara": (
            fold_to_arcana(a + c),
            fold_to_arcana(b + c),
            fold_to_arcana(a + b + c),
        ),
    }
    out: dict[str, dict[str, int]] = {}
    for key, (physics, energy, emotion) in rows.items():
        out[key] = {
            "physics": physics,
            "energy": energy,
            "emotion": emotion,
        }
    # Totals column (8th row in the diagram) — sum-fold over each column.
    out["totals"] = {
        "physics": fold_to_arcana(sum(row[0] for row in rows.values())),
        "energy": fold_to_arcana(sum(row[1] for row in rows.values())),
        "emotion": fold_to_arcana(sum(row[2] for row in rows.values())),
    }
    return out


# ── §4.3-§4.4 Money / love / health / karma lines (HYPOTHESIS) ───────────────


def _life_lines(big: dict[str, int], small: dict[str, int]) -> dict[str, list[int]]:
    """Each life line = 3 points: start, middle, outcome.

    HYPOTHESIS (pending Week 0 validation). Public sources agree that
    each line lives on a specific axis of the octagram with 3 nodes, but
    the exact formula for each node is private to commercial calculators.
    The convention here:
    - start = the diamond/square corner closest to one end of the axis
    - middle = fold of the two endpoints
    - outcome = the corner at the far end

    The "money" line sits on the vertical (sky) axis, anchored on
    Svadhisthana (2nd chakra). The "love" line sits on the relationship
    diagonal F↔H. Karma rides the personal axis, mission rides the sky-
    of-purpose, health rides the earth-of-body.
    """
    a, b, c, d = big["A"], big["B"], big["C"], big["D"]
    f, h = small["F"], small["H"]

    # TODO: validate vs gadalkindom.ru — money/love line nodes are §4.3-§4.4.
    return {
        # Karma — personal axis (A↔D via E)
        "line_karma": [
            a,
            fold_to_arcana(a + d),
            d,
        ],
        # Mission — heaven-of-purpose (B↔C via E)
        "line_mission": [
            b,
            fold_to_arcana(b + c),
            c,
        ],
        # Money — vertical sky axis (B↔D)
        "line_money": [
            b,
            fold_to_arcana(b + d),
            d,
        ],
        # Love — F↔H relationship diagonal
        "line_love": [
            f,
            fold_to_arcana(f + h),
            h,
        ],
        # Health — earth axis (A↔C)
        "line_health": [
            a,
            fold_to_arcana(a + c),
            c,
        ],
    }


# ── §4.5 Karmic tails + extra points (HYPOTHESIS) ────────────────────────────


def _karmic_and_points(
    big: dict[str, int], small: dict[str, int], purpose: dict[str, int],
) -> dict[str, int]:
    """Karmic tails (male/female lineage) + comfort/socialisation/love points.

    HYPOTHESIS. The karmic tail is conventionally the fold of three
    generations of lineage anchor points; we approximate as fold of the
    anchor + adjacent diamond corner.
    """
    e = big["E"]
    male_anchor = purpose["male_lineage_anchor"]
    female_anchor = purpose["female_lineage_anchor"]

    # TODO: validate vs gadalkindom.ru — karmic tails are §4.5 hypothesis.
    return {
        "karmic_tail_male": fold_to_arcana(male_anchor + e),
        "karmic_tail_female": fold_to_arcana(female_anchor + e),
        "point_comfort": e,                                # center = comfort
        "point_socialization": fold_to_arcana(small["F"] + small["G"]),
        "point_love": fold_to_arcana(small["F"] + small["H"]),
    }


# ── Public entry point ───────────────────────────────────────────────────────


def calculate_matrix(birth_date: date) -> dict[str, Any]:
    """Compute the full Destiny Matrix from a birth date.

    Returns a flat dict matching the api.schemas.destiny_matrix.
    DestinyMatrixPositions schema. The output is deterministic — same
    input always gives the same matrix.
    """
    big = _big_diamond(birth_date.day, birth_date.month, birth_date.year)
    small = _small_square(big)
    purpose = _purpose_lines(big, small)
    chakras = _chakras(big, small, purpose)
    lines = _life_lines(big, small)
    karmic = _karmic_and_points(big, small, purpose)

    return {
        # Big diamond
        "A": big["A"], "B": big["B"], "C": big["C"], "D": big["D"], "E": big["E"],
        # Small square
        "F": small["F"], "G": small["G"], "H": small["H"], "I": small["I"],
        # Purpose triple
        "line_earth": purpose["line_earth"],
        "line_sky": purpose["line_sky"],
        "purpose_personal": purpose["purpose_personal"],
        "purpose_social": purpose["purpose_social"],
        "purpose_spiritual": purpose["purpose_spiritual"],
        # Chakras 7×3 + totals
        "chakras": chakras,
        # 5 life lines
        **lines,
        # Karmic + points
        **karmic,
    }
