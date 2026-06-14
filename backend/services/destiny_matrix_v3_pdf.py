"""V3 Destiny Matrix PDF — long-form 15-section report.

Reuses the V2 PDF's CSS shell, cover, and octagram SVG (so the visual
identity stays consistent) but rebuilds the body for the new
15-section narrative + extended math (purposes triples, year energy,
canonical karmic program).

Page layout (~22 pages):
    1   Cover
    2   Contents
    3   Octagram diagram
    4-18 15 section pages, one per section
    19  Karmic program — canonical card (full description + how-to-heal)
    20  8 purposes — composition table
    21  Chakras — sky vs earth table
    22  Disclaimer / final page

PDFs are gated behind premium (same as V2) and reuse the V3 sections
already cached in `destiny_interpretations_v3`.
"""

from __future__ import annotations

from typing import Any

from services.destiny_matrix.arcana_names import ARCANA_NAMES_RU
from services.destiny_matrix.v3_interpreter import SECTION_TITLES, SECTIONS
from services.destiny_matrix_pdf_html import (
    TOTAL_PAGES_TOKEN,
    _css,
    _e,
    _format_birth_date,
    _octagram_page,
    _page,
)

# ── Page builders ───────────────────────────────────────────────────────────


def _cover_page(user_name: str, birth_date: str) -> str:
    bd = _e(_format_birth_date(birth_date))
    nm = _e(user_name or "Без имени")
    # Derive the section count from the live SECTIONS registry — historically
    # the cover-tag hard-coded «15 разделов»; that became wrong when 3
    # sections were merged into the 8 purpose deep dives (now 12).
    main_count = sum(1 for s in SECTIONS if s.group == "main")
    purpose_count = sum(1 for s in SECTIONS if s.group == "purpose")
    body = f"""
    <div class="cover">
      <div class="cover-eyebrow">МАТРИЦА СУДЬБЫ · V3</div>
      <h1 class="cover-title">Полный личный разбор</h1>
      <div class="cover-name">{nm}</div>
      <div class="cover-bd">Дата рождения: {bd}</div>
      <p class="cover-tag">{main_count} разделов · {purpose_count} предназначений · кармическая программа · энергия года</p>
    </div>
    """
    return _page(1, body, class_name="cover-page")


def _contents_page(section_pages: dict[str, int], extra_pages: dict[str, str]) -> str:
    items = []
    for spec in SECTIONS:
        page = section_pages.get(spec.key)
        if page is None:
            continue
        items.append(
            f"<li><span class='toc-num'>{page:02d}</span> "
            f"<span class='toc-title'>{_e(spec.title)}</span></li>"
        )
    for key, label in extra_pages.items():
        page = section_pages.get(key)
        if page is not None:
            items.append(
                f"<li><span class='toc-num'>{page:02d}</span> "
                f"<span class='toc-title'>{_e(label)}</span></li>"
            )
    body = f"""
    <div class="contents">
      <h2 class="contents-title">Содержание</h2>
      <ol class="toc-list">{''.join(items)}</ol>
    </div>
    """
    return _page(2, body, class_name="contents-page")


def _section_body(content: str) -> str:
    """LLM content sanitiser: strip markdown bold/headers + run the V3
    text-polish pipeline so old cached rows benefit retroactively.

    Polish covers preamble words («Ответ:», «Вот разбор:»), code fences,
    stray single asterisks, and canonical arcana-name enforcement. New
    rows are polished at generation time (services/destiny_matrix/
    v3_interpreter.py::_generate_one) — this call is the safety net
    for rows already in the DB.
    """
    if not content:
        return "<p class='section-empty'>Раздел не сгенерирован.</p>"
    # Lazy import to avoid pulling LLM deps when only the PDF helper is
    # used (e.g. tests).
    from services.destiny_matrix.text_fix import polish_section_text
    content, _ = polish_section_text(content)
    cleaned = (
        content
        .replace("**", "")
        .replace("__", "")
    )
    # Strip leading markdown headers (#, ##, ###) per line
    lines = []
    for raw_line in cleaned.split("\n"):
        ln = raw_line.lstrip()
        while ln.startswith("#"):
            ln = ln.lstrip("# ").strip()
        lines.append(ln)
    safe = _e("\n".join(lines))
    return f"<div class='section-body'>{safe}</div>"


