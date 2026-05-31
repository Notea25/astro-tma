"""HTML/CSS Destiny Matrix PDF renderer (MVP).

Mirrors ``services.natal_pdf_html`` — builds a print-oriented HTML document
and renders it through Playwright/Chromium. No ReportLab fallback here;
the route catches exceptions and surfaces a 502 to the client.

MVP scope (per spec, see ``memory/project_destiny_matrix_pdf_v2.md`` for V2):
    * cover page (name, birth date, 3 anchor arcana)
    * contents
    * octagram (SVG, simplified projection of the React component)
    * 8 narrative sections (one per page)
    * 36-slot summary table
    * disclaimer / final page
"""

from __future__ import annotations

import html
import math
from datetime import datetime
from typing import Any

from services.destiny_matrix.arcana_names import (
    ARCANA_KEYWORDS_RU,
    ARCANA_NAMES_RU,
)
from services.destiny_matrix.interpreter import SECTION_KEYS, SECTION_LABELS_RU

# ── Palette (matches DestinyOctagram + natal PDF) ──────────────────────────

GOLD = "#d6b85a"
GOLD_DIM = "#8d7842"
BG = "#050510"
PANEL = "#100c1f"
PANEL_DARK = "#0b0714"
WHEEL_BG = "#071029"
TEXT = "#f4f0e8"
TEXT_DIM = "#a9a1bb"
BORDER = "rgba(214, 184, 90, .22)"

# Octagram-specific colours (lifted from DestinyOctagram.tsx)
COLOR_DIAMOND = "#f4d76b"
COLOR_SQUARE = "#a7c0ff"
COLOR_FAMILY_M = "#5fa8ff"   # синяя стрелка (мужская линия)
COLOR_FAMILY_F = "#ff7a92"   # красная стрелка (женская линия)
COLOR_HEART = "#ff7a92"
COLOR_DOLLAR = "#f4d76b"

TOTAL_PAGES_TOKEN = "__TOTAL_PAGES__"


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _arcana_name(num: int | None) -> str:
    if num is None:
        return ""
    return ARCANA_NAMES_RU.get(int(num), f"Аркан {num}")


def _arcana_keywords(num: int | None) -> str:
    if num is None:
        return ""
    return ", ".join(ARCANA_KEYWORDS_RU.get(int(num), []))


def _format_birth_date(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%d.%m.%Y")
    except ValueError:
        return value


def _footer(page: int, total: int | str = TOTAL_PAGES_TOKEN) -> str:
    return f'<footer>ASTRO TMA · МАТРИЦА СУДЬБЫ <span>{page} / {total}</span></footer>'


def _page(page: int, body: str, *, class_name: str = "") -> str:
    cls = f"page {class_name}".strip()
    return f'<section class="{cls}">{body}{_footer(page)}</section>'


def _section_header(title: str, subtitle: str, aside: str = "") -> str:
    aside_html = f'<div class="section-aside">{_e(aside)}</div>' if aside else ""
    return (
        f'<div class="section-head"><div><h2>{_e(title)}</h2>'
        f'<div class="rule"></div><p>{_e(subtitle)}</p></div>{aside_html}</div>'
    )


# ── CSS ─────────────────────────────────────────────────────────────────────


def _css() -> str:
    return f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; overflow-wrap: anywhere; }}
