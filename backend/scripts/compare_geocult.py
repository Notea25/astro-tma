#!/usr/bin/env python3
"""Read-only numerical comparison with the saved GeoCult fixture."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from services.astro.natal import calculate_natal
from services.astro.synastry import calculate_synastry
from services.astro.transits import calculate_transits, get_current_sky

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/geocult_known_time_2000_02_20_1430.json"
PLANET_TOLERANCE = 0.001
ORB_TOLERANCE = 0.01


def _aspect_key(p1: str, p2: str, aspect: str) -> tuple[str, str, str]:
    first, second = sorted((p1.lower(), p2.lower()))
    return first, second, aspect.lower()


def compare(fixture_path: Path) -> list[str]:
    reference = json.loads(fixture_path.read_text(encoding="utf-8"))
    profile = reference["profile"]
    chart = calculate_natal(
        name=profile["name"],
        birth_dt=datetime.fromisoformat(profile["birth_local"]),
        lat=float(profile["latitude"]),
        lng=float(profile["longitude"]),
        tz_str=profile["timezone"],
        birth_time_known=True,
    )
    failures: list[str] = []
    print("| Проверка | Astro TMA | GeoCult | Разница | Статус |")
    print("|---|---:|---:|---:|---|")
    for name, expected in reference["planets"].items():
        actual = getattr(chart, name)
        delta = abs(actual.degree - float(expected["longitude"]))
        ok = delta <= PLANET_TOLERANCE and actual.house == expected["house"] and actual.retrograde == expected["retrograde"]
        print(f"| {name} | {actual.degree:.4f} / H{actual.house} | {expected['longitude']:.7f} / H{expected['house']} | {delta:.7f}° | {'OK' if ok else 'FAIL'} |")
        if not ok:
            failures.append(f"planet {name}")
    for index, expected in enumerate(reference["houses"], start=1):
        actual = float(chart.houses[index - 1]["degree"])
        delta = abs(actual - float(expected))
        ok = delta <= PLANET_TOLERANCE
        print(f"| house {index} | {actual:.4f} | {expected:.7f} | {delta:.7f}° | {'OK' if ok else 'FAIL'} |")
        if not ok:
            failures.append(f"house {index}")
    actual_aspects = {_aspect_key(a.p1, a.p2, a.aspect): a.orb for a in chart.aspects}
    expected_aspects = {_aspect_key(a, b, kind): float(orb) for a, b, kind, orb in reference["aspects"]}
    if actual_aspects.keys() != expected_aspects.keys():
        failures.append("aspect set")
        print(f"| aspect set | {len(actual_aspects)} | {len(expected_aspects)} | — | FAIL |")
    for key, expected_orb in expected_aspects.items():
        actual_orb = actual_aspects.get(key)
        delta = abs(actual_orb - expected_orb) if actual_orb is not None else float("inf")
        ok = delta <= ORB_TOLERANCE
        print(f"| {' '.join(key)} | {actual_orb if actual_orb is not None else 'missing'} | {expected_orb:.2f} | {delta:.4f}° | {'OK' if ok else 'FAIL'} |")
        if not ok:
            failures.append(f"aspect {key}")

    transit_ref = reference["transits"]
    transit_at = datetime.fromisoformat(transit_ref["utc"])
    sky = get_current_sky(transit_at)
    for name, expected in transit_ref["planets"].items():
        actual = float(sky[name]["degree"])
        delta = abs(actual - float(expected))
        ok = delta <= PLANET_TOLERANCE
        print(f"| transit {name} | {actual:.4f} | {expected:.7f} | {delta:.7f}° | {'OK' if ok else 'FAIL'} |")
        if not ok:
            failures.append(f"transit planet {name}")
    transits = calculate_transits(
        datetime.fromisoformat(profile["birth_local"]),
        float(profile["latitude"]),
        float(profile["longitude"]),
        profile["timezone"],
        transit_at,
        True,
    )
    displayed = {
        _aspect_key(transit, natal, kind): float(orb)
        for transit, natal, kind, orb in transit_ref["displayed_major_aspects_under_2_degrees"]
    }
    for item in transits:
        if float(item["orb"]) >= 2:
            continue
        key = _aspect_key(item["transit_planet"], item["natal_planet"], item["aspect"])
        expected = displayed.get(key)
        ok = expected is not None and abs(float(item["orb"]) - expected) <= ORB_TOLERANCE
        print(f"| transit {' '.join(key)} | {item['orb']:.2f} | {expected if expected is not None else 'not displayed'} | — | {'OK' if ok else 'FAIL'} |")
        if not ok:
            failures.append(f"transit aspect {key}")

    syn_ref = reference["synastry"]
    partner = syn_ref["partner"]
    partner_chart = calculate_natal(
        "Partner",
        datetime.fromisoformat(partner["birth_local"]),
        float(partner["latitude"]),
        float(partner["longitude"]),
        partner["timezone"],
        True,
    )
    for name, expected in syn_ref["partner_planets"].items():
        actual = getattr(partner_chart, name).degree
        delta = abs(actual - float(expected))
        ok = delta <= PLANET_TOLERANCE
        print(f"| partner {name} | {actual:.4f} | {expected:.7f} | {delta:.7f}° | {'OK' if ok else 'FAIL'} |")
        if not ok:
            failures.append(f"partner planet {name}")
    def _subject(name: str, birth_local: str, data: dict) -> dict:
        return {
            "name": name,
            "birth_dt": datetime.fromisoformat(birth_local),
            "lat": float(data["latitude"]),
            "lng": float(data["longitude"]),
            "tz_str": data["timezone"],
            "birth_time_known": True,
        }
    syn = calculate_synastry(
        _subject("Astro QA", profile["birth_local"], profile),
        _subject("Partner", partner["birth_local"], partner),
    )
    actual_top = {
        _aspect_key(item["p1_name"], item["p2_name"], item["aspect"]): float(item["orb"])
        for item in syn["aspects"]
    }
    expected_top = {
        _aspect_key(p1, p2, kind): float(orb)
        for p1, p2, kind, orb in syn_ref["top_12_aspects"]
    }
    if actual_top.keys() != expected_top.keys():
        failures.append("synastry top-12 set")
    for key, expected in expected_top.items():
        actual = actual_top.get(key)
        delta = abs(actual - expected) if actual is not None else float("inf")
        ok = delta <= ORB_TOLERANCE
        print(f"| synastry {' '.join(key)} | {actual if actual is not None else 'missing'} | {expected:.2f} | {delta:.4f}° | {'OK' if ok else 'FAIL'} |")
        if not ok:
            failures.append(f"synastry aspect {key}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    args = parser.parse_args()
    failures = compare(args.fixture)
    print(f"\nИтог: {'FAIL — ' + ', '.join(failures) if failures else 'PASS'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