def _section_page(
    page_num: int,
    section_key: str,
    content: str,
    *,
    suffix: str = "",
    group: str = "main",
    group_idx: int = 0,
    group_total: int = 15,
) -> str:
    """Render one V3 section.

    The eyebrow line is derived from the group/index/total triple, NOT
    from page_num arithmetic — historically `page_num - 3` collided
    with `… из 15` once the section list grew past 15 entries.

    ``group``:
      * ``"main"``    → «Раздел NN из {group_total}» (15 narrative sections)
      * ``"purpose"`` → «Предназначение N из 8»
    """
    title = SECTION_TITLES.get(section_key, section_key)
    suffix_html = (
        f"<span class='section-suffix'>{_e(suffix)}</span>" if suffix else ""
    )
    if group == "purpose":
        eyebrow = f"Предназначение {group_idx:01d} из {group_total}"
    else:
        eyebrow = f"Раздел {group_idx:02d} из {group_total}"
    body = f"""
    <div class="section-head v3-head">
      <div class="v3-eyebrow">{_e(eyebrow)}</div>
      <h2>{_e(title)}{suffix_html}</h2>
      <div class="rule"></div>
    </div>
    {_section_body(content)}
    """
    return _page(page_num, body, class_name="v3-section")


def _karmic_page(page_num: int, karmic: dict[str, str] | None) -> str:
    if not karmic:
        body = """
        <div class="section-head v3-head">
          <h2>Кармическая программа</h2><div class="rule"></div>
          <p>Канонической программы для данного хвоста нет в базе.</p>
        </div>
        """
        return _page(page_num, body, class_name="v3-section")
    body = f"""
    <div class="section-head v3-head">
      <div class="v3-eyebrow">Код программы · {_e(karmic['key'])}</div>
      <h2>Канон: «{_e(karmic['name'])}»</h2>
      <div class="rule"></div>
    </div>
    <div class="v3-canon">
      <h4>Прошлое воплощение</h4>
      <p>{_e(karmic['description'])}</p>
      <h4>Как проявляется сейчас</h4>
      <p>{_e(karmic['manifestations'])}</p>
      <h4>Как прорабатывать</h4>
      <div class="section-body">{_e(karmic['how_to_heal'])}</div>
    </div>
    """
    return _page(page_num, body, class_name="v3-section")


def _purposes_page(page_num: int, purposes: dict[str, dict[str, Any]]) -> str:
    """8 purposes as a composition table: `left + right = total (Name)`."""
    rows = []
    for k, p in purposes.items():
        name = p.get("name", k)
        triple = p.get("key", [0, 0, 0])
        l, r, t = triple
        arc_name = ARCANA_NAMES_RU.get(t, "")
        rows.append(
            f"<tr><td class='triple-name'>{_e(name)}</td>"
            f"<td class='triple-key'>{l} + {r} = <strong>{t}</strong></td>"
            f"<td class='triple-arc'>{_e(arc_name)}</td></tr>"
        )
    body = f"""
    <div class="section-head v3-head">
      <h2>8 предназначений</h2><div class="rule"></div>
      <p>Числовая композиция всех восьми задач: левый компонент + правый = итог.</p>
    </div>
    <table class="v3-table">
      <thead><tr><th>Линия</th><th>Композиция</th><th>Аркан итога</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """
    return _page(page_num, body, class_name="v3-section")


def _chakras_page(page_num: int, chakras: dict[str, dict[str, int]]) -> str:
    """7-row table of chakra arcanas on the sky and earth lines."""
    order = [
        ("Сахасрара",   "sahasrara"),
        ("Аджна",       "adjna"),
        ("Вишудха",     "vishuddha"),
        ("Анахата",     "anahata"),
        ("Манипура",    "manipura"),
        ("Свадхистана", "svadhisthana"),
        ("Муладхара",   "muladhara"),
    ]
    sky = chakras.get("sky", {})
    earth = chakras.get("earth", {})
    rows = []
    for ru, k in order:
        s = sky.get(k, 0)
        e = earth.get(k, 0)
        s_name = ARCANA_NAMES_RU.get(s, "")
        e_name = ARCANA_NAMES_RU.get(e, "")
        rows.append(
            f"<tr><td>{ru}</td>"
            f"<td>{s} <span class='dim'>{_e(s_name)}</span></td>"
            f"<td>{e} <span class='dim'>{_e(e_name)}</span></td></tr>"
        )
    body = f"""
    <div class="section-head v3-head">
      <h2>Чакры — Небо и Земля</h2><div class="rule"></div>
      <p>Слева — психо-эмоциональное измерение, справа — физическое проявление.</p>
    </div>
    <table class="v3-table">
      <thead><tr><th>Чакра</th><th>Небо</th><th>Земля</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """
    return _page(page_num, body, class_name="v3-section")