html, body {{ margin: 0; padding: 0; background: {BG}; color: {TEXT}; }}
body {{ font-family: "DejaVu Sans", Arial, sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.page {{ position: relative; display: block; width: 210mm; height: 297mm; overflow: hidden; padding: 22mm 18mm 17mm; background: {BG}; break-after: page; page-break-after: always; break-inside: avoid; }}
h1, h2, h3, .serif {{ font-family: "DejaVu Serif", Georgia, serif; font-weight: 400; }}

/* Cover */
.cover {{ display: flex; flex-direction: column; align-items: center; text-align: center; padding-top: 30mm; }}
.mark {{ color: {GOLD}; font-size: 32px; margin-bottom: 30mm; line-height: 1; }}
h1 {{ margin: 0; color: {GOLD}; font-size: 32px; letter-spacing: 6px; text-transform: uppercase; }}
.cover-subtitle {{ margin-top: 12mm; font: italic 16px "DejaVu Serif", Georgia, serif; color: {TEXT}; opacity: .92; }}
.cover-name {{ margin-top: 30mm; font: italic 21px "DejaVu Serif", Georgia, serif; }}
.cover-meta {{ margin-top: 10mm; color: {TEXT_DIM}; font-size: 13px; line-height: 1.72; }}
.cover-points {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14mm; margin-top: 8mm; width: 150mm; }}
.cover-point .num {{ color: {GOLD}; font: 26px "DejaVu Serif", Georgia, serif; }}
.cover-point .label {{ margin-top: 6mm; color: {TEXT_DIM}; font-size: 10.5px; letter-spacing: 2.5px; text-transform: uppercase; }}
.cover-point .value {{ margin-top: 4mm; font: 13px "DejaVu Serif", Georgia, serif; }}
.cover-line {{ width: 32mm; height: 1px; background: {GOLD_DIM}; margin-top: 16mm; }}
.cover-foot {{ margin-top: 8mm; color: #776f8c; font-size: 10px; letter-spacing: 3px; }}

/* Section heads */
.section-head {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8mm; }}
h2 {{ margin: 0; color: {GOLD}; font-size: 24px; letter-spacing: 4px; }}
.rule {{ height: 1px; width: 170mm; background: rgba(214,184,90,.2); margin: 6mm 0 5mm; }}
.section-head p {{ margin: 0; color: {TEXT_DIM}; font: italic 12px "DejaVu Serif", Georgia, serif; }}
.section-aside {{ color: #807894; font-size: 12px; margin-top: 5mm; }}
footer {{ position: absolute; bottom: 7mm; left: 0; right: 0; text-align: center; color: #6d6680; font-size: 10px; letter-spacing: 3px; }}
footer span {{ letter-spacing: 1px; margin-left: 8px; }}

/* TOC */
.toc-list {{ margin-top: 20mm; }}
.toc-row {{ display: grid; grid-template-columns: 12mm 1fr 14mm; align-items: center; min-height: 14mm; border-bottom: 1px solid rgba(255,255,255,.025); }}
.toc-roman {{ color: {GOLD}; font: 14px "DejaVu Serif", Georgia, serif; }}
.toc-title {{ font: 13px "DejaVu Serif", Georgia, serif; }}
.toc-page {{ color: {TEXT_DIM}; text-align: right; font-size: 13px; }}

/* Octagram page */
.octa-wrap {{ width: 168mm; height: 168mm; margin: 6mm auto 6mm; background: {BG}; display: grid; place-items: center; }}
.octa-svg {{ width: 100%; height: 100%; display: block; }}
.octa-caption {{ text-align: center; color: {TEXT_DIM}; font: italic 12px "DejaVu Serif", Georgia, serif; margin-top: 2mm; }}
.octa-anchors {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 5mm; margin-top: 8mm; }}
.octa-anchor {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 7px; padding: 5mm; text-align: center; }}
.octa-anchor .num {{ color: {GOLD}; font: 23px "DejaVu Serif", Georgia, serif; }}
.octa-anchor .label {{ color: {TEXT_DIM}; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-top: 2mm; }}
.octa-anchor .name {{ font: 12.5px "DejaVu Serif", Georgia, serif; margin-top: 2mm; }}

/* Narrative pages */
.section-card {{ background: {PANEL}; border: 1px solid {BORDER}; border-left: 3px solid {GOLD}; border-radius: 8px; padding: 8mm 8mm; }}
.section-card .anchor {{ display: flex; gap: 6mm; align-items: center; margin-bottom: 6mm; padding-bottom: 5mm; border-bottom: 1px solid rgba(214,184,90,.18); }}
.section-card .anchor .num {{ color: {GOLD}; font: 30px "DejaVu Serif", Georgia, serif; line-height: 1; }}
.section-card .anchor .name {{ font: 16px "DejaVu Serif", Georgia, serif; }}
.section-card .anchor .keywords {{ color: {TEXT_DIM}; font-size: 11px; margin-top: 1.5mm; }}
.section-card p {{ font-size: 13px; line-height: 1.55; margin: 0 0 5mm; }}
.section-card p:last-child {{ margin-bottom: 0; }}
.section-quote {{ text-align: center; color: {TEXT_DIM}; font: italic 13px "DejaVu Serif", Georgia, serif; margin: 6mm 0 8mm; }}

/* Summary table */
.summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 3mm 4mm; margin-top: 6mm; }}
.summary-cell {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 6px; padding: 3.5mm 4mm; min-height: 18mm; }}
.summary-cell .num {{ color: {GOLD}; font: 18px "DejaVu Serif", Georgia, serif; line-height: 1; }}
.summary-cell .label {{ color: {TEXT_DIM}; font-size: 9.5px; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 2mm; }}
.summary-cell .name {{ font-size: 11px; margin-top: 2mm; line-height: 1.25; }}
.summary-section {{ grid-column: 1 / -1; color: {GOLD}; font: 13px "DejaVu Serif", Georgia, serif; letter-spacing: 2px; text-transform: uppercase; margin: 4mm 0 0; }}

/* Final */
.final {{ display: flex; flex-direction: column; align-items: center; text-align: center; padding-top: 60mm; }}
.final .mark {{ margin-bottom: 18mm; }}
.final-copy {{ font: italic 15px/1.65 "DejaVu Serif", Georgia, serif; width: 130mm; color: {TEXT}; }}
.disclaimer {{ margin-top: 22mm; width: 140mm; color: {TEXT_DIM}; font-size: 11px; line-height: 1.5; text-align: left; }}
.disclaimer h3 {{ color: {GOLD}; font-size: 13px; letter-spacing: 2px; text-transform: uppercase; margin: 0 0 4mm; text-align: center; }}
"""


# ── Octagram SVG ────────────────────────────────────────────────────────────


def _ray_corner_dot(corner_xy: tuple[float, float], center_xy: tuple[float, float], t: float) -> tuple[float, float]:
    cx, cy = corner_xy
    mx, my = center_xy
    return cx + (mx - cx) * t, cy + (my - cy) * t


def _octagram_svg(positions: dict[str, Any]) -> str:
    """Project the React DestinyOctagram into static SVG.

    Geometry mirrors ``frontend/src/components/destiny/DestinyOctagram.tsx``:
    viewBox 600x600, centre (300, 300), R = 220 for personality diamond
    corners, R = 220 / sqrt(2) for ancestral square corners.
    """
    pers = positions.get("personality", {})
    sq = positions.get("ancestral_square", {})
    specials = positions.get("specials", {}) or {}
    money_diag = positions.get("money_diagonal") or []

    cx = cy = 300.0
    r_diamond = 220.0
    r_square = r_diamond * 0.78

    # Diamond corners (personality)
    top = (cx, cy - r_diamond)
    right = (cx + r_diamond, cy)
    bottom = (cx, cy + r_diamond)
    left = (cx - r_diamond, cy)
    # Square corners (ancestral)
    tl = (cx - r_square, cy - r_square)
    tr = (cx + r_square, cy - r_square)
    br = (cx + r_square, cy + r_square)
    bl = (cx - r_square, cy + r_square)

    parts: list[str] = [
        '<svg class="octa-svg" viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg">',
        # Diamond + square outlines
        f'<polygon points="{top[0]},{top[1]} {right[0]},{right[1]} {bottom[0]},{bottom[1]} {left[0]},{left[1]}" '
        f'fill="none" stroke="{COLOR_DIAMOND}" stroke-width="1.6" opacity=".85"/>',
        f'<polygon points="{tl[0]},{tl[1]} {tr[0]},{tr[1]} {br[0]},{br[1]} {bl[0]},{bl[1]}" '
        f'fill="none" stroke="{COLOR_SQUARE}" stroke-width="1.6" opacity=".85"/>',
        # Diagonal rays (corner → centre, terminating at R_INNER = 155)
    ]
    r_inner = 155.0
    for corner in (top, right, bottom, left, tl, tr, br, bl):
        dx, dy = corner[0] - cx, corner[1] - cy
        dist = math.hypot(dx, dy)
        if not dist:
            continue
        ix = cx + dx / dist * r_inner
        iy = cy + dy / dist * r_inner
        parts.append(
            f'<line x1="{corner[0]:.1f}" y1="{corner[1]:.1f}" x2="{ix:.1f}" y2="{iy:.1f}" '
            f'stroke="{GOLD_DIM}" stroke-width=".8" opacity=".55"/>'
        )

    # Family-line arrows (faint, just to hint at TL↔BR and TR↔BL diagonals)
    parts.append(
        f'<line x1="{tl[0]}" y1="{tl[1]}" x2="{br[0]}" y2="{br[1]}" '
        f'stroke="{COLOR_FAMILY_M}" stroke-width="1" opacity=".35"/>'
    )
    parts.append(
        f'<line x1="{tr[0]}" y1="{tr[1]}" x2="{bl[0]}" y2="{bl[1]}" '
        f'stroke="{COLOR_FAMILY_F}" stroke-width="1" opacity=".35"/>'
    )

    # Money diagonal (dashed): centre → BR area
    if money_diag:
        parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{br[0]:.1f}" y2="{br[1]:.1f}" '
            f'stroke="{COLOR_DOLLAR}" stroke-width="1" stroke-dasharray="4 4" opacity=".55"/>'
        )

    # Big corner nodes
    R_DOT = 26.0
    nodes = [
        (top, pers.get("month"), "Месяц"),
        (right, pers.get("year"), "Год"),
        (bottom, pers.get("bottom"), "Низ"),
        (left, pers.get("day"), "День"),
        (tl, sq.get("top_left"), "Род ↖"),
        (tr, sq.get("top_right"), "Род ↗"),
        (br, sq.get("bottom_right"), "Род ↘"),
        (bl, sq.get("bottom_left"), "Род ↙"),
    ]
    for (x, y), num, _label in nodes:
        if num is None:
            continue
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{R_DOT}" fill="{BG}" '
            f'stroke="{GOLD}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" dy="0.35em" '
            f'fill="{GOLD}" font-size="22" font-family="DejaVu Serif, Georgia, serif">{int(num)}</text>'
        )

    # Centre
    center_val = pers.get("center")
    if center_val is not None:
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{R_DOT + 4}" fill="{BG}" '
            f'stroke="{GOLD}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy}" text-anchor="middle" dy="0.35em" '
            f'fill="{GOLD}" font-size="24" font-family="DejaVu Serif, Georgia, serif">{int(center_val)}</text>'
        )

    # Mid-of-ray dots (specials.talent / character / money / love)
    R_MID = 16.0
    mid_t = 0.42  # along corner → centre, from corner
    mid_dots = [
        (top, specials.get("talent")),
        (left, specials.get("character")),
        (right, specials.get("money")),
        (bottom, specials.get("love")),
    ]
    for corner, num in mid_dots:
        if num is None:
            continue
        x, y = _ray_corner_dot(corner, (cx, cy), mid_t)
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R_MID}" fill="{BG}" '
            f'stroke="{GOLD_DIM}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dy="0.35em" '
            f'fill="{GOLD}" font-size="14" font-family="DejaVu Serif, Georgia, serif">{int(num)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


# ── Pages ──────────────────────────────────────────────────────────────────


def _cover_page(user_name: str, birth_date: str, positions: dict[str, Any]) -> str:
    pers = positions.get("personality", {})
    purposes = positions.get("purposes", {})
    points = [
        (pers.get("center"), "Центр", _arcana_name(pers.get("center"))),
        (pers.get("bottom"), "Карма", _arcana_name(pers.get("bottom"))),
        (purposes.get("personal"), "Предназн.", _arcana_name(purposes.get("personal"))),
    ]
    return _page(
        1,
        '<div class="mark">✦</div><h1>Матрица судьбы</h1>'
        '<div class="cover-subtitle">Персональный разбор по методу Ладини</div>'
        f'<div class="cover-name">{_e(user_name)}</div>'
        f'<div class="cover-meta">Дата рождения: {_e(_format_birth_date(birth_date))}</div>'
        '<div class="cover-points">'
        + "".join(
            f'<div class="cover-point"><div class="num">{int(num) if num is not None else "—"}</div>'
            f'<div class="label">{_e(label)}</div><div class="value">{_e(name)}</div></div>'
            for num, label, name in points
        )
        + '</div><div class="cover-line"></div>'
        f'<div class="cover-foot">СОЗДАНО ДЛЯ {_e(user_name).upper()}</div>',
        class_name="cover",
    )


def _contents_page(narrative_start: int, summary_page: int) -> str:
    rows = [
        ("I", "Октаграмма судьбы", "3"),
        ("II", "Кто ты — характер и центр", str(narrative_start)),
        ("III", "Кармический хвост", str(narrative_start + 1)),
        ("IV", "Таланты и вдохновение", str(narrative_start + 2)),
        ("V", "Предназначение", str(narrative_start + 3)),
        ("VI", "Отношения", str(narrative_start + 4)),
        ("VII", "Деньги и реализация", str(narrative_start + 5)),
        ("VIII", "Род и семья", str(narrative_start + 6)),
        ("IX", "Совет на этот период", str(narrative_start + 7)),
        ("X", "Сводная таблица ключевых точек", str(summary_page)),
    ]
    body = _section_header("Содержание", "Что внутри отчёта")
    body += '<div class="toc-list">' + "".join(
        f'<div class="toc-row"><div class="toc-roman">{roman}</div><div class="toc-title">{_e(title)}</div><div class="toc-page">{page}</div></div>'
        for roman, title, page in rows
    ) + "</div>"
    return _page(2, body)


def _octagram_page(positions: dict[str, Any]) -> str:
    body = _section_header(
        "Октаграмма судьбы",
        "Восемь точек личностного ромба и родового квадрата",
    )
    body += f'<div class="octa-wrap">{_octagram_svg(positions)}</div>'
    body += (
        '<div class="octa-caption">Тёплое золото — личностный ромб (день, месяц, год, '
        'кармический низ + центр). Голубой — родовой квадрат. Синяя стрелка — мужская '
        'линия, красная — женская.</div>'
    )
    pers = positions.get("personality", {})
    anchors = [
        (pers.get("center"), "Центр / характер"),
        (pers.get("bottom"), "Кармический урок"),
        (pers.get("month"), "Талант / вдохновение"),
    ]
    body += '<div class="octa-anchors">' + "".join(
        f'<div class="octa-anchor"><div class="num">{int(num) if num is not None else "—"}</div>'
        f'<div class="label">{_e(label)}</div><div class="name">{_e(_arcana_name(num))}</div></div>'
        for num, label in anchors
    ) + "</div>"
    return _page(3, body)


# Map narrative section → anchor arcana (the single number that the section
# is mostly about). Keeps the section page visually anchored.
def _section_anchor(positions: dict[str, Any], section_key: str) -> int | None:
    pers = positions.get("personality", {})
    purposes = positions.get("purposes", {})
    channels = positions.get("channels", {}) or {}
    mapping = {
        "who_you_are":   pers.get("center"),
        "karmic_tail":   pers.get("bottom"),
        "talents":       pers.get("month"),
        "purpose":       purposes.get("personal"),
        "relationships": (channels.get("relationships") or [None])[0],
        "finance":       (channels.get("finance") or [None])[0],
        "parental":      (channels.get("parental") or [None])[0],
        "advice":        pers.get("center"),
    }
    val = mapping.get(section_key)
    return int(val) if isinstance(val, int) else None


SECTION_QUOTES_RU = {
    "who_you_are":   "Характер — это не приговор, а способ дышать.",
    "karmic_tail":   "Урок повторяется, пока не научишься выбирать иначе.",
    "talents":       "Талант — там, где тебе становится легко быть собой.",
    "purpose":       "Предназначение — это направление, а не пункт назначения.",
    "relationships": "Мы притягиваем не тех, кого хотим, а тех, кому равны.",
    "finance":       "Деньги — это форма, в которой энергия возвращается обратно.",
    "parental":      "Род лечится через одного — того, кто решился увидеть.",
    "advice":        "Один шаг честно — лучше десяти, сделанных «правильно».",
}


def _narrative_page(
    page: int,
    section_key: str,
    section_text: str,
    positions: dict[str, Any],
) -> str:
    label = SECTION_LABELS_RU.get(section_key, section_key)
    anchor_num = _section_anchor(positions, section_key)
    anchor_html = ""
    if anchor_num is not None:
        anchor_html = (
            '<div class="anchor">'
            f'<div class="num">{anchor_num}</div>'
            f'<div><div class="name">{_e(_arcana_name(anchor_num))}</div>'
            f'<div class="keywords">{_e(_arcana_keywords(anchor_num))}</div></div></div>'
        )
    body = _section_header(label, "Личный разбор", aside=f"{section_key.replace('_', ' ').title()}")
    body += f'<div class="section-quote">«{_e(SECTION_QUOTES_RU.get(section_key, ""))}»</div>'
    body += '<div class="section-card">' + anchor_html
    # Split the LLM text into paragraphs on blank lines / single newlines.
    paragraphs: list[str] = []
    current: list[str] = []
    for raw in (section_text or "").splitlines():
        line = raw.strip()
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    if not paragraphs:
        paragraphs = [
            "Подробный текст этого раздела появится после обновления контента. "
            "Числа арканов уже рассчитаны и видны на октаграмме."
        ]
    body += "".join(f'<p>{_e(p)}</p>' for p in paragraphs)
    body += "</div>"
    return _page(page, body)


def _summary_page(page: int, positions: dict[str, Any]) -> str:
    pers = positions.get("personality", {}) or {}
    sq = positions.get("ancestral_square", {}) or {}
    lines = positions.get("lines", {}) or {}
    purposes = positions.get("purposes", {}) or {}
    channels = positions.get("channels", {}) or {}
    specials = positions.get("specials", {}) or {}

    body = _section_header("Сводная таблица", "Ключевые точки матрицы — 36 чисел в одном месте")
    body += '<div class="summary-grid">'

    def cells(items: list[tuple[Any, str]]) -> str:
        out: list[str] = []
        for num, label in items:
            if num is None:
                continue
            out.append(
                f'<div class="summary-cell"><div class="num">{int(num)}</div>'
                f'<div class="label">{_e(label)}</div>'
                f'<div class="name">{_e(_arcana_name(num))}</div></div>'
            )
        return "".join(out)

    sections: list[tuple[str, list[tuple[Any, str]]]] = [
        ("Личностный ромб", [
            (pers.get("day"), "День"),
            (pers.get("month"), "Месяц"),
            (pers.get("year"), "Год"),
            (pers.get("bottom"), "Низ / карма"),
            (pers.get("center"), "Центр"),
        ]),
        ("Родовой квадрат", [
            (sq.get("top_left"), "Род ↖"),
            (sq.get("top_right"), "Род ↗"),
            (sq.get("bottom_right"), "Род ↘"),
            (sq.get("bottom_left"), "Род ↙"),
        ]),
        ("Линии", [
            (lines.get("sky"), "Небо"),
            (lines.get("earth"), "Земля"),
            (lines.get("father"), "Отец"),
            (lines.get("mother"), "Мать"),
        ]),
        ("Предназначения", [
            (purposes.get("personal"), "До 40"),
            (purposes.get("social"), "40–60"),
            (purposes.get("spiritual"), "После 60"),
            (purposes.get("planetary"), "Миссия"),
        ]),
        ("Семантические точки", [
            (specials.get("talent"), "Талант"),
            (specials.get("character"), "Характер"),
            (specials.get("money"), "Деньги"),
            (specials.get("love"), "Любовь"),
            (specials.get("cross"), "Крест"),
        ]),
        ("Каналы — итоговая точка", [
            ((channels.get("karmic_tail") or [None] * 3)[-1], "Кармический"),
            ((channels.get("talents") or [None] * 3)[-1], "Талантов"),
            ((channels.get("relationships") or [None] * 3)[-1], "Отношений"),
            ((channels.get("finance") or [None] * 3)[-1], "Финансов"),
            ((channels.get("material_karma") or [None] * 3)[-1], "Мат. карма"),
            ((channels.get("parental") or [None] * 3)[-1], "Род.-дет."),
        ]),
    ]

    for title, items in sections:
        body += f'<div class="summary-section">{_e(title)}</div>'
        body += cells(items)

    body += "</div>"
    return _page(page, body)


def _final_page(page: int) -> str:
    body = (
        '<div class="mark">✦</div>'
        '<div class="final-copy">Матрица — не приговор и не предсказание. '
        'Это карта твоих сильных сторон, повторяющихся уроков и точек роста, '
        'к которой полезно возвращаться раз в несколько месяцев.</div>'
        '<div class="disclaimer">'
        '<h3>Важно понимать</h3>'
        '<p>Отчёт носит информационно-просветительский характер и не заменяет '
        'консультаций с врачом, психологом, юристом или финансовым советником. '
        'Решения о здоровье, деньгах и отношениях принимай, опираясь на свой '
        'опыт и здравый смысл — матрица только подсветит то, на что стоит '
        'обратить внимание.</p>'
        '<p>Авторская методика расчёта — Лариса Ладини. Авторские названия '
        'арканов взяты из книги «Матрица судьбы от А до Я».</p>'
        '</div>'
        '<div class="cover-foot">ASTRO TMA · СОЗДАНО ДЛЯ ТЕБЯ</div>'
    )
    return _page(page, body, class_name="final")


# ── Public API ──────────────────────────────────────────────────────────────


def build_destiny_matrix_pdf_html(
    user_name: str,
    birth_date: str,
    positions: dict[str, Any],
    sections: dict[str, str] | None,
) -> str:
    """Compose the final HTML document. Section order follows SECTION_KEYS."""
    safe_sections = sections or {}

    narrative_start = 4  # cover(1) + toc(2) + octagram(3) → first narrative is 4
    narrative_pages = [
        _narrative_page(
            narrative_start + idx,
            key,
            safe_sections.get(key, ""),
            positions,
        )
        for idx, key in enumerate(SECTION_KEYS)
    ]
    summary_page_num = narrative_start + len(SECTION_KEYS)
    final_page_num = summary_page_num + 1

    pages = [
        _cover_page(user_name, birth_date, positions),
        _contents_page(narrative_start, summary_page_num),
        _octagram_page(positions),
        *narrative_pages,
        _summary_page(summary_page_num, positions),
        _final_page(final_page_num),
    ]
    body = "".join(pages).replace(TOTAL_PAGES_TOKEN, str(len(pages)))
    return (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{_css()}</style></head><body>{body}</body></html>"
    )


async def generate_destiny_matrix_pdf_html(
    user_name: str,
    birth_date: str,
    positions: dict[str, Any],
    sections: dict[str, str] | None,
) -> bytes:
    from playwright.async_api import async_playwright

    document = build_destiny_matrix_pdf_html(
        user_name=user_name,
        birth_date=birth_date,
        positions=positions,
        sections=sections,
    )
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            page = await browser.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=1)
            await page.set_content(document, wait_until="load")
            return await page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                prefer_css_page_size=True,
            )
        finally:
            await browser.close()
