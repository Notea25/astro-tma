"""HTML/CSS natal chart PDF renderer.

The public API mirrors ``services.natal_pdf.generate_natal_pdf`` but renders a
print-oriented HTML document through Playwright/Chromium. The old ReportLab
renderer remains the route fallback.
"""

from __future__ import annotations

import html
import math
import re
import time
from datetime import datetime
from typing import Any

from core.logging import get_logger
from services.astro.planet_names import PLANET_GLYPH as PLANET_SYMBOLS
from services.astro.planet_names import PLANET_RU
from services.astro.sign_cases import sign_ru as _sign_case_ru
from services.natal_pdf import (
    ASPECT_ORDER,
    ASPECT_RU,
    ASPECT_SYMBOLS,
    ASPECT_TOPICS,
    ELEMENT_COPY,
    ELEMENTS,
    GLOSSARY,
    HOUSE_LABELS,
    PLANET_ORDER,
    SIGN_RU,
    SIGN_SYMBOLS,
)
from services.natal_pdf import (
    _aspect_fallback as _aspect_fallback_base,
)
from services.natal_pdf import (
    _house_fallback as _house_fallback_base,
)
from services.natal_pdf import (
    _planet_fallback as _planet_fallback_base,
)

log = get_logger(__name__)

GOLD = "#d6b85a"
GOLD_DIM = "#8d7842"
BG = "#050510"
PANEL = "#100c1f"
PANEL_DARK = "#0b0714"
WHEEL_BG = "#071029"
TEXT = "#f4f0e8"
TEXT_DIM = "#a9a1bb"
BORDER = "rgba(214, 184, 90, .22)"

ELEMENT_COLORS = {
    "fire": "#e05b30",
    "earth": "#1fa37c",
    "air": "#398ada",
    "water": "#5846b6",
}
# Символы стихий (геометрические треугольники — стабильно рендерятся в любом
# шрифте PDF). Огонь △, земля ▽, воздух △ с чертой, вода ▽ с чертой. Раньше для
# всех стихий хардкодился огненный △ — земля/воздух/вода выглядели как огонь.
ELEMENT_SYMBOLS = {
    "fire": "△",
    "earth": "▽",
    "air": "▵",
    "water": "▿",
}
ASPECT_COLORS = {
    "conjunction": GOLD,
    "trine": "#1fa37c",
    "sextile": "#96d957",
    "square": "#398ada",  # синий — чтобы НЕ путать с оппозицией (красный)
    "opposition": "#ff585f",
    "quincunx": "#8b65da",
}
PLANET_COLORS = {
    "sun": "#f3cf4e",
    "moon": "#cad4f3",
    "mercury": "#8dd05f",
    "venus": "#ef85a4",
    "mars": "#f05a5a",
    "jupiter": "#e8955c",
    "saturn": "#8f8f9a",
    "uranus": "#7b77e7",
    "neptune": "#78a9e8",
    "pluto": "#bb426b",
}
TOTAL_PAGES_TOKEN = "__TOTAL_PAGES__"


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _key(value: Any) -> str:
    return str(value or "").strip().lower()


def _sign_ru(sign: Any) -> str:
    return _sign_case_ru(sign)


def _sign_ru_case(sign: Any, case: str) -> str:
    if case == "prep":
        return _sign_case_ru(sign, "prep")
    if case == "gen":
        return _sign_case_ru(sign, "gen")
    return _sign_case_ru(sign)


def _sign_symbol(sign: Any) -> str:
    key = _key(sign)
    if key not in SIGN_SYMBOLS:
        reverse = {v.lower(): k for k, v in SIGN_RU.items()}
        key = reverse.get(key, key)
    return SIGN_SYMBOLS.get(key, "")


def _sign_abs_degree(sign: Any) -> float:
    sign_order = list(SIGN_RU.keys())
    key = _key(sign)
    return float(sign_order.index(key) * 30) if key in sign_order else 0.0


def _chart_abs_degree(point: dict[str, Any]) -> float:
    if point.get("degree") is not None:
        return float(point.get("degree") or 0) % 360
    return (_sign_abs_degree(point.get("sign")) + float(point.get("sign_degree") or 0)) % 360


def _planet_key(name: Any) -> str:
    raw = _key(name)
    reverse = {
        "солнце": "sun",
        "луна": "moon",
        "меркурий": "mercury",
        "венера": "venus",
        "марс": "mars",
        "юпитер": "jupiter",
        "сатурн": "saturn",
        "уран": "uranus",
        "нептун": "neptune",
        "плутон": "pluto",
    }
    return reverse.get(raw, raw)


def _aspect_key(name: Any) -> str:
    raw = _key(name)
    reverse = {
        "соединение": "conjunction",
        "трин": "trine",
        "секстиль": "sextile",
        "квадрат": "square",
        "оппозиция": "opposition",
        "квинконс": "quincunx",
    }
    return reverse.get(raw, raw)


