"""HTML/CSS Destiny Matrix PDF renderer (V2).

Mirrors ``services.natal_pdf_html`` — builds a print-oriented HTML document
and renders it through Playwright/Chromium. No ReportLab fallback here;
the route catches exceptions and surfaces a 502 to the client.

V2 scope:
    * cover, contents, octagram (same as MVP)
    * 8 narrative sections, each now augmented with 3 arcana mini-cards
      (meaning + plus/minus from ``arcana_meanings``) and a hardcoded
      practice-template block (bulleted action steps)
    * mini-glossary page(s) — all 22 arcana × ~40 words
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
/* @page margin 0 so the dark theme background fills the entire paper
   (Chromium doesn't paint a custom @page background, so we let .page
   take the whole sheet). For overflow sections we use box-decoration-
   break: clone — when a section breaks across printed pages, EACH
   fragment carries its own padding+background, so multi-page sections
   keep their 22mm top / 17mm bottom margins on every sheet without
   bleeding text to the paper edge. */
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; overflow-wrap: anywhere; }}
html, body {{ margin: 0; padding: 0; background: {BG}; color: {TEXT}; }}
body {{ font-family: "DejaVu Sans", Arial, sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.page {{
  position: relative;
  display: block;
  width: 210mm;
  min-height: 297mm;
  padding: 22mm 18mm 17mm;
  background: {BG};
  break-after: page;
  page-break-after: always;
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
}}
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
.octa-caption {{ color: {TEXT_DIM}; font: 11.5px/1.55 "DejaVu Serif", Georgia, serif; margin: 3mm 6mm 0; }}
.octa-caption p {{ margin: 0 0 2.5mm; text-align: left; }}
.octa-caption p:last-child {{ margin-bottom: 0; }}
.octa-caption strong {{ color: {GOLD}; font-weight: 600; }}
.octa-anchors {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 5mm; margin-top: 8mm; }}
.octa-anchor {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 7px; padding: 5mm; text-align: center; }}
.octa-anchor .num {{ color: {GOLD}; font: 23px "DejaVu Serif", Georgia, serif; }}
.octa-anchor .label {{ color: {TEXT_DIM}; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-top: 2mm; }}
.octa-anchor .name {{ font: 12.5px "DejaVu Serif", Georgia, serif; margin-top: 2mm; }}

/* Narrative pages */
.section-card {{ background: {PANEL}; border: 1px solid {BORDER}; border-left: 3px solid {GOLD}; border-radius: 8px; padding: 6mm 7mm; }}
.section-card .anchor {{ display: flex; gap: 6mm; align-items: center; margin-bottom: 5mm; padding-bottom: 4mm; border-bottom: 1px solid rgba(214,184,90,.18); }}
.section-card .anchor .num {{ color: {GOLD}; font: 30px "DejaVu Serif", Georgia, serif; line-height: 1; }}
.section-card .anchor .name {{ font: 16px "DejaVu Serif", Georgia, serif; }}
.section-card .anchor .keywords {{ color: {TEXT_DIM}; font-size: 11px; margin-top: 1.5mm; }}
.section-card p {{ font-size: 12.5px; line-height: 1.5; margin: 0 0 4mm; }}
.section-card p:last-child {{ margin-bottom: 0; }}
.section-quote {{ text-align: center; color: {TEXT_DIM}; font: italic 12.5px "DejaVu Serif", Georgia, serif; margin: 4mm 0 5mm; }}

/* V2: decoded arcana mini-cards inside each narrative section */
.arc-trio {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 3mm; margin-top: 5mm; }}
.arc-card {{ background: {PANEL_DARK}; border: 1px solid {BORDER}; border-radius: 6px; padding: 4mm; min-height: 38mm; }}
.arc-card .head {{ display: flex; align-items: baseline; gap: 3mm; margin-bottom: 2mm; }}
.arc-card .num {{ color: {GOLD}; font: 18px "DejaVu Serif", Georgia, serif; line-height: 1; }}
.arc-card .name {{ font: 11.5px "DejaVu Serif", Georgia, serif; line-height: 1.2; }}
.arc-card .ctx {{ color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 2mm; }}
.arc-card .body {{ color: {TEXT}; font-size: 10px; line-height: 1.4; margin: 0 0 2.5mm; }}
.arc-card .pm {{ font-size: 9.5px; line-height: 1.35; margin: 0; }}
.arc-card .pm .pl {{ color: #8fd497; font-weight: 600; }}
.arc-card .pm .mn {{ color: #ff8b8b; font-weight: 600; }}
.arc-card .pro {{ color: {TEXT_DIM}; font-size: 9px; margin-top: 2mm; font-style: italic; }}

/* V2: practice template blocks */
.practice {{ background: rgba(20,16,28,.55); border: 1px solid {BORDER}; border-radius: 8px; padding: 5mm 6mm; margin-top: 5mm; }}
.practice h3 {{ color: {GOLD}; font: 13px "DejaVu Serif", Georgia, serif; letter-spacing: 1.5px; text-transform: uppercase; margin: 0 0 3mm; }}
.practice ul {{ margin: 0; padding-left: 5mm; }}
.practice li {{ font-size: 11px; line-height: 1.45; margin-bottom: 2mm; color: {TEXT}; }}
.practice li:last-child {{ margin-bottom: 0; }}
.practice .affirm {{ margin-top: 4mm; padding: 3mm; border-left: 2px solid {GOLD}; color: {TEXT}; font: italic 11.5px "DejaVu Serif", Georgia, serif; background: rgba(214,184,90,.05); }}

/* V2: glossary */
.glossary-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 3mm 5mm; margin-top: 6mm; }}
.gloss-cell {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 6px; padding: 3.5mm 4mm; min-height: 22mm; }}
.gloss-cell .head {{ display: flex; align-items: baseline; gap: 3mm; }}
.gloss-cell .num {{ color: {GOLD}; font: 16px "DejaVu Serif", Georgia, serif; line-height: 1; }}
.gloss-cell .name {{ font: 12px "DejaVu Serif", Georgia, serif; }}
.gloss-cell .kw {{ color: {TEXT_DIM}; font-size: 9.5px; margin-top: 1mm; letter-spacing: .5px; }}
.gloss-cell p {{ margin: 2mm 0 0; font-size: 10px; line-height: 1.4; color: {TEXT}; }}

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
    """Port of ``frontend/src/components/destiny/DestinyOctagram.tsx`` to
    static SVG so the PDF and the React TMA view render the same picture.

    Geometry constants mirror the React file verbatim:
      viewBox -40 -40 (600+80) (600+80), centre (300, 300).
      Diamond corners: TOP (300,70), RIGHT (530,300), BOTTOM (300,530),
      LEFT (70,300). Square corners: TL (140,140) … BL (140,460).
      8 main nodes are offset OUTWARD from the corners by NODE_OFF=26
      (cardinal) / 26/√2 (diagonal). Inner ring R=155.
    """
    pers = positions.get("personality", {})
    sq = positions.get("ancestral_square", {})
    specials = positions.get("specials", {}) or {}
    money_diag = positions.get("money_diagonal") or [0, 0, 0]
    channels = positions.get("channels", {}) or {}

    def ch3(key: str) -> tuple[int | None, int | None, int | None]:
        arr = channels.get(key) or []
        return (
            arr[0] if len(arr) > 0 else None,
            arr[1] if len(arr) > 1 else None,
            arr[2] if len(arr) > 2 else None,
        )

    t1_, t2_, t3_ = ch3("talents")          # top ray
    d1_, d2_, d3_ = ch3("parental")         # left ray
    r1_, r2_, _ = ch3("material_karma")     # right ray
    b1_, b2_, _ = ch3("karmic_tail")        # bottom ray
    aft1_, aft2_, _ = ch3("ancestral_father_talents")  # TL ray
    amt1_, amt2_, _ = ch3("ancestral_mother_talents")  # TR ray
    afk1_, afk2_, _ = ch3("ancestral_father_karma")    # BR ray
    amk1_, amk2_, _ = ch3("ancestral_mother_karma")    # BL ray

    CX = CY = 300.0
    # Diamond vertices (TOP/RIGHT/BOTTOM/LEFT) — corners of the rotated square
    TOP = (300.0, 70.0)
    RIGHT = (530.0, 300.0)
    BOTTOM = (300.0, 530.0)
    LEFT = (70.0, 300.0)
    # Straight (ancestral) square vertices
    TL = (140.0, 140.0)
    TR = (460.0, 140.0)
    BR = (460.0, 460.0)
    BL = (140.0, 460.0)

    # 8 main nodes are positioned OUTSIDE the octagram so their inner edge
    # just kisses the corner. Cardinal offset 26, diagonal 26/√2.
    NODE_OFF = 26.0
    NODE_OFF_D = NODE_OFF / math.sqrt(2)
    N_TOP = (TOP[0], TOP[1] - NODE_OFF)
    N_RIGHT = (RIGHT[0] + NODE_OFF, RIGHT[1])
    N_BOTTOM = (BOTTOM[0], BOTTOM[1] + NODE_OFF)
    N_LEFT = (LEFT[0] - NODE_OFF, LEFT[1])
    N_TL = (TL[0] - NODE_OFF_D, TL[1] - NODE_OFF_D)
    N_TR = (TR[0] + NODE_OFF_D, TR[1] - NODE_OFF_D)
    N_BR = (BR[0] + NODE_OFF_D, BR[1] + NODE_OFF_D)
    N_BL = (BL[0] - NODE_OFF_D, BL[1] + NODE_OFF_D)

    R_INNER = 155.0

    def along(v: tuple[float, float], t: float) -> tuple[float, float]:
        return (v[0] + t * (CX - v[0]), v[1] + t * (CY - v[1]))

    # Channel-dot tiers — 1st near corner (t=0.09), 3rd near centre (t=0.62)
    RAY_T_1 = 0.09
    RAY_T_3 = 0.62
    TOP_1 = along(TOP, RAY_T_1); TOP_3 = along(TOP, RAY_T_3)
    LEFT_1 = along(LEFT, RAY_T_1); LEFT_3 = along(LEFT, RAY_T_3)
    RIGHT_1 = along(RIGHT, RAY_T_1)
    BOT_1 = along(BOTTOM, RAY_T_1)
    TL_1 = along(TL, RAY_T_1)
    TR_1 = along(TR, RAY_T_1)
    BR_1 = along(BR, RAY_T_1)
    BL_1 = along(BL, RAY_T_1)
    # 2nd tier — on the perimeter of the octagram (intersection of ray and
    # the opposite shape's side), hard-coded per spec.
    TOP_2 = (300.0, 140.0); BOT_2 = (300.0, 460.0)
    LEFT_2 = (140.0, 300.0); RIGHT_2 = (460.0, 300.0)
    TL_2 = (185.0, 185.0); TR_2 = (415.0, 185.0)
    BR_2 = (415.0, 415.0); BL_2 = (185.0, 415.0)

    # Inner-circle specials per spec §6.1
    COMFORT_A = along((530.0, 300.0), 0.85)  # ближе к центру
    COMFORT_B = along((530.0, 300.0), 0.72)  # ближе к money
    CROSS_POS = (380.0, 380.0)
    MONEY_DIAG_OUTER = (429.0, 349.0)
    LOVE_DIAG_OUTER = (349.0, 429.0)
    HEART_POS = (345.0, 400.0)
    DOLLAR_POS = (392.0, 345.0)

    # Palette (mirrors the React file's COLOR_*)
    LINE = "rgba(200, 195, 180, 0.6)"
    LINE_ACC = "rgba(232, 200, 98, 0.75)"
    INNER_RING = "rgba(232, 200, 98, 0.35)"
    DOT_GOLD = "rgba(232, 200, 98, 0.95)"
    DOT_RED = "#e07b6a"
    DOT_PINK = "#d27b9c"
    DOT_ORANGE = "#e8a553"
    CENTER_GOLD = "#e8c862"
    BASE_GOLD = "#e8c862"
    KARMA_RED = "#e07b6a"
    FATHER = "rgba(120, 145, 220, 0.75)"
    MOTHER = "rgba(220, 110, 130, 0.75)"
    NODE_FILL = "#0e0b20"  # matches React (slightly different from BG)

    R_DOT_1, R_DOT_2, R_DOT_3 = 20.0, 17.0, 14.0

    def _inner_edge(toward: tuple[float, float]) -> tuple[float, float]:
        dx, dy = toward[0] - CX, toward[1] - CY
        length = math.hypot(dx, dy) or 1.0
        return (CX + (dx / length) * R_INNER, CY + (dy / length) * R_INNER)

    p: list[str] = [
        '<svg class="octa-svg" viewBox="-40 -40 680 680" xmlns="http://www.w3.org/2000/svg">',
        # ── 8 inner spokes: centre → inner-ring edge in each direction ──
    ]
    for corner in (LEFT, RIGHT, TOP, BOTTOM, TL, TR, BR, BL):
        ex, ey = _inner_edge(corner)
        p.append(
            f'<line x1="{CX}" y1="{CY}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="{LINE}" stroke-width="1"/>'
        )

    # ── Diamond + straight square outlines ──
    p.append(
        f'<path d="M {LEFT[0]} {LEFT[1]} L {TOP[0]} {TOP[1]} '
        f'L {RIGHT[0]} {RIGHT[1]} L {BOTTOM[0]} {BOTTOM[1]} Z" '
        f'fill="none" stroke="{LINE_ACC}" stroke-width="1.3"/>'
    )
    p.append(
        f'<path d="M {TL[0]} {TL[1]} L {TR[0]} {TR[1]} '
        f'L {BR[0]} {BR[1]} L {BL[0]} {BL[1]} Z" '
        f'fill="none" stroke="{LINE_ACC}" stroke-width="1.3"/>'
    )

    # ── Inner soul circle ──
    p.append(
        f'<circle cx="{CX}" cy="{CY}" r="{R_INNER}" '
        f'fill="none" stroke="{INNER_RING}" stroke-width="1.1"/>'
    )

    # ── Father (blue) / Mother (red) lineage arrows inside the ring ──
    p.append(
        '<defs>'
        f'<marker id="dm-arr-f" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{FATHER}"/></marker>'
        f'<marker id="dm-arr-m" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{MOTHER}"/></marker>'
        '</defs>'
    )
    p.append(
        f'<line x1="{CX - 75}" y1="{CY - 75}" x2="{CX + 75}" y2="{CY + 75}" '
        f'stroke="{FATHER}" stroke-width="1.6" opacity="0.85" '
        f'marker-start="url(#dm-arr-f)" marker-end="url(#dm-arr-f)"/>'
    )
    p.append(
        f'<line x1="{CX - 75}" y1="{CY + 75}" x2="{CX + 75}" y2="{CY - 75}" '
        f'stroke="{MOTHER}" stroke-width="1.6" opacity="0.85" '
        f'marker-start="url(#dm-arr-m)" marker-end="url(#dm-arr-m)"/>'
    )

    # ── Diagonal-arrow labels: «мужская / женская линия» rendered along
    #    the arrows so the reader can identify what they look at without
    #    consulting the caption. Slight offset off the line so the text
    #    doesn't overlap the channel-dots near the centre.
    p.append(
        f'<text x="{CX - 50:.1f}" y="{CY - 52:.1f}" '
        f'transform="rotate(45 {CX - 50:.1f} {CY - 52:.1f})" '
        f'text-anchor="middle" fill="{FATHER}" '
        f'font-size="13" font-weight="500" letter-spacing="0.06em" '
        f'font-family="DejaVu Serif, Georgia, serif">МУЖСКАЯ ЛИНИЯ · РОД ОТЦА</text>'
    )
    p.append(
        f'<text x="{CX - 50:.1f}" y="{CY + 64:.1f}" '
        f'transform="rotate(-45 {CX - 50:.1f} {CY + 64:.1f})" '
        f'text-anchor="middle" fill="{MOTHER}" '
        f'font-size="13" font-weight="500" letter-spacing="0.06em" '
        f'font-family="DejaVu Serif, Georgia, serif">ЖЕНСКАЯ ЛИНИЯ · РОД МАТЕРИ</text>'
    )

    # ── Dashed money/love diagonal RIGHT_2 → BOT_2 through cross_p ──
    p.append(
        f'<path d="M {RIGHT_2[0]} {RIGHT_2[1]} L {BOT_2[0]} {BOT_2[1]}" '
        f'fill="none" stroke="{DOT_ORANGE}" stroke-width="1.2" '
        f'stroke-dasharray="4 3" opacity="0.7"/>'
    )

    # ── Heart icon (red) at (345, 400) ──
    p.append(
        f'<g transform="translate({HEART_POS[0]} {HEART_POS[1]}) scale(0.5)">'
        '<path d="M 0 6 C -10 -4 -22 -4 -22 6 C -22 18 0 32 0 32 '
        'C 0 32 22 18 22 6 C 22 -4 10 -4 0 6 Z" fill="#e84545"/></g>'
    )
    # ── $ icon (green) at (392, 345) ──
    p.append(
        f'<text x="{DOLLAR_POS[0]}" y="{DOLLAR_POS[1]}" text-anchor="middle" '
        f'dy="0.35em" fill="#5cb85c" font-weight="700" '
        f'font-size="22" font-family="DejaVu Serif, Georgia, serif">$</text>'
    )

    # ── Channel dots (small numbered circles on each ray) ──
    def _dot(pos: tuple[float, float], num: int | None, r: float, color: str) -> None:
        if num is None or num == 0:
            return
        x, y = pos
        p.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" '
            f'stroke="none"/>'
        )
        p.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dy="0.35em" '
            f'fill="{NODE_FILL}" font-size="{int(r * 0.85)}" '
            f'font-weight="600" font-family="DejaVu Serif, Georgia, serif">{int(num)}</text>'
        )

    # Cardinal rays
    _dot(TOP_1, t1_, R_DOT_1, DOT_GOLD)
    _dot(TOP_2, t2_, R_DOT_2, DOT_GOLD)
    _dot(TOP_3, t3_, R_DOT_3, DOT_GOLD)
    _dot(LEFT_1, d1_, R_DOT_1, DOT_GOLD)
    _dot(LEFT_2, d2_, R_DOT_2, DOT_GOLD)
    _dot(LEFT_3, d3_, R_DOT_3, DOT_GOLD)
    _dot(RIGHT_1, r1_, R_DOT_1, DOT_GOLD)
    _dot(RIGHT_2, r2_, R_DOT_2, DOT_GOLD)
    _dot(BOT_1, b1_, R_DOT_1, DOT_RED)
    _dot(BOT_2, b2_, R_DOT_2, DOT_RED)
    # Diagonal rays
    _dot(TL_1, aft1_, R_DOT_1, DOT_GOLD)
    _dot(TL_2, aft2_, R_DOT_2, DOT_GOLD)
    _dot(TR_1, amt1_, R_DOT_1, DOT_GOLD)
    _dot(TR_2, amt2_, R_DOT_2, DOT_GOLD)
    _dot(BR_1, afk1_, R_DOT_1, DOT_RED)
    _dot(BR_2, afk2_, R_DOT_2, DOT_RED)
    _dot(BL_1, amk1_, R_DOT_1, DOT_RED)
    _dot(BL_2, amk2_, R_DOT_2, DOT_RED)

    # Comfort / cross / money_diag / love_diag specials inside the ring
    comfort_arr = specials.get("comfort") or []
    if comfort_arr:
        _dot(COMFORT_A, comfort_arr[0] if len(comfort_arr) > 0 else None, R_DOT_3, DOT_PINK)
        _dot(COMFORT_B, comfort_arr[1] if len(comfort_arr) > 1 else None, R_DOT_3, DOT_PINK)
    _dot(CROSS_POS, specials.get("cross"), R_DOT_3, DOT_GOLD)
    _dot(MONEY_DIAG_OUTER, money_diag[0] if money_diag else None, R_DOT_3, DOT_ORANGE)
    _dot(LOVE_DIAG_OUTER, specials.get("love_diag_1"), R_DOT_3, DOT_PINK)

    # ── 9 main numbered nodes (drawn LAST so they sit on top) ──
    def _main(pos: tuple[float, float], num: int | None, r: float, stroke: str) -> None:
        if num is None:
            return
        x, y = pos
        p.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{NODE_FILL}" '
            f'stroke="{stroke}" stroke-width="1.8"/>'
        )
        p.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" dy="0.35em" '
            f'fill="{stroke}" font-size="22" font-weight="500" '
            f'font-family="DejaVu Serif, Georgia, serif">{int(num)}</text>'
        )

    _main(N_LEFT, pers.get("day"), 26.0, BASE_GOLD)
    _main(N_TOP, pers.get("month"), 26.0, BASE_GOLD)
    _main(N_RIGHT, pers.get("year"), 26.0, BASE_GOLD)
    _main(N_BOTTOM, pers.get("bottom"), 26.0, KARMA_RED)
    _main(N_TL, sq.get("top_left"), 26.0, BASE_GOLD)
    _main(N_TR, sq.get("top_right"), 26.0, BASE_GOLD)
    _main(N_BR, sq.get("bottom_right"), 26.0, BASE_GOLD)
    _main(N_BL, sq.get("bottom_left"), 26.0, BASE_GOLD)
    # Centre node (slightly smaller — main-md)
    _main((CX, CY), pers.get("center"), 22.0, CENTER_GOLD)

    # ── Node labels (rendered LAST so they sit above the circles)
    # 4 cardinal points of the personality diamond + 4 ancestral corners.
    LABEL_COLOR = "rgba(232, 200, 98, 0.78)"
    LABEL_RED = "rgba(224, 123, 106, 0.85)"

    def _label(x: float, y: float, anchor: str, color: str, text: str) -> None:
        p.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'fill="{color}" font-size="13" font-weight="500" '
            f'letter-spacing="0.08em" '
            f'font-family="DejaVu Serif, Georgia, serif">{text}</text>'
        )

    # Cardinal nodes — labelled OUTSIDE the diamond corners.
    _label(N_TOP[0], N_TOP[1] - 38, "middle", LABEL_COLOR, "ТАЛАНТ · МЕСЯЦ")
    _label(N_RIGHT[0] + 32, N_RIGHT[1] + 5, "start", LABEL_COLOR, "ФИНАНСЫ")
    _label(N_RIGHT[0] + 32, N_RIGHT[1] + 20, "start", LABEL_COLOR, "ГОД")
    _label(N_BOTTOM[0], N_BOTTOM[1] + 44, "middle", LABEL_RED, "КАРМИЧЕСКИЙ УРОК")
    _label(N_LEFT[0] - 32, N_LEFT[1] + 5, "end", LABEL_COLOR, "ХАРАКТЕР")
    _label(N_LEFT[0] - 32, N_LEFT[1] + 20, "end", LABEL_COLOR, "ДЕНЬ")

    # Ancestral-square corners — labelled OUTSIDE the diagonal corners.
    _label(N_TL[0] - 4, N_TL[1] - 30, "end", LABEL_COLOR, "РОД ОТЦА")
    _label(N_TL[0] - 4, N_TL[1] - 15, "end", LABEL_COLOR, "талант")
    _label(N_TR[0] + 4, N_TR[1] - 30, "start", LABEL_COLOR, "РОД МАТЕРИ")
    _label(N_TR[0] + 4, N_TR[1] - 15, "start", LABEL_COLOR, "талант")
    _label(N_BR[0] + 4, N_BR[1] + 26, "start", LABEL_RED, "РОД ОТЦА")
    _label(N_BR[0] + 4, N_BR[1] + 41, "start", LABEL_RED, "карма")
    _label(N_BL[0] - 4, N_BL[1] + 26, "end", LABEL_RED, "РОД МАТЕРИ")
    _label(N_BL[0] - 4, N_BL[1] + 41, "end", LABEL_RED, "карма")

    p.append("</svg>")
    return "".join(p)


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


_TOC_TITLES = {
    "who_you_are":   "Кто ты — характер и центр",
    "karmic_tail":   "Кармический хвост",
    "talents":       "Таланты и вдохновение",
    "purpose":       "Предназначение",
    "relationships": "Отношения",
    "finance":       "Деньги и реализация",
    "parental":      "Род и семья",
    "advice":        "Совет на этот период",
}

_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")


def _contents_page(
    section_first_pages: dict[str, int],
    glossary_page: int,
    summary_page: int,
) -> str:
    rows: list[tuple[str, str, str]] = [(_ROMAN[0], "Октаграмма судьбы", "3")]
    for idx, key in enumerate(SECTION_KEYS, start=1):
        rows.append(
            (_ROMAN[idx], _TOC_TITLES.get(key, key), str(section_first_pages.get(key, "—")))
        )
    rows.append((_ROMAN[len(SECTION_KEYS) + 1], "Краткий словарь арканов", str(glossary_page)))
    rows.append((_ROMAN[len(SECTION_KEYS) + 2], "Сводная таблица ключевых точек", str(summary_page)))
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
        '<div class="octa-caption">'
        '<p><strong>Личностный ромб</strong> — четыре кардинальные точки + центр. '
        'Слева <strong>День</strong> (характер, как вас видят), сверху '
        '<strong>Месяц</strong> (главный талант), справа <strong>Год</strong> '
        '(материальная сфера, финансы), снизу <strong>Карма</strong> '
        '(главный кармический урок жизни). В центре — настоящий характер.</p>'
        '<p><strong>Родовой квадрат</strong> — углы, развёрнутые на 45°. '
        'Верхние два — родовые таланты (отец слева-вверху, мать справа-вверху), '
        'нижние — родовая карма (отец справа-внизу, мать слева-внизу).</p>'
        '<p><strong>Синяя стрелка</strong> — мужская линия (род отца, диагональ '
        'талант→карма по отцовской линии). <strong>Красная стрелка</strong> — '
        'женская линия (род матери). Числа на лучах между узлами — каналы '
        'талантов, денег, родителей и партнёрства.</p>'
        '</div>'
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


def _section_arcana_trio(
    positions: dict[str, Any], section_key: str
) -> list[tuple[int, str, str]]:
    """3 ``(arcana_num, context, short_label)`` per section. Each gets a
    mini-card with meaning + plus/minus from ``arcana_meanings``.

    Picked so the section is anchored to its dominant matrix points —
    keeps the cards specific to the reader, not generic."""
    pers = positions.get("personality", {}) or {}
    sq = positions.get("ancestral_square", {}) or {}
    purposes = positions.get("purposes", {}) or {}
    channels = positions.get("channels", {}) or {}

    def _ch(name: str, idx: int) -> int | None:
        seq = channels.get(name)
        if isinstance(seq, list) and len(seq) > idx:
            return seq[idx]
        return None

    raw_map: dict[str, list[tuple[Any, str, str]]] = {
        "who_you_are": [
            (pers.get("center"),     "personality", "Центр — характер"),
            (pers.get("day"),        "personality", "День — портрет"),
            (sq.get("top_left"),     "ancestral",   "Внутренний потенциал"),
        ],
        "karmic_tail": [
            (pers.get("bottom"),     "karmic_tail",     "Главный урок"),
            (pers.get("year"),       "material_karma",  "Прошлый опыт"),
            (sq.get("bottom_left"),  "ancestral",       "Родовая карма"),
        ],
        "talents": [
            (pers.get("month"),      "talents",     "Высшая суть"),
            (sq.get("top_right"),    "ancestral",   "Талант рода"),
            (sq.get("top_left"),     "talents",     "Подача дара"),
        ],
        "purpose": [
            (purposes.get("personal"),  "purpose", "До ~40 лет"),
            (purposes.get("social"),    "purpose", "40–60 лет"),
            (purposes.get("planetary"), "purpose", "Миссия"),
        ],
        "relationships": [
            (_ch("relationships", 0), "relationships", "Вход в отношения"),
            (_ch("relationships", 1), "relationships", "Что делать"),
            (pers.get("bottom"),      "relationships", "Урок отношений"),
        ],
        "finance": [
            (_ch("finance", 0),         "finance",        "Откуда деньги"),
            (pers.get("year"),          "finance",        "Денежный канал"),
            (_ch("finance", 2),         "material_karma", "Готовый ресурс"),
        ],
        "parental": [
            (_ch("parental", 0),     "parental", "Зачем пришёл"),
            (pers.get("day"),        "parental", "Роль ребёнка"),
            (sq.get("bottom_right"), "parental", "Урок родителей"),
        ],
        "advice": [
            (pers.get("center"),         "personality", "Опора характера"),
            (purposes.get("planetary"),  "purpose",     "Миссия дальше"),
            (pers.get("month"),          "talents",     "Питание дара"),
        ],
    }
    out: list[tuple[int, str, str]] = []
    seen: set[tuple[int, str]] = set()
    for num, ctx, label in raw_map.get(section_key, []):
        if not isinstance(num, int):
            continue
        key = (num, ctx)
        if key in seen:
            continue
        seen.add(key)
        out.append((num, ctx, label))
    return out


_CONTEXT_LABEL_RU = {
    "personality":     "характер",
    "talents":         "талант",
    "purpose":         "предназначение",
    "parental":        "род.-дет.",
    "ancestral":       "род",
    "relationships":   "отношения",
    "finance":         "финансы",
    "material_karma":  "мат. карма",
    "karmic_tail":     "карма",
}


# Hardcoded practice templates — generic but actionable. Personalisation
# already comes from the LLM section text + the arcana cards above.
PRACTICE_BLOCKS = {
    "who_you_are": {
        "title": "Твои сильные стороны на каждый день",
        "items": [
            "Записывай каждый вечер 1-2 ситуации дня, где ты проявил свою «настоящую» энергию — без подстройки под чужие ожидания.",
            "Раз в неделю задавай себе вопрос: «Что я делал в эту неделю по привычке, а не по своему характеру?» Меняй одну такую привычку.",
            "Найди 2-3 человека, рядом с которыми тебе не приходится «играть». Контакт с ними — твоя точка перезагрузки.",
            "Когда чувствуешь усталость без причины — сверься с центром: что ты сейчас делаешь вопреки своей природе?",
        ],
    },
    "karmic_tail": {
        "title": "Практика проработки кармического урока",
        "items": [
            "Выпиши 3-5 ситуаций из прошлого года, в которых ты повторил один и тот же сценарий. Что у них общего?",
            "Один раз в неделю — практика «другого выбора»: в типовой ситуации поступи противоположно привычному. Заметь реакцию тела.",
            "Если урок про границы — тренируйся отказывать без оправданий («нет, не получится», без объяснений). Минимум 1 отказ в день.",
            "Если урок про доверие — тренируйся озвучивать просьбу прямо, а не намёками. Минимум 1 такая просьба в день.",
        ],
    },
    "talents": {
        "title": "Профессии и призвание — куда направить дар",
        "items": [
            "Выпиши 5 занятий, после которых ты чувствуешь не усталость, а наполнение. Это первые подсказки про твой дар.",
            "В течение месяца уделяй 30 минут в день одному из этих занятий — не для результата, а для подтверждения «это моё».",
            "Если в карте сильны творческие арканы — попробуй формат «учитель-наставник»: объясни кому-то то, что умеешь.",
            "Если сильны организационные арканы (4, 7, 11) — попробуй вести небольшой проект от старта до запуска.",
            "Не путай талант с социально одобряемой профессией. Твоё предназначение — там, где тебе легко, а не где платят больше.",
        ],
    },
    "purpose": {
        "title": "Шаги к своему предназначению",
        "items": [
            "Раз в квартал перечитывай раздел «Предназначение». До 40 — собирай навык, после 40 — выходи в социальный масштаб, после 60 — делись опытом.",
            "Поставь одну цель на этот год, которая лежит на векторе ЛП → СП → ДП — а не «потому что все так делают».",
            "Если у тебя сильное планетарное предназначение — не торопись. Оно раскрывается через все три первых этапа, не миная их.",
            "Раз в месяц — честный аудит: что из последнего месяца было «по моему вектору», а что — по чужому сценарию?",
        ],
    },
    "relationships": {
        "title": "Твой идеальный партнёр и как с ним строить",
        "items": [
            "Перечитай канал отношений в своей матрице. «Вход» — кого ты притягиваешь, «середина» — что делать в паре, «итог» — куда отношения идут.",
            "Партнёр-зеркало: 3 черты, которые тебя бесят в других, — твои собственные неприсвоенные качества. Найди их у себя.",
            "Раз в неделю — разговор «без претензий» с близким человеком: только наблюдения и просьбы, без обвинений.",
            "Если канал «застрял» в минусе (повторяющиеся болезненные сценарии) — пауза от новых отношений минимум 3 месяца, чтобы пересобрать паттерн.",
        ],
    },
    "finance": {
        "title": "5 шагов открыть денежный канал",
        "items": [
            "Шаг 1. Посмотри в матрицу: твой денежный канал — это «канал года» (правый луч). Какие 3 числа на нём?",
            "Шаг 2. Найди профессию или хобби, где задействован арканный смысл этих чисел. Не «нравится теоретически» — а «уже пробовал».",
            "Шаг 3. Минимум 90 дней одной фокусной деятельности. Деньги приходят к сосредоточенности, а не к разбросу.",
            "Шаг 4. Раз в месяц — учёт доходов и расходов вручную. Без таблиц-автоматов: рука пишет — мозг видит.",
            "Шаг 5. 10-20% дохода — на развитие в своём канале (обучение, инструменты, контакты), не «просто отложить».",
        ],
    },
    "parental": {
        "title": "Твоя задача перед родом и детьми",
        "items": [
            "Если есть дети — спроси себя: что я даю им из «здоровой» части своей родовой программы, а что бессознательно повторяю из больной?",
            "Найди свою «детскую» обиду на одного из родителей. Опиши её на бумаге одним абзацем. Один раз. Сожги или порви — символический жест важен.",
            "Раз в месяц — встреча или звонок старшим родственникам без повода и просьб. Просто послушать.",
            "Если в роду были «закрытые темы» (репрессии, потери, развод) — узнай факты. Знание расширяет канал, незнание сужает.",
        ],
    },
    "advice": {
        "title": "5 шагов на ближайшие 3 месяца + аффирмация",
        "items": [
            "Месяц 1: ежедневная микро-практика 10 минут (медитация, дыхание, прогулка молча). Без пропусков.",
            "Месяц 2: один большой шаг по своему предназначению (новый проект / навык / разговор / переезд).",
            "Месяц 3: один большой отказ — от того, что давно не твоё (отношения, привычка, договор, обязательство).",
            "В конце каждого месяца — короткий письменный отчёт: что было / что узнал о себе / что меняю.",
            "Перечитывай эту страницу раз в 3 месяца. Матрица не меняется, но твой взгляд на неё — да.",
        ],
        "affirmation": (
            "Я не борюсь со своей картой — я учусь её читать. Каждый поворот, "
            "который раньше казался ошибкой, — это страница, на которой я "
            "наконец увидел свой настоящий рисунок."
        ),
    },
}


def _render_arcana_card(
    arcana_num: int,
    context: str,
    label: str,
    arcana_meanings: dict[int, dict[str, dict[str, Any]]] | None,
) -> str:
    fields: dict[str, Any] = {}
    if arcana_meanings:
        fields = arcana_meanings.get(arcana_num, {}).get(context, {}) or {}
    meaning = str(fields.get("meaning") or "").strip()
    plus = str(fields.get("plus") or "").strip()
    minus = str(fields.get("minus") or "").strip()
    professions = str(fields.get("professions") or "").strip()
    if not meaning:
        meaning = (
            f"Аркан {arcana_num} ({_arcana_name(arcana_num)}) в контексте "
            f"«{_CONTEXT_LABEL_RU.get(context, context)}». Подробная "
            "расшифровка появится после обновления словаря."
        )
    pm_html = ""
    if plus or minus:
        bits = []
        if plus:
            bits.append(f'<span class="pl">+ </span>{_e(plus)}')
        if minus:
            bits.append(f'<span class="mn">− </span>{_e(minus)}')
        pm_html = '<p class="pm">' + "<br>".join(bits) + "</p>"
    pro_html = (
        f'<div class="pro">Профессии: {_e(professions)}</div>'
        if professions
        else ""
    )
    return (
        '<article class="arc-card">'
        f'<div class="head"><div class="num">{arcana_num}</div>'
        f'<div class="name">{_e(_arcana_name(arcana_num))}</div></div>'
        f'<div class="ctx">{_e(label)}</div>'
        f'<p class="body">{_e(meaning)}</p>'
        f'{pm_html}{pro_html}'
        "</article>"
    )


def _render_practice_block(section_key: str) -> str:
    block = PRACTICE_BLOCKS.get(section_key)
    if not block:
        return ""
    items_html = "".join(f"<li>{_e(item)}</li>" for item in block.get("items", []))
    affirm = block.get("affirmation")
    affirm_html = f'<div class="affirm">«{_e(affirm)}»</div>' if affirm else ""
    return (
        f'<section class="practice"><h3>{_e(block.get("title", ""))}</h3>'
        f'<ul>{items_html}</ul>{affirm_html}</section>'
    )


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


def _narrative_pages(
    start_page: int,
    section_key: str,
    section_text: str,
    positions: dict[str, Any],
    arcana_meanings: dict[int, dict[str, dict[str, Any]]] | None,
) -> list[str]:
    """V2 narrative section. Returns one or two pages: page 1 has the
    LLM text + 3 arcana cards; if a practice block exists for this
    section, it goes on page 2 (avoids cramming everything onto one A4)."""
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

    trio = _section_arcana_trio(positions, section_key)
    cards_html = "".join(
        _render_arcana_card(num, ctx, label_, arcana_meanings)
        for num, ctx, label_ in trio
    )

    body1 = _section_header(label, "Личный разбор")
    body1 += f'<div class="section-quote">«{_e(SECTION_QUOTES_RU.get(section_key, ""))}»</div>'
    body1 += '<div class="section-card">' + anchor_html
    body1 += "".join(f'<p>{_e(p)}</p>' for p in paragraphs)
    body1 += "</div>"
    if cards_html:
        body1 += f'<div class="arc-trio">{cards_html}</div>'

    pages = [_page(start_page, body1)]

    # Page 2 — practice block (only if defined)
    practice_html = _render_practice_block(section_key)
    if practice_html:
        body2 = _section_header(label, "Практика и шаги", aside="что делать")
        body2 += practice_html
        pages.append(_page(start_page + 1, body2))
    return pages


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


def _glossary_pages(
    start_page: int,
    arcana_meanings: dict[int, dict[str, dict[str, Any]]] | None,
) -> list[str]:
    """Mini-glossary — all 22 arcana, each as a short cell. Pulls the
    `personality` context as the short definition (gender='any'). Falls
    back to the keyword list if the row isn't seeded yet."""

    def _short_text(arcana_num: int) -> str:
        if arcana_meanings:
            fields = arcana_meanings.get(arcana_num, {}).get("personality", {})
            text = str(fields.get("meaning") or "").strip()
            if text:
                words = text.split()
                if len(words) > 36:
                    text = " ".join(words[:36]).rstrip(",.;:") + "…"
                return text
        keywords = _arcana_keywords(arcana_num)
        return f"Ключевые смыслы: {keywords}." if keywords else (
            "Подробное описание появится после обновления словаря."
        )

    # 22 cards / 2 columns ≈ 11 rows; A4 fits ~12 per page so we split
    # into 2 pages of 11 cards each.
    chunks = [list(range(1, 12)), list(range(12, 23))]
    pages: list[str] = []
    for idx, chunk in enumerate(chunks, start=0):
        body = _section_header(
            "Краткий словарь арканов",
            "22 ключевых архетипа Матрицы Судьбы",
            aside=f"{idx + 1} / {len(chunks)}",
        )
        body += '<div class="glossary-grid">'
        for arcana_num in chunk:
            body += (
                '<div class="gloss-cell"><div class="head">'
                f'<div class="num">{arcana_num}</div>'
                f'<div class="name">{_e(_arcana_name(arcana_num))}</div></div>'
                f'<div class="kw">{_e(_arcana_keywords(arcana_num))}</div>'
                f'<p>{_e(_short_text(arcana_num))}</p></div>'
            )
        body += "</div>"
        pages.append(_page(start_page + idx, body))
    return pages


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
    arcana_meanings: dict[int, dict[str, dict[str, Any]]] | None = None,
    gender: str | None = None,  # noqa: ARG001 — reserved for future tone-of-voice tweaks
) -> str:
    """Compose the final HTML document. Section order follows SECTION_KEYS.

    V2: narrative sections may span 2 pages each (narrative + practice).
    Page numbers are assigned sequentially as sections are built so the
    TOC / footer stays consistent regardless of the practice-block mix."""
    safe_sections = sections or {}

    narrative_start = 4  # cover(1) + toc(2) + octagram(3) → narrative starts at 4
    narrative_pages: list[str] = []
    section_first_pages: dict[str, int] = {}
    next_page = narrative_start
    for key in SECTION_KEYS:
        section_first_pages[key] = next_page
        produced = _narrative_pages(
            next_page,
            key,
            safe_sections.get(key, ""),
            positions,
            arcana_meanings,
        )
        narrative_pages.extend(produced)
        next_page += len(produced)

    glossary_start = next_page
    glossary_pages = _glossary_pages(glossary_start, arcana_meanings)
    next_page += len(glossary_pages)

    summary_page_num = next_page
    final_page_num = summary_page_num + 1

    pages = [
        _cover_page(user_name, birth_date, positions),
        _contents_page(section_first_pages, glossary_start, summary_page_num),
        _octagram_page(positions),
        *narrative_pages,
        *glossary_pages,
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
    arcana_meanings: dict[int, dict[str, dict[str, Any]]] | None = None,
    gender: str | None = None,
) -> bytes:
    from playwright.async_api import async_playwright

    from services.playwright_pool import pdf_semaphore

    document = build_destiny_matrix_pdf_html(
        user_name=user_name,
        birth_date=birth_date,
        positions=positions,
        sections=sections,
        arcana_meanings=arcana_meanings,
        gender=gender,
    )
    async with pdf_semaphore:
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