def _final_page(page_num: int) -> str:
    body = """
    <div class="final">
      <h2>Несколько важных оговорок</h2>
      <div class="rule"></div>
      <p>
        Этот разбор — карта внутренних энергий и потенциальных сценариев,
        а не предсказание событий или диагноз. Решения о здоровье,
        финансах и отношениях принимаются с учётом профессиональных
        консультантов (врачи, юристы, финансовые советники).
      </p>
      <p>
        Расшифровки кармической программы и 8 предназначений построены на
        методологии Натальи Ладини. Числа в матрице вычисляются точно из
        даты рождения; всё остальное — это интерпретация, в которой важна
        ваша собственная резонансность с описанным.
      </p>
      <p class="final-sign">ASTRO TMA — ваш карманный астролог 🌙</p>
    </div>
    """
    return _page(page_num, body, class_name="v3-final")


# ── V3-specific CSS overlay ─────────────────────────────────────────────────


_V3_CSS = """
/* V3 section heads are vertical: eyebrow → title → rule.
   The base .section-head is flex+space-between which squeezed h2 into
   a narrow column and forced wraps like «День / ги» across the
   horizontal rule. Reset that layout for V3 specifically. */
.section-head.v3-head {
  display: block;
  margin-bottom: 6mm;
}
.v3-head .rule {
  width: 100%;
  margin: 3mm 0 0;
}
.v3-eyebrow {
  text-transform: uppercase;
  font-size: 8pt;
  letter-spacing: 0.18em;
  color: #d6b85a;
  margin-bottom: 4mm;
}
.v3-head h2 {
  font-size: 22pt;
  margin: 0 0 3mm;
  /* The global rule sets overflow-wrap: anywhere so long Latin URLs
     don't overflow body columns. On Cyrillic headings that produces
     mid-word breaks («День»/«ги») — opt back out for V3 titles. */
  overflow-wrap: normal;
  word-break: keep-all;
  hyphens: manual;
}
.section-suffix {
  font-size: 12pt;
  color: #a9a1bb;
  font-weight: normal;
  margin-left: 6pt;
}
.section-body {
  font-size: 10.5pt;
  line-height: 1.55;
  white-space: pre-line;
  color: #f4f0e8;
  margin-top: 6mm;
}
.section-empty {
  color: #a9a1bb;
  font-style: italic;
}
.v3-canon h4 {
  margin: 6mm 0 2mm;
  color: #d6b85a;
  font-size: 11pt;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}
.v3-canon p {
  font-size: 10.5pt;
  line-height: 1.55;
  margin: 0 0 4mm;
}
.v3-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8mm;
  font-size: 10pt;
}
.v3-table th, .v3-table td {
  padding: 3mm 4mm;
  border-bottom: 1px solid rgba(214, 184, 90, .18);
  text-align: left;
  vertical-align: top;
}
.v3-table th {
  color: #d6b85a;
  font-weight: normal;
  text-transform: uppercase;
  font-size: 8pt;
  letter-spacing: 0.18em;
}
.triple-name { width: 42%; }
.triple-key  { width: 28%; }
.triple-arc  { color: #a9a1bb; }
.dim         { color: #a9a1bb; font-style: italic; }
.contents { padding: 18mm 16mm; }
.contents-title { font-size: 22pt; color: #d6b85a; margin: 0 0 8mm; }
.toc-list { list-style: none; padding: 0; margin: 0; font-size: 11pt; }
.toc-list li {
  display: flex; gap: 8mm; padding: 2.6mm 0;
  border-bottom: 1px dashed rgba(214, 184, 90, .16);
}
.toc-num { width: 14mm; color: #d6b85a; font-variant-numeric: tabular-nums; }
.toc-title { color: #f4f0e8; }
.cover { padding: 30mm 18mm; display: flex; flex-direction: column; gap: 6mm; }
.cover-eyebrow {
  text-transform: uppercase; letter-spacing: 0.22em; color: #d6b85a; font-size: 9pt;
}
.cover-title { font-size: 30pt; margin: 0; line-height: 1.15; }
.cover-name  { font-size: 16pt; color: #f4d76b; }
.cover-bd    { font-size: 11pt; color: #a9a1bb; }
.cover-tag   { font-size: 10pt; color: #a9a1bb; margin-top: auto; }
.final { padding: 20mm 18mm; }
.final h2 { font-size: 18pt; color: #d6b85a; margin: 0 0 4mm; }
.final p { font-size: 10.5pt; line-height: 1.55; color: #f4f0e8; }
.final-sign { margin-top: 10mm; color: #d6b85a; font-style: italic; }
"""


