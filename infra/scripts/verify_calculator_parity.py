"""Phase 0 sanity check: confirm our backend calculator emits the same 36
values as the matritsa-sudbi.ru spec on 3 etalon dates.

Runs OUR backend `calculator.calculate_matrix()` (the one wired into prod),
maps the nested output to the flat `OctagramData` shape used by the new
interpretation spec, and diffs against the etalon table from the new
pack's `test_calculator_site.py`.

If this prints OK on all 3 dates → safe to proceed; the diagram won't
break because the math is identical, only the JSON shape differs.

Run:
    python infra/scripts/verify_calculator_parity.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from services.destiny_matrix.calculator import calculate_matrix  # noqa: E402


# ── Etalon from the new pack (test_calculator_site.py) ─────────────────────
ETALONS = {
    date(2001, 12, 15): {
        "day": 15, "month": 12, "year": 3, "bottom": 3, "center": 6,
        "top_left": 9, "top_right": 15, "bottom_right": 6, "bottom_left": 18,
        "month_1": 3, "day_1": 9, "year_1": 12, "bottom_1": 12,
        "aft_1": 6, "amt_1": 9, "afk_1": 18, "amk_1": 6,
        "month_2": 18, "day_2": 21, "year_2": 9, "bottom_2": 9,
        "aft_2": 15, "amt_2": 21, "afk_2": 12, "amk_2": 6,
        "month_3": 6, "day_3": 9,
        "comfort_a": 18, "comfort_b": 12,
        "cross_p": 18, "money_diag_1": 9, "love_diag_1": 9,
        "male_upper": [15, 6], "male_lower": [12, 18],
        "female_upper": [21, 9], "female_lower": [6, 6],
    },
    date(1988, 1, 13): {
        "day": 13, "month": 1, "year": 8, "bottom": 22, "center": 8,
        "top_left": 14, "top_right": 9, "bottom_right": 3, "bottom_left": 8,
        "month_1": 10, "day_1": 7, "year_1": 6, "bottom_1": 7,
        "aft_1": 9, "amt_1": 8, "afk_1": 14, "amk_1": 6,
        "month_2": 9, "day_2": 21, "year_2": 16, "bottom_2": 3,
        "aft_2": 22, "amt_2": 17, "afk_2": 11, "amk_2": 16,
        "month_3": 17, "day_3": 11,
        "comfort_a": 15, "comfort_b": 7,
        "cross_p": 19, "money_diag_1": 8, "love_diag_1": 22,
        "male_upper": [22, 9], "male_lower": [11, 14],
        "female_upper": [17, 8], "female_lower": [16, 6],
    },
    date(2000, 8, 17): {
        "day": 17, "month": 8, "year": 2, "bottom": 9, "center": 9,
        "top_left": 7, "top_right": 10, "bottom_right": 11, "bottom_left": 8,
        "month_1": 7, "day_1": 7, "year_1": 13, "bottom_1": 9,
        "aft_1": 5, "amt_1": 11, "afk_1": 4, "amk_1": 7,
        "month_2": 17, "day_2": 8, "year_2": 11, "bottom_2": 18,
        "aft_2": 16, "amt_2": 19, "afk_2": 20, "amk_2": 17,
        "month_3": 8, "day_3": 17,
        "comfort_a": 18, "comfort_b": 9,
        "cross_p": 11, "money_diag_1": 22, "love_diag_1": 11,
        "male_upper": [16, 5], "male_lower": [20, 4],
        "female_upper": [19, 11], "female_lower": [17, 7],
    },
}


def flatten(positions: dict) -> dict:
    """Pull the 36 etalon-named values out of our nested API response."""
    pers = positions["personality"]
    sq = positions["ancestral_square"]
    ch = positions["channels"]
    sp = positions["specials"]
    fl = positions["family_lines"]
    return {
        # base diamond
        "day": pers["day"], "month": pers["month"], "year": pers["year"],
        "bottom": pers["bottom"], "center": pers["center"],
        # square corners
        "top_left": sq["top_left"], "top_right": sq["top_right"],
        "bottom_right": sq["bottom_right"], "bottom_left": sq["bottom_left"],
        # dot1 (near_corner = channels[0])
        "month_1":  ch["talents"][0],
        "day_1":    ch["parental"][0],
        "year_1":   ch["material_karma"][0],
        "bottom_1": ch["karmic_tail"][0],
        "aft_1":    ch["ancestral_father_talents"][0],
        "amt_1":    ch["ancestral_mother_talents"][0],
        "afk_1":    ch["ancestral_father_karma"][0],
        "amk_1":    ch["ancestral_mother_karma"][0],
        # dot2 (mid = channels[1] = specials for cardinals)
        "month_2":  sp["talent"],
        "day_2":    sp["character"],
        "year_2":   sp["money"],
        "bottom_2": sp["love"],
        "aft_2":    ch["ancestral_father_talents"][1],
        "amt_2":    ch["ancestral_mother_talents"][1],
        "afk_2":    ch["ancestral_father_karma"][1],
        "amk_2":    ch["ancestral_mother_karma"][1],
        # dot3 (near_center = channels[2], only top/left)
        "month_3":  ch["talents"][2],
        "day_3":    ch["parental"][2],
        # specials inside the inner circle
        "comfort_a":    sp["comfort"][0],
        "comfort_b":    sp["comfort"][1],
        "cross_p":      sp["cross"],
        "money_diag_1": positions["money_diagonal"][0],
        "love_diag_1":  sp["love_diag_1"],
        # family-line half-diagonals (2 dots per side)
        "male_upper":   fl["male_upper"],
        "male_lower":   fl["male_lower"],
        "female_upper": fl["female_upper"],
        "female_lower": fl["female_lower"],
    }


def run() -> int:
    failures = 0
    for birth, etalon in ETALONS.items():
        positions = calculate_matrix(birth)
        ours = flatten(positions)
        diffs = []
        for key, expected in etalon.items():
            got = ours.get(key)
            if got != expected:
                diffs.append(f"  {key}: got={got} expected={expected}")
        if diffs:
            failures += 1
            print(f"❌ {birth} — {len(diffs)} field(s) mismatch:")
            for d in diffs:
                print(d)
        else:
            print(f"✅ {birth} — 36/36 fields match")
    print()
    if failures == 0:
        print("PHASE 0 PASS — math is identical, safe to proceed.")
        return 0
    print(f"PHASE 0 FAIL — {failures}/{len(ETALONS)} dates have mismatches.")
    return 1


if __name__ == "__main__":
    sys.exit(run())