def _roman(num: int) -> str:
    values = (
        (10, "X"),
        (9, "IX"),
        (8, "VIII"),
        (7, "VII"),
        (6, "VI"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    out = ""
    rest = num
    for value, glyph in values:
        while rest >= value:
            out += glyph
            rest -= value
    return out


def _deg_str(deg: float | int | None, *, within_sign: bool = True) -> str:
    value = float(deg or 0)
    if within_sign:
        value = value % 30
    d = int(value)
    m = int((value - d) * 60)
    return f"{d}°{m:02d}'"


def _lines(text: str, max_words: int) -> str:
    words = str(text or "").replace("\n", " ").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(" .,;:") + "."


_DANGLING_TAIL_WORDS = {
    "а",
    "в",
    "во",
    "для",
    "за",
    "и",
    "или",
    "к",
    "ко",
    "на",
    "над",
    "не",
    "о",
    "об",
    "от",
    "по",
    "под",
    "при",
    "про",
    "с",
    "со",
    "у",
    "через",
}


def _trim_dangling_tail(text: str) -> str:
    words = str(text or "").strip().split()
    while words and words[-1].strip("«»\"'.,;:—-").lower() in _DANGLING_TAIL_WORDS:
        words.pop()
    return " ".join(words).rstrip(" .,;:—-")


def _first_sentences(text: str, max_chars: int = 170) -> str:
    """Усечение по границе предложения (для коротких карточек «Ключевые точки»).

    Накапливает целые предложения, пока влезают в лимит символов; всегда
    возвращает хотя бы одно предложение. Если первое предложение длиннее лимита —
    режет по последнему пробелу и добавляет «…» (без обрыва слова)."""
    clean = " ".join(str(text or "").replace("\n", " ").split())
    if not clean:
        return ""
    sentences = re.findall(r"[^.!?…]+[.!?…]+|[^.!?…]+$", clean)
    out = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = (out + " " + sentence).strip() if out else sentence.strip()
        if out and len(candidate) > max_chars:
            break
        if not out and len(candidate) > max_chars:
            break
        out = candidate
        if len(out) >= max_chars:
            break
    if not out:
        first = sentences[0].strip()
        window = first[:max_chars]
        cut_at = max(window.rfind(mark) for mark in (",", ";", ":", " — ", " - "))
        if cut_at >= max_chars * 0.55:
            out = window[:cut_at]
        else:
            out = window.rsplit(" ", 1)[0] if " " in window else window
        out = _trim_dangling_tail(out)
        return (out + "…") if out else first[:max_chars].rstrip() + "…"
    if len(out) > max_chars:
        cut = out[:max_chars].rsplit(" ", 1)[0].rstrip(" .,;:—-")
        cut = _trim_dangling_tail(cut)
        out = (cut + "…") if cut else out[:max_chars].rstrip() + "…"
    return out


def _word_count(text: str) -> int:
    return len(str(text or "").split())


def _split_words(text: str, max_words: int) -> list[str]:
    """Split text into chunks of at most max_words, breaking at sentence boundaries."""
    words = str(text or "").split()
    if len(words) <= max_words:
        return [" ".join(words)] if words else []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        if end < len(words):
            # Try to find the last sentence boundary (. ! ?) within the window
            best = end
            for i in range(end - 1, max(start, end - 40) - 1, -1):
                if words[i].endswith((".", "!", "?", "…")):
                    best = i + 1
                    break
            end = best
        chunks.append(" ".join(words[start:end]))
        start = end
    return chunks


def _description(entry: Any, fallback: str, *, words: int) -> str:
    if isinstance(entry, dict):
        source = str(entry.get("full") or "").strip()
    else:
        source = ""
    fallback = str(fallback or "").strip()
    if source and fallback and _word_count(source) < max(18, words // 2):
        source = f"{source} {fallback}"
    if not source:
        source = fallback
    return _lines(source, words)


def _card_blurb(entry: Any, fallback: str, *, max_chars: int = 230) -> str:
    """Короткий текст для карточек «Ключевые точки»: целые предложения, без
    обрыва на полуслове. Источник — «full» (или fallback), как у _description:
    «short» — это in-app popup, в PDF не идёт. Затем усечение по границе
    предложения через _first_sentences (вместо пословного _lines, который резал
    «…задачей — не.»). Лимит 230 (а не 170): карточка key-card высокая
    (min-height 86mm), типичное первое предложение ~150-190 символов влезает
    целиком, и первый экран PDF не обрывает мысль (P0-2, карта Andrey)."""
    source = ""
    if isinstance(entry, dict):
        source = str(entry.get("full") or "").strip()
    if not source:
        source = str(fallback or "").strip()
    return _first_sentences(source, max_chars)


def _full_description(entry: Any, fallback: str) -> str:
    if isinstance(entry, dict):
        source = str(entry.get("full") or "").strip()
    else:
        source = ""
    return source or str(fallback or "").strip()


def _planet_fallback(name: str, planet: dict[str, Any]) -> str:
    return _planet_fallback_base(name, planet)


def _house_fallback(house: dict[str, Any]) -> str:
    return _house_fallback_base(house)


def _aspect_fallback(aspect: dict[str, Any]) -> str:
    return _aspect_fallback_base(aspect)


def _aspect_description_map(
    descriptions: dict[str, Any] | None,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry in (descriptions or {}).get("aspects") or []:
        if not isinstance(entry, dict):
            continue
        p1 = _planet_key(entry.get("p1"))
        p2 = _planet_key(entry.get("p2"))
        atype = _aspect_key(entry.get("type") or entry.get("aspect"))
        if p1 and p2 and atype:
            out[(p1, p2, atype)] = entry
            out[(p2, p1, atype)] = entry
    return out


def _sign_element(sign: Any) -> str:
    sign_key = _key(sign)
    if sign_key not in SIGN_SYMBOLS:
        reverse = {v.lower(): k for k, v in SIGN_RU.items()}
        sign_key = reverse.get(sign_key, sign_key)
    for element, (_, signs) in ELEMENTS.items():
        if sign_key in signs:
            return element
    return "fire"


def _element_percentages(planets: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {element: 0 for element in ELEMENTS}
    for planet in planets.values():
        counts[_sign_element(planet.get("sign"))] += 1
    total = max(sum(counts.values()), 1)
    return {key: round(value / total * 100) for key, value in counts.items()}


def _dominant_element(planets: dict[str, dict[str, Any]]) -> str:
    percentages = _element_percentages(planets)
    return max(percentages.items(), key=lambda item: item[1])[0] if percentages else "fire"


def _format_birth_date(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%d.%m.%Y")
    except ValueError:
        return value


def _section_header(title: str, subtitle: str, aside: str = "") -> str:
    return (
        f'<div class="section-head"><div class="section-head-row">'
        f"<h2>{_e(title)}</h2><p>{_e(subtitle)}</p></div>"
        f'<div class="rule"></div></div>'
    )


def _footer(page: int, total: int | str = TOTAL_PAGES_TOKEN) -> str:
    return f"<footer>ASTRO TMA · НАТАЛЬНАЯ КАРТА <span>{page} / {total}</span></footer>"


def _page(page: int, body: str, *, class_name: str = "") -> str:
    cls = f"page {class_name}".strip()
    return f'<section class="{cls}">{body}{_footer(page)}</section>'


def _card(title: str, body: str, *, class_name: str = "", meta: str = "", icon: str = "") -> str:
    icon_html = f'<div class="card-icon">{icon}</div>' if icon else ""
    meta_html = f'<div class="card-meta">{_e(meta)}</div>' if meta else ""
    return (
        f'<article class="card {class_name}">{icon_html}<h3>{title}</h3>'
        f'{meta_html}<div class="mini-rule"></div><p>{body}</p></article>'
    )


def _polar(cx: float, cy: float, radius: float, degree: float) -> tuple[float, float]:
    angle = math.radians(degree)
    return cx + math.cos(angle) * radius, cy + math.sin(angle) * radius


def _ascendant_degree(houses: list[dict[str, Any]], asc_sign: str | None) -> float:
    for house in houses:
        if int(house.get("number") or 0) == 1:
            return _chart_abs_degree(house)
    return _sign_abs_degree(asc_sign)


def _wheel_angle(abs_degree: float, ascendant_degree: float) -> float:
    return 180 + (abs_degree - ascendant_degree)


def _natal_wheel_svg(
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    asc_sign: str | None,
) -> str:
    cx = cy = 360
    outer = 315
    middle = 250
    inner = 170
    asc = _ascendant_degree(houses, asc_sign)
    sign_keys = list(SIGN_RU.keys())
    parts = [
        '<svg class="wheel-svg" viewBox="0 0 720 720" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="720" height="720" fill="{WHEEL_BG}"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{outer}" fill="none" stroke="{GOLD_DIM}" stroke-width="1"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{middle}" fill="none" stroke="{GOLD_DIM}" stroke-width=".8" opacity=".75"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{inner}" fill="none" stroke="{GOLD_DIM}" stroke-width=".8" opacity=".55"/>',
    ]
    for i, sign in enumerate(sign_keys):
        start = _wheel_angle(i * 30, asc)
        x1, y1 = _polar(cx, cy, middle, start)
        x2, y2 = _polar(cx, cy, outer, start)
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{GOLD_DIM}" stroke-width=".7" opacity=".7"/>'
        )
        gx, gy = _polar(cx, cy, 286, _wheel_angle(i * 30 + 15, asc))
        parts.append(
            f'<text x="{gx:.1f}" y="{gy:.1f}" text-anchor="middle" dominant-baseline="middle" fill="{GOLD}" font-size="30">{SIGN_SYMBOLS[sign]}</text>'
        )
    ordered_houses = sorted(
        [h for h in houses if int(h.get("number") or 0)], key=lambda h: int(h.get("number") or 0)
    )
    for index, house in enumerate(ordered_houses):
        num = int(house.get("number") or 0)
        angle = _wheel_angle(_chart_abs_degree(house), asc)
        x1, y1 = _polar(cx, cy, inner, angle)
        x2, y2 = _polar(cx, cy, middle, angle)
        width = 1.3 if num in (1, 4, 7, 10) else 0.55
        color = GOLD if num in (1, 4, 7, 10) else GOLD_DIM
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}" opacity=".75"/>'
        )
        next_house = ordered_houses[(index + 1) % len(ordered_houses)] if ordered_houses else house
        span = (_chart_abs_degree(next_house) - _chart_abs_degree(house)) % 360
        tx, ty = _polar(cx, cy, 210, _wheel_angle((_chart_abs_degree(house) + span / 2) % 360, asc))
        parts.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" dominant-baseline="middle" fill="{GOLD_DIM}" font-size="17">{_roman(num)}</text>'
        )
    planet_points: dict[str, tuple[float, float]] = {}
    planet_angles: dict[str, float] = {}
    for name in PLANET_ORDER:
        planet = planets.get(name)
        if not planet:
            continue
        angle = _wheel_angle(_chart_abs_degree(planet), asc)
        px, py = _polar(cx, cy, 143, angle)
        planet_points[name] = (px, py)
        planet_angles[name] = angle
    for aspect in sorted(aspects, key=lambda a: float(a.get("orb") or 99))[:16]:
        p1 = _planet_key(aspect.get("p1"))
        p2 = _planet_key(aspect.get("p2"))
        atype = _aspect_key(aspect.get("aspect"))
        if p1 not in planet_points or p2 not in planet_points:
            continue
        x1, y1 = planet_points[p1]
        x2, y2 = planet_points[p2]
        dash = ' stroke-dasharray="5 5"' if atype in ("sextile", "opposition", "quincunx") else ""
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{ASPECT_COLORS.get(atype, GOLD_DIM)}" stroke-width=".8" opacity=".55"{dash}/>'
        )
    for name, (px, py) in planet_points.items():
        parts.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="15" fill="{BG}" stroke="{GOLD_DIM}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{py + 1:.1f}" text-anchor="middle" dominant-baseline="middle" fill="{PLANET_COLORS.get(name, GOLD)}" font-size="26">{PLANET_SYMBOLS.get(name, "")}</text>'
        )
        # Degree label outside the planet circle, pushed radially outward
        planet = planets.get(name) or {}
        deg_value = planet.get("sign_degree")
        if deg_value is None:
            deg_value = float(planet.get("degree") or 0) % 30
        deg_int = int(float(deg_value))
        deg_label = f"{deg_int}°"
        if planet.get("retrograde"):
            deg_label += "℞"
        label_x, label_y = _polar(cx, cy, 122, planet_angles[name])
        parts.append(
            f'<text x="{label_x:.1f}" y="{label_y + 1:.1f}" text-anchor="middle" dominant-baseline="middle" fill="{GOLD}" font-size="12" font-weight="600">{deg_label}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _donut_svg(percentages: dict[str, int], dominant: str) -> str:
    total = max(sum(percentages.values()), 1)
    radius = 80
    circumference = 2 * math.pi * radius
    offset = 0.0
    circles = []
    for element in ELEMENTS:
        pct = percentages.get(element, 0)
        length = circumference * pct / total
        circles.append(
            f'<circle class="donut-seg" r="{radius}" cx="110" cy="110" '
            f'stroke="{ELEMENT_COLORS[element]}" stroke-dasharray="{length:.2f} {circumference - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}"/>'
        )
        offset += length
    label = ELEMENTS[dominant][0]
    return (
        '<svg class="donut" viewBox="0 0 220 220">'
        '<circle r="80" cx="110" cy="110" fill="none" stroke="#141029" stroke-width="38"/>'
        f"{''.join(circles)}"
        f'<text x="110" y="103" text-anchor="middle" class="donut-kicker">ДОМИНАНТА</text>'
        f'<text x="110" y="129" text-anchor="middle" class="donut-label">{_e(label)} {percentages.get(dominant, 0)}%</text>'
        "</svg>"
    )


def _css() -> str:
    return f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; overflow-wrap: anywhere; }}