# ── Public builders ─────────────────────────────────────────────────────────


def build_destiny_matrix_v3_pdf_html(
    *,
    user_name: str,
    birth_date: str,
    positions: dict[str, Any],
    sections_text: dict[str, str],
    purposes: dict[str, dict[str, Any]],
    karmic_program: dict[str, str] | None,
    year_energy: dict[str, int],
) -> str:
    section_titles_suffix = {
        "karmic_tail": f"· {karmic_program['name']}" if karmic_program else "",
        "year_energy": (
            f"· {year_energy.get('current', 0)} → {year_energy.get('upcoming', 0)}"
        ),
    }

    # Page counter: cover=1, contents=2, octagram=3, then sections 4-18.
    pages: list[str] = []
    pages.append(_cover_page(user_name, birth_date))
    section_pages: dict[str, int] = {}

    # Pre-compute per-group totals so the eyebrow counter renders the
    # correct denominator ("из 15" / "из 8") instead of the old hard-coded
    # "из 15" that overflowed once the purpose sections were appended.
    group_totals: dict[str, int] = {}
    for spec in SECTIONS:
        group_totals[spec.group] = group_totals.get(spec.group, 0) + 1

    next_num = 4
    section_html: list[str] = []
    group_counters: dict[str, int] = {}
    for spec in SECTIONS:
        section_pages[spec.key] = next_num
        suffix = section_titles_suffix.get(spec.key, "")
        group_counters[spec.group] = group_counters.get(spec.group, 0) + 1
        section_html.append(_section_page(
            next_num,
            spec.key,
            sections_text.get(spec.key, ""),
            suffix=suffix,
            group=spec.group,
            group_idx=group_counters[spec.group],
            group_total=group_totals[spec.group],
        ))
        next_num += 1

    karmic_page_num = next_num
    purposes_page_num = karmic_page_num + 1
    chakras_page_num = purposes_page_num + 1
    final_page_num = chakras_page_num + 1

    # NOTE: extras keys must NOT collide with any SECTIONS key. Previously
    # 'purposes' was used here AND in SECTIONS, so the merge below silently
    # overwrote section_pages['purposes'] (narrative section, page ~15)
    # with the TOC of the 8-purposes table (page ~28). Result: TOC link
    # to the narrative '8 предназначений' section pointed at the wrong
    # page. Prefix extras keys with '_extra_' to keep namespaces disjoint.
    extras = {
        "_extra_karmic": ("Кармическая программа · канон", karmic_page_num),
        "_extra_purposes_table": ("8 предназначений · таблица", purposes_page_num),
        "_extra_chakras": ("Чакры · таблица", chakras_page_num),
    }
    contents_section_pages = dict(section_pages)
    for key, (label, p) in extras.items():
        contents_section_pages[key] = p
    extras_for_toc = {k: v[0] for k, v in extras.items()}

    pages.append(_contents_page(contents_section_pages, extras_for_toc))
    pages.append(_octagram_page(positions))
    pages.extend(section_html)
    pages.append(_karmic_page(karmic_page_num, karmic_program))
    pages.append(_purposes_page(purposes_page_num, purposes))
    pages.append(_chakras_page(chakras_page_num, positions.get("chakras", {})))
    pages.append(_final_page(final_page_num))

    body = "".join(pages).replace(TOTAL_PAGES_TOKEN, str(len(pages)))
    return (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{_css()}{_V3_CSS}</style></head><body>{body}</body></html>"
    )


async def generate_destiny_matrix_v3_pdf_html(
    *,
    user_name: str,
    birth_date: str,
    positions: dict[str, Any],
    sections_text: dict[str, str],
    purposes: dict[str, dict[str, Any]],
    karmic_program: dict[str, str] | None,
    year_energy: dict[str, int],
) -> bytes:
    from playwright.async_api import async_playwright

    from services.playwright_pool import pdf_semaphore

    document = build_destiny_matrix_v3_pdf_html(
        user_name=user_name,
        birth_date=birth_date,
        positions=positions,
        sections_text=sections_text,
        purposes=purposes,
        karmic_program=karmic_program,
        year_energy=year_energy,
    )
    async with pdf_semaphore:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                page = await browser.new_page(
                    viewport={"width": 794, "height": 1123},
                    device_scale_factor=1,
                )
                await page.set_content(document, wait_until="load")
                return await page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                    prefer_css_page_size=True,
                )
            finally:
                await browser.close()
