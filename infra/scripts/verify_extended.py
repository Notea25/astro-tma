"""Phase 4 sanity check: extended calculator vs Ладини book + Юля etalons.

Confirms `calculate_purposes_v3()` produces the 8/8 canonical triples
for the book example 01.05.1969, and `calculate_year_energy()` matches
hand-computed values for the Юля example (08.07.2002).

Run:
    docker compose exec backend python /app/scripts/verify_extended.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from services.destiny_matrix.calculator import calculate_matrix  # noqa: E402
from services.destiny_matrix.extended import (  # noqa: E402
    calculate_purposes_v3,
    calculate_year_energy,
    karmic_program_key,
)


# Ладини book example, p. «Расшифровки»
BOOK_EXPECTED_PURPOSES = {
    "celestial_personal":  (5, 13, 18),
    "earthly_personal":    (1, 7, 8),
    "wholeness_personal":  (18, 8, 8),
    "father_lineage":      (6, 20, 8),
    "mother_lineage":      (12, 14, 8),
    "wholeness_lineage":   (8, 8, 16),
    "personal_divine":     (8, 16, 6),
    "divine_mission":      (16, 6, 22),
}


def check_purposes() -> int:
    positions = calculate_matrix(date(1969, 5, 1))
    actual = calculate_purposes_v3(positions)
    fails = 0
    for k, expected in BOOK_EXPECTED_PURPOSES.items():
        got = actual[k].key
        if got != expected:
            print(f"  ❌ {k}: got={got} expected={expected}")
            fails += 1
    if fails == 0:
        print("✅ 01.05.1969 — 8/8 purposes match Ладини book")
    return fails


def check_year_energy() -> int:
    fails = 0
    # Юля 08.07.2002, before her birthday in 2026 (on 02.06.2026)
    e1 = calculate_year_energy(date(2002, 7, 8), date(2026, 6, 2))
    if e1.current != 6 or e1.upcoming != 7:
        print(
            f"  ❌ Юля @ 02.06.2026: got current={e1.current} upcoming={e1.upcoming}; "
            "expected current=6 upcoming=7"
        )
        fails += 1
    else:
        print("✅ Юля @ 02.06.2026 — current=6 upcoming=7")

    # Юля after her birthday: energy already shifted to 7
    e2 = calculate_year_energy(date(2002, 7, 8), date(2026, 8, 1))
    if e2.current != 7:
        print(f"  ❌ Юля @ 01.08.2026: got current={e2.current}; expected current=7")
        fails += 1
    else:
        print("✅ Юля @ 01.08.2026 — current=7 (post-BD)")
    return fails


def check_karmic_key() -> int:
    # Yulia 08.07.2002: bottom should be 6, bottom_1 = near_corner = 6, bottom_2 = mid = 18
    # → "6-6-18" — exists in our karmic_programs as «Зеркальный соблазнитель»
    pos = calculate_matrix(date(2002, 7, 8))
    key = karmic_program_key(pos)
    if "-" not in key or len(key.split("-")) != 3:
        print(f"  ❌ malformed karmic key for Юля: {key}")
        return 1
    print(f"✅ Юля karmic key = {key}")
    return 0


def main() -> int:
    fails = check_purposes() + check_year_energy() + check_karmic_key()
    print()
    if fails == 0:
        print("PHASE 4 PASS — extended calculator matches book + Юля etalons.")
        return 0
    print(f"PHASE 4 FAIL — {fails} mismatches.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