html, body {{ margin: 0; padding: 0; background: {BG}; color: {TEXT}; }}
body {{ font-family: "DejaVu Sans", Arial, sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.page {{ position: relative; display: block; width: 210mm; height: 297mm; overflow: hidden; padding: 22mm 18mm 17mm; background: {BG}; break-after: page; page-break-after: always; break-inside: avoid; }}
.cover {{ display: flex; flex-direction: column; align-items: center; text-align: center; padding-top: 30mm; }}
.mark {{ color: {GOLD}; font-size: 32px; margin-bottom: 34mm; line-height: 1; }}
h1, h2, h3, .serif {{ font-family: "DejaVu Serif", Georgia, serif; font-weight: 400; }}
h1 {{ margin: 0; color: {GOLD}; font-size: 34px; letter-spacing: 7px; text-transform: uppercase; }}
.cover-subtitle {{ margin-top: 12mm; font: italic 16px "DejaVu Serif", Georgia, serif; color: {TEXT}; opacity: .92; }}
.cover-name {{ margin-top: 36mm; font: italic 21px "DejaVu Serif", Georgia, serif; }}
.cover-meta {{ margin-top: 10mm; color: {TEXT_DIM}; font-size: 13px; line-height: 1.72; }}
.cover-points {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 19mm; margin-top: 6mm; width: 128mm; }}
.cover-point .glyph {{ color: {GOLD}; font-size: 28px; line-height: 1; }}
.cover-point .label {{ margin-top: 7mm; color: {TEXT_DIM}; font-size: 10.5px; letter-spacing: 3px; text-transform: uppercase; }}
.cover-point .value {{ margin-top: 6mm; font: 15px "DejaVu Serif", Georgia, serif; }}
.cover-line {{ width: 32mm; height: 1px; background: {GOLD_DIM}; margin-top: 20mm; }}
.cover-foot {{ margin-top: 8mm; color: #776f8c; font-size: 10px; letter-spacing: 3px; }}
.section-head {{ margin-bottom: 4mm; }}
.section-head-row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 6mm; }}
h2 {{ margin: 0; color: {GOLD}; font-size: 17px; letter-spacing: 3px; }}
.rule {{ height: 1px; width: 170mm; background: rgba(214,184,90,.2); margin: 3mm 0 0; }}
.section-head p {{ margin: 0; color: {TEXT_DIM}; font: italic 10.5px "DejaVu Serif", Georgia, serif; white-space: nowrap; }}
.section-aside {{ color: #807894; font-size: 12px; margin-top: 5mm; }}
footer {{ position: absolute; bottom: 7mm; left: 0; right: 0; text-align: center; color: #6d6680; font-size: 10px; letter-spacing: 3px; }}
footer span {{ letter-spacing: 1px; margin-left: 8px; }}
.toc-list {{ margin-top: 22mm; }}
.toc-row {{ display: grid; grid-template-columns: 12mm 1fr 14mm; align-items: center; min-height: 16mm; border-bottom: 1px solid rgba(255,255,255,.025); }}
.toc-roman {{ color: {GOLD}; font: 15px "DejaVu Serif", Georgia, serif; }}
.toc-title {{ font: 14px "DejaVu Serif", Georgia, serif; }}
.toc-page {{ color: {TEXT_DIM}; text-align: right; font-size: 13px; }}
.cards-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6mm; }}
.grid-2 {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 4.5mm; }}
.card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px; padding: 5mm 6mm; min-height: 39mm; }}
.card h3 {{ margin: 0; color: {TEXT}; font-size: 15px; line-height: 1.3; }}
.card p {{ margin: 3mm 0 0; font-size: 12px; line-height: 1.55; color: {TEXT}; }}
.card-icon {{ color: {GOLD}; font-size: 25px; margin-bottom: 4mm; }}
.card-meta {{ color: {TEXT_DIM}; font-size: 10px; letter-spacing: .8px; text-transform: uppercase; margin-top: 1.5mm; }}
.mini-rule {{ width: 14mm; height: 1px; margin-top: 3mm; background: {GOLD_DIM}; }}
.key-card {{ text-align: center; min-height: 86mm; padding: 8mm 6mm 7mm; }}
.key-card .card-icon {{ margin-bottom: 2mm; }}
.key-card .zodiac-dot {{ margin: 5mm auto 3mm; width: 7mm; height: 7mm; border-radius: 50%; display: grid; place-items: center; color: white; font-size: 15px; }}
.key-card h3 {{ font-size: 19px; }}
.key-card .mini-rule {{ margin: 4mm auto 0; }}
.key-card .quote {{ margin-top: 3mm; color: {TEXT_DIM}; font: italic 11px "DejaVu Serif", Georgia, serif; }}
.key-card p {{ text-align: center; color: {TEXT_DIM}; margin-top: 4mm; }}
.dominant-card {{ margin-top: 8mm; border-left: 3px solid {GOLD}; min-height: 35mm; display: grid; grid-template-columns: 12mm 1fr; gap: 5mm; align-items: center; }}
.dominant-symbol {{ font-size: 27px; color: var(--element-color); }}
.dominant-card h3 {{ color: {GOLD}; font-size: 17px; }}
.wheel-wrap {{ width: 164mm; height: 164mm; margin: 9mm auto 7mm; background: {WHEEL_BG}; display: flex; align-items: center; justify-content: center; }}
.wheel-wrap svg {{ width: 100%; height: 100%; max-width: 100%; display: block; }}
.wheel-svg {{ width: 100%; height: 100%; display: block; }}
.legend {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 3mm 24mm; width: 154mm; margin: 0 auto; color: {TEXT_DIM}; font-size: 11.5px; }}
.legend-line {{ display: inline-block; width: 13mm; height: 1px; margin-right: 4mm; vertical-align: middle; background: currentColor; }}
.elements-layout {{ display: grid; grid-template-columns: 78mm 1fr; gap: 9mm; align-items: center; margin-top: 10mm; }}
.donut {{ width: 72mm; height: 72mm; transform: rotate(-90deg); }}
.donut text {{ transform: rotate(90deg); transform-origin: 110px 110px; font-family: "DejaVu Serif", Georgia, serif; }}
.donut-seg {{ fill: none; stroke-width: 38; transform: rotate(-90deg); transform-origin: 110px 110px; }}
.donut-kicker {{ fill: #73b568; font-size: 11px; letter-spacing: 2px; }}
.donut-label {{ fill: {GOLD}; font-size: 17px; }}
.element-list {{ display: grid; gap: 3mm; }}
.element-row {{ display: grid; grid-template-columns: 9mm 1fr 12mm; align-items: center; background: {PANEL}; border: 1px solid {BORDER}; border-radius: 7px; padding: 3.5mm 4mm; font: 14px "DejaVu Serif", Georgia, serif; }}
.swatch {{ width: 6mm; height: 6mm; border-radius: 2px; background: var(--element-color); }}
.percent {{ color: {GOLD}; text-align: right; font-family: "DejaVu Sans"; font-weight: 700; }}
.element-cards {{ margin-top: 12mm; }}
.element-card h3 {{ color: var(--element-color); }}
.tags {{ margin-top: 8mm; display: flex; gap: 3mm; flex-wrap: wrap; }}
.tag {{ border: 1px solid rgba(224,91,48,.35); color: #d99072; background: rgba(224,91,48,.13); border-radius: 999px; padding: 1.5mm 5mm; font-size: 11px; }}
.zero-elements {{ margin-top: 7mm; display: grid; gap: 3.5mm; }}
.zero-element-card {{ min-height: auto; padding: 4mm 5mm; background: {PANEL_DARK}; }}
.zero-element-card h3 {{ font-size: 14px; margin-bottom: 2mm; }}
.zero-element-card p {{ font-size: 12px; line-height: 1.55; color: {TEXT_DIM}; margin: 0; }}
.planet-card {{ display: flex; flex-wrap: wrap; align-items: center; }}
.planet-card .card-icon {{ font-size: 22px; color: var(--planet-color); margin: 0 4mm 0 0; flex: 0 0 auto; }}
.planet-card > h3 {{ margin: 0; flex: 1 1 auto; }}
.planet-card .card-meta {{ margin: 0 0 0 4mm; flex: 0 0 auto; white-space: nowrap; }}
.planet-card .mini-rule {{ flex-basis: 100%; margin-top: 3mm; }}
.planet-card > p {{ flex-basis: 100%; }}
.detail-card {{ min-height: auto; margin-bottom: 3mm; }}
.detail-card p {{ font-size: 12px; line-height: 1.55; color: {TEXT}; }}
.detail-card.continuation h3::after {{ content: " · продолжение"; color: {TEXT_DIM}; font-family: "DejaVu Sans", Arial, sans-serif; font-size: 12px; }}
.retro {{ display: inline-block; margin-left: 3mm; padding: 1mm 3mm; border: 1px solid {GOLD_DIM}; border-radius: 999px; color: {GOLD}; font-size: 11px; letter-spacing: 1px; }}
.houses-grid {{ display: grid; grid-template-columns: 1fr; gap: 0; }}
.house-card {{ padding: 4mm 5mm; }}
.house-top {{ display: flex; justify-content: space-between; align-items: baseline; gap: 4mm; }}
.house-head {{ display: flex; align-items: baseline; flex-wrap: wrap; gap: 0 2.5mm; }}
.house-num {{ color: {GOLD}; font: 15.5px "DejaVu Serif", Georgia, serif; }}
.house-sign {{ font: 12px "DejaVu Serif", Georgia, serif; }}
.house-degree {{ color: {TEXT_DIM}; font-size: 11px; white-space: nowrap; }}
.house-label {{ color: {TEXT_DIM}; font-size: 10.5px; letter-spacing: 1.4px; text-transform: uppercase; }}
.house-label::before {{ content: "· "; }}
.house-axis {{ font-weight: 700; }}
.house-card p {{ margin-top: 3mm; font-size: 12.5px; line-height: 1.55; }}
.house-card.detail-card p {{ font-size: 12px; line-height: 1.5; }}
.metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 4mm; margin: 8mm 0 7mm; }}
.metric {{ text-align: center; background: {PANEL}; border: 1px solid {BORDER}; border-radius: 7px; padding: 4mm 0 3.5mm; }}
.metric strong {{ color: var(--metric-color, {GOLD}); display: block; font: 22px "DejaVu Serif", Georgia, serif; }}
.metric span {{ color: {TEXT_DIM}; font-size: 11px; letter-spacing: 1.2px; text-transform: uppercase; }}
.aspect-group {{ margin-top: 3mm; break-inside: avoid; }}
.aspect-group h3 {{ color: var(--aspect-color); font-size: 15px; letter-spacing: 1.2px; text-transform: uppercase; margin: 0 0 2.5mm; }}
.aspect-group h3 em {{ color: {TEXT_DIM}; text-transform: none; font-size: 11.5px; letter-spacing: 0; margin-left: 3mm; }}
.aspect-row {{ padding: 3mm 4mm; background: {PANEL}; border: 1px solid {BORDER}; border-radius: 7px; break-inside: avoid; }}
.aspect-title {{ display: flex; flex-wrap: nowrap; align-items: flex-start; justify-content: space-between; gap: 4mm; color: {TEXT}; font-size: 14.5px; line-height: 1.3; }}
.aspect-title .aspect-name {{ flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.orb {{ flex: 0 0 auto; color: {TEXT_DIM}; white-space: nowrap; font-size: 12px; }}
.aspect-row p {{ display: block; margin: 2.5mm 0 0; color: {TEXT_DIM}; line-height: 1.55; font-size: 13px; }}
.aspect-row.detail-card p {{ color: {TEXT}; font-size: 11.5px; line-height: 1.5; }}
.reading {{ padding-right: 4mm; }}
.reading-quote {{ text-align: center; color: {TEXT_DIM}; font: italic 14px "DejaVu Serif", Georgia, serif; margin: 8mm 0 9mm; }}
.reading h3 {{ color: {GOLD}; font-family: "DejaVu Serif", Georgia, serif; font-size: 22px; font-weight: 500; letter-spacing: 0.01em; line-height: 1.3; text-transform: none; margin: 0 0 2.2mm; }}
.reading p {{ font-size: 17px; line-height: 1.72; margin: 0 0 6.4mm; color: {TEXT}; }}
.final {{ display: flex; flex-direction: column; align-items: center; text-align: center; padding-top: 18mm; }}
.final .mark {{ margin-bottom: 8mm; }}
.final-hero {{ display: flex; flex-direction: column; align-items: center; margin-bottom: 8mm; }}
.final-copy {{ font: italic 15px/1.6 "DejaVu Serif", Georgia, serif; width: 110mm; }}
.glossary-title {{ color: {GOLD}; font: 18px "DejaVu Serif", Georgia, serif; letter-spacing: 4px; text-transform: uppercase; margin: 8mm 0 7mm; }}
.glossary-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 5mm; width: 170mm; }}
.glossary-card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px; padding: 7mm 6mm 6mm; min-height: 48mm; text-align: left; position: relative; }}
.glossary-glyph {{ color: {GOLD}; font-size: 26px; line-height: 1; margin-bottom: 4mm; font-family: "DejaVu Serif", Georgia, serif; }}
.glossary-card h3 {{ color: {TEXT}; font-size: 15px; margin: 0; letter-spacing: 1px; }}
.glossary-card .mini-rule {{ width: 12mm; height: 1px; margin: 3mm 0 4mm; background: {GOLD_DIM}; }}
.glossary-card p {{ margin: 0; font-size: 12px; line-height: 1.55; color: {TEXT_DIM}; }}
"""


def _content_page(
    *, planets_page: int, houses_page: int, aspects_page: int, reading_page: int
) -> str:
    rows = [
        ("I", "Ключевые точки карты", "3"),
        ("II", "Натальное колесо", "4"),
        ("III", "Баланс стихий и характер", "5"),
        ("IV", "Планеты в знаках", str(planets_page)),
        ("V", "Дома гороскопа", str(houses_page)),
        ("VI", "Аспекты — связи между планетами", str(aspects_page)),
        ("VII", "Персональная интерпретация", str(reading_page)),
    ]
    body = _section_header("Содержание", "Что внутри отчёта")
    body += (
        '<div class="toc-list">'
        + "".join(
            f'<div class="toc-row"><div class="toc-roman">{roman}</div><div class="toc-title">{_e(title)}</div><div class="toc-page">{page}</div></div>'
            for roman, title, page in rows
        )
        + "</div>"
    )
    return _page(2, body)


def _cover_page(
    user_name: str,
    birth_date: str,
    birth_time: str | None,
    birth_city: str,
    sun_sign: str,
    moon_sign: str,
    asc_sign: str | None,
) -> str:
    birth_bits = " · ".join(bit for bit in (_format_birth_date(birth_date), birth_time) if bit)
    points = [
        ("☉", "СОЛНЦЕ", _sign_ru(sun_sign)),
        ("☽", "ЛУНА", _sign_ru(moon_sign)),
        ("↑", "ВОСХОД", _sign_ru(asc_sign)),
    ]
    return _page(
        1,
        '<div class="mark">✦</div><h1>Натальная карта</h1>'
        '<div class="cover-subtitle">Персональный астрологический отчёт</div>'
        f'<div class="cover-name">{_e(user_name)}</div>'
        f'<div class="cover-meta">{_e(birth_bits)}<br>{_e(birth_city)}</div>'
        '<div class="cover-points">'
        + "".join(
            f'<div class="cover-point"><div class="glyph">{glyph}</div><div class="label">{label}</div><div class="value">{_e(value)}</div></div>'
            for glyph, label, value in points
        )
        + '</div><div class="cover-line"></div>'
        f'<div class="cover-foot">ASTRO TMA · MADE FOR {_e(user_name).upper()}</div>',
        class_name="cover",
    )


def _key_points_page(
    planets: dict[str, dict[str, Any]],
    sun_sign: str,
    moon_sign: str,
    asc_sign: str | None,
    descriptions: dict[str, Any] | None,
) -> str:
    planet_desc = (descriptions or {}).get("planets") or {}
    dominant = _dominant_element(planets)
    dominant_label = ELEMENTS[dominant][0]
    dominant_pct = _element_percentages(planets).get(dominant, 0)
    data = [
        (
            "sun",
            "☉",
            "СОЛНЦЕ",
            sun_sign,
            "«Как я сияю»",
            _card_blurb(
                planet_desc.get("sun"),
                _planet_fallback("sun", planets.get("sun", {"sign": sun_sign})),
            ),
        ),
        (
            "moon",
            "☽",
            "ЛУНА",
            moon_sign,
            "«Что я чувствую»",
            _card_blurb(
                planet_desc.get("moon"),
                _planet_fallback("moon", planets.get("moon", {"sign": moon_sign})),
            ),
        ),
        (
            "asc",
            "↑",
            "ВОСХОД",
            asc_sign,
            "«Как меня видят»",
            f"Восходящий знак {_sign_ru(asc_sign)} показывает первое впечатление, стиль реакции и внешний ритм.",
        ),
    ]
    body = _section_header("Ключевые точки", "Три центра, через которые читается ваша карта")
    body += (
        '<div class="cards-3">'
        + "".join(
            f'<article class="card key-card"><div class="card-icon">{glyph}</div><div class="card-meta">{label}</div>'
            f'<div class="zodiac-dot" style="background:{ELEMENT_COLORS[_sign_element(sign)]}">{_sign_symbol(sign)}</div>'
            f'<h3>{_e(_sign_ru(sign))}</h3><div class="mini-rule"></div><div class="quote">{quote}</div><p>{_e(text)}</p></article>'
            for _key_name, glyph, label, sign, quote, text in data
        )
        + "</div>"
    )
    body += (
        f'<article class="card dominant-card" style="--element-color:{ELEMENT_COLORS[dominant]}">'
        f'<div class="dominant-symbol">{ELEMENT_SYMBOLS.get(dominant, "△")}</div><div><h3>Доминирует {dominant_label.lower()}</h3>'
        f'<div class="card-meta">{dominant_pct}% карты</div><p>{_e(ELEMENT_COPY[dominant][0])}</p></div></article>'
    )
    return _page(3, body)


def _wheel_page(
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    asc_sign: str | None,
    wheel_svg: str | None = None,
) -> str:
    legend = [
        ("conjunction", "Соединение · слияние"),
        ("trine", "Трин · поток"),
        ("sextile", "Секстиль · возможность"),
        ("square", "Квадрат · вызов"),
        ("opposition", "Оппозиция · противостояние"),
        ("quincunx", "Квинконс · пересборка"),
    ]
    body = _section_header("Натальное колесо", "Карта неба в момент вашего рождения")
    wheel_markup = wheel_svg if wheel_svg else _natal_wheel_svg(planets, houses, aspects, asc_sign)
    body += f'<div class="wheel-wrap">{wheel_markup}</div>'
    body += (
        '<div class="legend">'
        + "".join(
            f'<div style="color:{ASPECT_COLORS[k]}"><span class="legend-line"></span>{_e(label)}</div>'
            for k, label in legend
        )
        + "</div>"
    )
    return _page(4, body)


_ZERO_ELEMENT_TEXTS: dict[str, str] = {
    "fire": (
        "Огонь (0%) — отсутствующая стихия. Ни одна планета не стоит в Овне, Льве или Стрельце. "
        "Инициатива, энтузиазм и спонтанное действие даются с усилием или через других людей. "
        "Задача: научиться доверять собственным импульсам, не дожидаясь внешнего разрешения."
    ),
    "earth": (
        "Земля (0%) — отсутствующая стихия. Ни одна планета не стоит в Тельце, Деве или Козероге. "
        "Материальность, практичность и стабильность не приходят автоматически — требуют сознательного внимания. "
        "Задача: выстроить конкретные структуры в быту и финансах, не полагаясь только на интуицию."
    ),
    "air": (
        "Воздух (0%) — отсутствующая стихия. Ни одна планета не стоит в Близнецах, Весах или Водолее. "
        "Абстрактное мышление, лёгкая коммуникация и дистанцирование от чувств даются труднее. "
        "Задача: развивать навык называть происходящее словами и смотреть на ситуацию с рационального расстояния."
    ),
    "water": (
        "Вода (0%) — отсутствующая стихия. Ни одна планета не стоит в Раке, Скорпионе или Рыбах. "
        "Глубокие чувства, интуиция и эмпатия не проявляются сами по себе — они требуют усилия. "
        "Задача: позволить себе чувствовать без немедленного объяснения и контроля."
    ),
}


def _elements_page(planets: dict[str, dict[str, Any]]) -> str:
    percentages = _element_percentages(planets)
    dominant = _dominant_element(planets)
    zero_elements = [el for el in ELEMENTS if percentages.get(el, 0) == 0]
    body = _section_header("Баланс стихий", "Как распределена энергия вашей карты")
    body += '<div class="elements-layout">'
    body += _donut_svg(percentages, dominant)
    body += (
        '<div class="element-list">'
        + "".join(
            f'<div class="element-row" style="--element-color:{ELEMENT_COLORS[element]}"><span class="swatch"></span>'
            f'<span>{_e(ELEMENTS[element][0])}</span><span class="percent">{percentages.get(element, 0)}%</span></div>'
            for element in ELEMENTS
        )
        + "</div></div>"
    )
    body += (
        '<div class="grid-2 element-cards">'
        + "".join(
            f'<article class="card element-card" style="--element-color:{ELEMENT_COLORS[element]}"><h3>{_e(ELEMENTS[element][0])}'
            f'<span class="percent" style="float:right">{percentages.get(element, 0)}%</span></h3><p>{_e(ELEMENT_COPY[element][0])}</p></article>'
            for element in ELEMENTS
        )
        + "</div>"
    )
    body += (
        '<div class="tags">'
        + "".join(f'<span class="tag">{_e(tag)}</span>' for tag in ELEMENT_COPY[dominant][1])
        + "</div>"
    )
    if zero_elements:
        body += '<div class="zero-elements">'
        for el in zero_elements:
            text = _ZERO_ELEMENT_TEXTS.get(el, "")
            color = ELEMENT_COLORS[el]
            body += (
                f'<article class="card zero-element-card" style="border-left:3px solid {color}">'
                f'<h3 style="color:{color}">⚠ {_e(ELEMENTS[el][0])} — отсутствующая стихия</h3>'
                f"<p>{_e(text)}</p></article>"
            )
        body += "</div>"
    return _page(5, body)


class _SectionItem:
    """A packable card. `group`/`group_open`/`group_close` let cards that share a
    visual wrapper (aspect groups) re-open that wrapper at the top of each page."""

    __slots__ = ("html", "group", "group_open", "group_close", "wrap_open", "wrap_close")

    def __init__(
        self,
        html: str,
        *,
        group: str | None = None,
        group_open: str = "",
        group_close: str = "",
        wrap_open: str = "",
        wrap_close: str = "",
    ) -> None:
        self.html = html
        self.group = group
        self.group_open = group_open
        self.group_close = group_close
        self.wrap_open = wrap_open  # per-page container (e.g. .houses-grid)
        self.wrap_close = wrap_close


class _Section:
    """Title/subtitle + a flat list of packable items, plus optional prefix HTML
    (aspect metrics) shown only on the section's first page."""

    __slots__ = ("title", "subtitle", "items", "prefix_html")

    def __init__(
        self, title: str, subtitle: str, items: list[_SectionItem], prefix_html: str = ""
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.items = items
        self.prefix_html = prefix_html


def _render_section_page(
    section: _Section, items: list[_SectionItem], *, page_index: int, sub_idx: int, sub_total: int
) -> str:
    """Render one page of a section from a slice of its items, restoring any
    group / wrapper containers so cards keep their visual chrome per page."""
    body = _section_header(section.title, section.subtitle, f"{sub_idx} / {sub_total}")
    if sub_idx == 1 and section.prefix_html:
        body += section.prefix_html
    cur_wrap: str | None = None
    cur_wrap_close = ""
    cur_group: str | None = None
    cur_group_close = ""
    for item in items:
        if item.wrap_open != (cur_wrap or ""):
            if cur_group is not None:
                body += cur_group_close
                cur_group = None
            if cur_wrap is not None:
                body += cur_wrap_close
            cur_wrap = item.wrap_open or None
            cur_wrap_close = item.wrap_close
            if cur_wrap:
                body += cur_wrap
        if item.group != cur_group:
            if cur_group is not None:
                body += cur_group_close
            cur_group = item.group
            cur_group_close = item.group_close
            if cur_group is not None:
                body += item.group_open
        body += item.html
    if cur_group is not None:
        body += cur_group_close
    if cur_wrap is not None:
        body += cur_wrap_close
    return _page(page_index, body)


def _planet_section(
    planets: dict[str, dict[str, Any]], descriptions: dict[str, Any] | None
) -> _Section:
    planet_desc = (descriptions or {}).get("planets") or {}
    names = [name for name in PLANET_ORDER if planets.get(name)]
    items: list[_SectionItem] = []
    for name in names:
        planet = planets[name]
        desc = _full_description(planet_desc.get(name), _planet_fallback(name, planet))
        sign = planet.get("sign_ru") or planet.get("sign")
        retro = '<span class="retro">℞ РЕТРО</span>' if planet.get("retrograde") else ""
        meta = f"{_roman(int(planet.get('house') or 0))} дом · {_deg_str(planet.get('sign_degree', planet.get('degree', 0)))}"
        icon = f'<span style="color:{PLANET_COLORS.get(name, GOLD)}">{PLANET_SYMBOLS.get(name, "")}</span>'
        for chunk_index, text_chunk in enumerate(_split_words(desc, 520) or [desc]):
            continuation_cls = " continuation" if chunk_index else ""
            card = _card(
                f"{PLANET_RU[name]} в {_sign_ru(sign)} {retro}",
                _e(text_chunk),
                class_name=f"planet-card detail-card{continuation_cls}",
                meta=meta,
                icon=icon,
            )
            items.append(_SectionItem(card))
    return _Section("Планеты в знаках", "Где находится каждая планета и что это значит", items)


def _houses_section(houses: list[dict[str, Any]], descriptions: dict[str, Any] | None) -> _Section:
    house_desc = (descriptions or {}).get("houses") or {}
    axis = {1: "Асцендент", 4: "Основание (IC)", 7: "Десцендент", 10: "Середина неба (MC)"}
    house_items = [house for house in houses if int(house.get("number") or 0)]
    items: list[_SectionItem] = []
    for house in house_items:
        desc = _full_description(
            house_desc.get(str(int(house.get("number") or 0))), _house_fallback(house)
        )
        num = int(house.get("number") or 0)
        sign = house.get("sign_ru") or house.get("sign")
        angle_cls = " angle" if num in axis else ""
        axis_html = (
            f'<span class="house-axis" style="color:{GOLD}">{axis[num]} · </span>'
            if num in axis
            else ""
        )
        head = (
            f'<div class="house-top"><div class="house-head">'
            f'<span class="house-num">{_roman(num)}</span><span class="house-sign">{_sign_symbol(sign)} {_e(_sign_ru(sign))}</span>'
            f'<span class="house-label">{axis_html}{_e(HOUSE_LABELS.get(num, f"ДОМ {num}"))}</span></div>'
            f'<div class="house-degree">{_deg_str(house.get("degree"), within_sign=False)}</div></div>'
        )
        for chunk_index, text_chunk in enumerate(_split_words(desc, 330) or [desc]):
            continuation_cls = " continuation" if chunk_index else ""
            card = (
                f'<article class="card house-card detail-card{angle_cls}{continuation_cls}">'
                f"{head}<p>{_e(text_chunk)}</p></article>"
            )
            items.append(
                _SectionItem(card, wrap_open='<div class="houses-grid">', wrap_close="</div>")
            )
    return _Section("Дома гороскопа", "12 сфер жизни и их обстановка", items)


def _aspect_hidden(
    aspect: dict[str, Any], aspect_desc: dict[tuple[str, str, str], dict[str, Any]]
) -> bool:
    """Аспект помечен на скрытие, если его LLM-описание оказалось заглушкой
    (флаг ``hide`` ставит пайплайн генерации). Лучше показать меньше аспектов,
    чем разбавлять отчёт болванками."""
    p1 = _planet_key(aspect.get("p1"))
    p2 = _planet_key(aspect.get("p2"))
    atype = _aspect_key(aspect.get("aspect"))
    entry = aspect_desc.get((p1, p2, atype))
    return bool(entry and entry.get("hide"))


def _aspect_described(
    aspect: dict[str, Any],
    aspect_desc: dict[tuple[str, str, str], dict[str, Any]],
) -> bool:
    """Есть ли для аспекта персональный текст (непустой full). Если нет —
    аспект не рендерим вообще, чтобы не подставлять шаблонный _aspect_fallback
    (шаблоны в платном PDF не показываем)."""
    p1 = _planet_key(aspect.get("p1"))
    p2 = _planet_key(aspect.get("p2"))
    atype = _aspect_key(aspect.get("aspect"))
    entry = aspect_desc.get((p1, p2, atype))
    return bool(entry and str(entry.get("full") or "").strip())


def _aspect_section(aspects: list[dict[str, Any]], descriptions: dict[str, Any] | None) -> _Section:
    aspect_desc = _aspect_description_map(descriptions)
    # Показываем только аспекты с готовым персональным текстом и не скрытые.
    aspects = [
        a
        for a in aspects
        if not _aspect_hidden(a, aspect_desc) and _aspect_described(a, aspect_desc)
    ]
    groups = [
        (atype, [a for a in aspects if _aspect_key(a.get("aspect")) == atype])
        for atype in ASPECT_ORDER
    ]
    groups = [(atype, group) for atype, group in groups if group]
    total = sum(len(group) for _, group in groups)
    harm = sum(1 for a in aspects if _aspect_key(a.get("aspect")) in ("trine", "sextile"))
    chall = sum(1 for a in aspects if _aspect_key(a.get("aspect")) in ("square", "opposition"))
    neutral = max(total - harm - chall, 0)
    metric_html = (
        '<div class="metrics">'
        f'<div class="metric"><strong>{total}</strong><span>Всего</span></div>'
        f'<div class="metric" style="--metric-color:#1fa37c"><strong>{harm}</strong><span>Гармоничных</span></div>'
        f'<div class="metric" style="--metric-color:#f0673c"><strong>{chall}</strong><span>Напряжённых</span></div>'
        f'<div class="metric" style="--metric-color:{TEXT_DIM}"><strong>{neutral}</strong><span>Нейтральных</span></div>'
        "</div>"
    )
    if not groups:
        empty = _SectionItem(
            '<article class="card detail-card"><h3>Основных аспектов не найдено</h3>'
            '<div class="mini-rule"></div>'
            "<p>В карте нет основных аспектов из текущего набора расчёта. Остальные разделы отчёта можно читать как главные акценты натальной карты: планеты, знаки и дома покажут основной рисунок характера.</p></article>"
        )
        return _Section(
            "Аспекты", "Связи между планетами вашей карты", [empty], prefix_html=metric_html
        )

    items: list[_SectionItem] = []
    seen_texts: set[str] = set()  # дедуп дословных дублей аспектов в платном отчёте
    for atype, group_items in groups:
        color = ASPECT_COLORS.get(atype, GOLD)
        group_open = (
            f'<section class="aspect-group" style="--aspect-color:{color}">'
            f"<h3>{ASPECT_SYMBOLS.get(atype, '')} {ASPECT_RU.get(atype, atype)} "
            f"<em>— {_e(ASPECT_TOPICS.get(atype, ''))}</em></h3>"
        )
        for aspect in group_items:
            p1 = _planet_key(aspect.get("p1"))
            p2 = _planet_key(aspect.get("p2"))
            desc = _full_description(aspect_desc.get((p1, p2, atype)), _aspect_fallback(aspect))
            # Дедуп: если текст дословно совпал с уже отрисованным — заменяем на
            # параметризованную заглушку (всегда уникальна по паре планет).
            norm = " ".join(desc.split()).lower()
            if norm in seen_texts:
                log.warning("natal_pdf_html.aspect_text_duplicate", p1=p1, p2=p2, aspect=atype)
                desc = _aspect_fallback(aspect)
                norm = " ".join(desc.split()).lower()
            seen_texts.add(norm)
            for chunk_index, text_chunk in enumerate(_split_words(desc, 260) or [desc]):
                continuation_label = " · продолжение" if chunk_index else ""
                row = (
                    f'<div class="aspect-row detail-card"><div class="aspect-title"><span class="aspect-name">{PLANET_SYMBOLS.get(p1, "")} {_e(PLANET_RU.get(p1, p1))} '
                    f"{ASPECT_SYMBOLS.get(atype, '')} {PLANET_SYMBOLS.get(p2, '')} {_e(PLANET_RU.get(p2, p2))}{continuation_label}</span>"
                    f'<span class="orb">орб {float(aspect.get("orb") or 0):.1f}°</span></div><p>{_e(text_chunk)}</p></div>'
                )
                items.append(
                    _SectionItem(row, group=atype, group_open=group_open, group_close="</section>")
                )
    return _Section("Аспекты", "Связи между планетами вашей карты", items, prefix_html=metric_html)


def _reading_pages(
    reading: str | None,
    sun_sign: str,
    moon_sign: str,
    asc_sign: str | None,
    *,
    start_page: int = 11,
) -> list[str]:
    text = str(reading or "").strip()
    if not text:
        text = (
            f"**Ядро личности**\nВаша карта соединяет Солнце в {_sign_ru(sun_sign)}, Луну в {_sign_ru(moon_sign)}"
            f"{' и восходящий знак ' + _sign_ru(asc_sign) if asc_sign else ''}. Это сочетание показывает главный рисунок характера, эмоциональные потребности и то, как вас считывают другие.\n\n"
            "**Совет и путь**\nЧитайте отчёт как карту внимания: он не фиксирует судьбу, а помогает увидеть сильные стороны, зоны роста и темы, с которыми стоит обращаться осознанно."
        )
    blocks: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("**") and line.endswith("**"):
            if current_title or current_lines:
                blocks.append((current_title, " ".join(current_lines)))
            current_title = line.strip("* ")
            current_lines = []
        else:
            current_lines.append(line)
    if current_title or current_lines:
        blocks.append((current_title or "Персональная интерпретация", " ".join(current_lines)))
    expanded_blocks: list[tuple[str, str]] = []
    for title, paragraph in blocks:
        chunks = _split_words(paragraph, 340)
        if not chunks:
            continue
        expanded_blocks.append((title, chunks[0]))
        expanded_blocks.extend((f"{title} · продолжение", chunk) for chunk in chunks[1:])

    page_chunks: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    current_words = 0
    limits = [300, 380]
    for title, paragraph in expanded_blocks:
        block_words = _word_count(paragraph) + 10
        limit = limits[min(len(page_chunks), len(limits) - 1)]
        if current and current_words + block_words > limit:
            page_chunks.append(current)
            current = []
            current_words = 0
        current.append((title, paragraph))
        current_words += block_words
    if current:
        page_chunks.append(current)

    pages = []
    for idx, chunk in enumerate(page_chunks, start=start_page):
        if not chunk:
            continue
        body = _section_header("Персональная интерпретация", "Написано специально для вас")
        if idx == start_page:
            body += '<div class="reading-quote">«Каждый рисунок звёзд раскрывается только через того, кто его носит»</div>'
        body += (
            '<div class="reading">'
            + "".join(f"<h3>✦ {_e(title)}</h3><p>{_e(paragraph)}</p>" for title, paragraph in chunk)
            + "</div>"
        )
        pages.append(_page(idx, body))
    return pages


def _final_page(page: int) -> str:
    glyph_map = {
        "Планета": "☉",
        "Знак зодиака": "♈",
        "Дом": "⌂",
        "Аспект": "△",
        "Асцендент": "↑",
        "Ретроградность": "℞",
    }
    body = (
        '<div class="final-hero">'
        '<div class="mark">✦</div>'
        '<div class="final-copy">Этот отчёт создан для вашего понимания<br>личного космического рисунка.</div>'
        '<div class="cover-line"></div>'
        "</div>"
        '<div class="glossary-title">Краткий справочник</div>'
        '<div class="glossary-grid">'
    )
    for term, definition in GLOSSARY:
        glyph = glyph_map.get(term, "✦")
        body += (
            '<article class="glossary-card">'
            f'<div class="glossary-glyph">{glyph}</div>'
            f"<h3>{_e(term)}</h3>"
            '<div class="mini-rule"></div>'
            f"<p>{_e(definition)}</p>"
            "</article>"
        )
    body += '</div><div class="cover-foot">ASTRO TMA · СОЗДАНО ДЛЯ ВАС</div>'
    return _page(page, body, class_name="final")


# Usable content height of one .page in CSS px at the 794×1123 viewport:
# page is 297mm tall with 22mm top + 17mm bottom padding → 258mm of content.
# 1123px == 297mm ⇒ 258mm ≈ 975px. Keep a small safety margin.
_PAGE_CONTENT_PX = 1090
# Approx px height the section header (title + rule) eats on a section's pages.
_SECTION_HEAD_PX = 96


def _pack_section_by_words(section: _Section) -> list[list[_SectionItem]]:
    """Word-count fallback packing (used when measured heights are unavailable,
    e.g. in unit tests). Mirrors the old per-section budgets loosely."""
    if not section.items:
        return [[]]
    pages: list[list[_SectionItem]] = []
    current: list[_SectionItem] = []
    weight = 0
    for item in section.items:
        words = _word_count(item.html)
        cost = words + 14  # card chrome
        budget = 360 if not pages else 470
        if current and weight + cost > budget:
            pages.append(current)
            current = []
            weight = 0
        current.append(item)
        weight += cost
    if current:
        pages.append(current)
    return pages


def _assemble_natal_html(
    *,
    user_name: str,
    birth_date: str,
    birth_time: str | None,
    birth_city: str,
    sun_sign: str,
    moon_sign: str,
    asc_sign: str | None,
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    reading: str | None,
    descriptions: dict[str, Any] | None,
    wheel_svg: str | None,
    planet_split: list[list[_SectionItem]],
    house_split: list[list[_SectionItem]],
    aspect_split: list[list[_SectionItem]],
) -> str:
    planet_sec = _planet_section(planets, descriptions)
    house_sec = _houses_section(houses, descriptions)
    aspect_sec = _aspect_section(aspects, descriptions)

    planets_page = 6
    planet_pages = [
        _render_section_page(
            planet_sec,
            chunk,
            page_index=planets_page + i,
            sub_idx=i + 1,
            sub_total=len(planet_split),
        )
        for i, chunk in enumerate(planet_split)
    ]
    houses_start = planets_page + len(planet_pages)
    house_pages = [
        _render_section_page(
            house_sec, chunk, page_index=houses_start + i, sub_idx=i + 1, sub_total=len(house_split)
        )
        for i, chunk in enumerate(house_split)
    ]
    aspects_start = houses_start + len(house_pages)
    aspect_pages = [
        _render_section_page(
            aspect_sec,
            chunk,
            page_index=aspects_start + i,
            sub_idx=i + 1,
            sub_total=len(aspect_split),
        )
        for i, chunk in enumerate(aspect_split)
    ]
    reading_start = aspects_start + len(aspect_pages)
    pages = [
        _cover_page(user_name, birth_date, birth_time, birth_city, sun_sign, moon_sign, asc_sign),
        _content_page(
            planets_page=planets_page,
            houses_page=houses_start,
            aspects_page=aspects_start,
            reading_page=reading_start,
        ),
        _key_points_page(planets, sun_sign, moon_sign, asc_sign, descriptions),
        _wheel_page(planets, houses, aspects, asc_sign, wheel_svg=wheel_svg),
        _elements_page(planets),
        *planet_pages,
        *house_pages,
        *aspect_pages,
        *_reading_pages(reading, sun_sign, moon_sign, asc_sign, start_page=reading_start),
    ]
    pages.append(_final_page(len(pages) + 1))
    body = "".join(pages).replace(TOTAL_PAGES_TOKEN, str(len(pages)))
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{_css()}</style></head><body>{body}</body></html>"


def build_natal_pdf_html(
    user_name: str,
    birth_date: str,
    birth_time: str | None,
    birth_city: str,
    sun_sign: str,
    moon_sign: str,
    asc_sign: str | None,
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    reading: str | None = None,
    descriptions: dict[str, Any] | None = None,
    wheel_svg: str | None = None,
) -> str:
    """Synchronous build with word-count packing (fallback / tests). The async
    renderer uses measured heights for tighter, overflow-free packing."""
    return _assemble_natal_html(
        user_name=user_name,
        birth_date=birth_date,
        birth_time=birth_time,
        birth_city=birth_city,
        sun_sign=sun_sign,
        moon_sign=moon_sign,
        asc_sign=asc_sign,
        planets=planets,
        houses=houses,
        aspects=aspects,
        reading=reading,
        descriptions=descriptions,
        wheel_svg=wheel_svg,
        planet_split=_pack_section_by_words(_planet_section(planets, descriptions)),
        house_split=_pack_section_by_words(_houses_section(houses, descriptions)),
        aspect_split=_pack_section_by_words(_aspect_section(aspects, descriptions)),
    )


def _measure_doc(sections: list[_Section]) -> str:
    """A standalone HTML whose body lays out every packable item inside a
    page-width column, each tagged ``data-mid`` so we can read its rendered
    height in the browser. Group/grid wrappers are included so width-dependent
    reflow matches the real layout."""
    blocks: list[str] = []
    mid = 0
    for s_idx, section in enumerate(sections):
        for item in section.items:
            wrap_o = item.wrap_open or ""
            wrap_c = item.wrap_close or ""
            grp_o = item.group_open or ""
            grp_c = item.group_close or ""
            blocks.append(
                f'<div class="page measure" data-mid="{s_idx}:{mid}">'
                f"{wrap_o}{grp_o}{item.html}{grp_c}{wrap_c}</div>"
            )
            mid += 1
        mid = 0
    extra = (
        ".measure{{height:auto !important;overflow:visible !important;"
        "break-after:auto !important;page-break-after:auto !important;}}"
    )
    body = "".join(blocks)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{_css()}{extra}</style></head><body>{body}</body></html>"
    )


def _pack_section_by_heights(
    section: _Section, heights: list[float], *, gap: float = 11.0
) -> list[list[_SectionItem]]:
    """Greedily fill pages so the summed measured item heights (plus a small
    inter-item gap and a group-header allowance) stay under the page budget.
    Overflow is impossible: an item only starts a new page when it doesn't fit."""
    if not section.items:
        return [[]]
    pages: list[list[_SectionItem]] = []
    current: list[_SectionItem] = []
    used = 0.0
    prefix_px = 96.0 if section.prefix_html else 0.0  # metrics block on first page
    prev_group: str | None = "<<none>>"
    for item, h in zip(section.items, heights):
        # every section page carries the header; the section's first page also
        # carries the prefix (aspect metrics).
        budget = _PAGE_CONTENT_PX - _SECTION_HEAD_PX - (prefix_px if not pages else 0.0)
        # group header re-emitted at the top of a page or on group change
        group_cost = 34.0 if item.group is not None and item.group != prev_group else 0.0
        cost = h + (gap if current else 0.0) + group_cost
        if current and used + cost > budget:
            pages.append(current)
            current = []
            used = 0.0
            prev_group = "<<none>>"
            group_cost = 34.0 if item.group is not None else 0.0
            cost = h + group_cost
        current.append(item)
        used += cost
        prev_group = item.group
    if current:
        pages.append(current)
    return pages


async def generate_natal_pdf_html(
    user_name: str,
    birth_date: str,
    birth_time: str | None,
    birth_city: str,
    sun_sign: str,
    moon_sign: str,
    asc_sign: str | None,
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    reading: str | None = None,
    descriptions: dict[str, Any] | None = None,
    wheel_svg: str | None = None,
) -> bytes:
    from playwright.async_api import async_playwright

    from services.playwright_pool import pdf_semaphore

    planet_sec = _planet_section(planets, descriptions)
    house_sec = _houses_section(houses, descriptions)
    aspect_sec = _aspect_section(aspects, descriptions)
    sections = [planet_sec, house_sec, aspect_sec]
    log.info(
        "natal.pdf_html_render_start",
        has_wheel_svg=bool(wheel_svg),
        has_descriptions=bool(
            descriptions
            and (
                descriptions.get("planets")
                or descriptions.get("houses")
                or descriptions.get("aspects")
            )
        ),
        has_reading=bool(reading and reading.strip()),
    )
    started = time.monotonic()
    stage = "acquire_semaphore"
    async with pdf_semaphore:
        try:
            stage = "playwright_start"
            async with async_playwright() as p:
                stage = "chromium_launch"
                browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
                try:
                    stage = "new_page"
                    page = await browser.new_page(
                        viewport={"width": 794, "height": 1123}, device_scale_factor=1
                    )
                    # ── Phase 1: measure item heights for height-based packing ──
                    stage = "measure"
                    try:
                        await page.set_content(_measure_doc(sections), wait_until="load")
                        raw = await page.evaluate(
                            """() => {
                                const out = {};
                                document.querySelectorAll('[data-mid]').forEach(el => {
                                    out[el.getAttribute('data-mid')] =
                                        el.firstElementChild
                                            ? el.firstElementChild.getBoundingClientRect().height
                                            : el.getBoundingClientRect().height;
                                });
                                return out;
                            }"""
                        )
                        per_section: list[list[float]] = [[] for _ in sections]
                        for key, h in raw.items():
                            s_idx, _mid = key.split(":")
                            per_section[int(s_idx)].append(float(h))
                        planet_split = _pack_section_by_heights(planet_sec, per_section[0])
                        house_split = _pack_section_by_heights(house_sec, per_section[1])
                        aspect_split = _pack_section_by_heights(aspect_sec, per_section[2])
                    except Exception as me:  # noqa: BLE001
                        log.warning("natal.pdf_measure_failed_fallback", error=str(me))
                        planet_split = _pack_section_by_words(planet_sec)
                        house_split = _pack_section_by_words(house_sec)
                        aspect_split = _pack_section_by_words(aspect_sec)

                    document = _assemble_natal_html(
                        user_name=user_name,
                        birth_date=birth_date,
                        birth_time=birth_time,
                        birth_city=birth_city,
                        sun_sign=sun_sign,
                        moon_sign=moon_sign,
                        asc_sign=asc_sign,
                        planets=planets,
                        houses=houses,
                        aspects=aspects,
                        reading=reading,
                        descriptions=descriptions,
                        wheel_svg=wheel_svg,
                        planet_split=planet_split,
                        house_split=house_split,
                        aspect_split=aspect_split,
                    )
                    # ── Phase 2: render the final packed document ──
                    stage = "set_content"
                    await page.set_content(document, wait_until="load")
                    stage = "render_pdf"
                    pdf_bytes = await page.pdf(
                        format="A4",
                        print_background=True,
                        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                        prefer_css_page_size=True,
                    )
                finally:
                    await browser.close()
        except Exception as e:
            log.error(
                "natal.pdf_html_render_failed",
                stage=stage,
                error_type=type(e).__name__,
                error=str(e),
                elapsed_ms=round((time.monotonic() - started) * 1000),
                exc_info=True,
            )
            raise
    log.info(
        "natal.pdf_html_render_ok",
        pdf_bytes=len(pdf_bytes),
        elapsed_ms=round((time.monotonic() - started) * 1000),
    )
    return pdf_bytes
