"""Post-processing for LLM section text in V3 Matrix.

Two responsibilities:

  1. ``fix_arcana_names(text)`` — replace any «аркан N (X)» token where
     X is not the canonical Ladini name with «аркан N (canon)». The
     model has strong Rider-Waite priors and sometimes writes «Дьявол»
     for 15 instead of «Проявление». We fix by number, because the
     NUMBER is the source of truth in our domain model.

  2. ``strip_service_preamble(text)`` — remove leading service phrases
     («Ответ:», «Вот разбор:», «Конечно, …»). The model occasionally
     prepends them even when the system prompt forbids it.

Both helpers are idempotent and run on cached content too, so old
DB rows benefit immediately without regen.
"""

from __future__ import annotations

import re
from typing import Iterable

from services.destiny_matrix.calculator import ARCANA_NAMES

__all__ = (
    "fix_arcana_names",
    "strip_service_preamble",
    "fix_known_typos",
    "polish_section_text",
)


_ARCANA_RE = re.compile(
    r"(аркан\s+)(\d{1,2})(\s*\()([^)]+)(\))",
    re.IGNORECASE,
)


def fix_arcana_names(text: str) -> tuple[str, int]:
    """Replace every «аркан N (X)» where X ≠ canonical name.

    Returns (fixed_text, num_replacements). The replacement is silent —
    the canonical name simply overrides whatever the model wrote, since
    the number is unambiguous.
    """
    fixes = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal fixes
        try:
            num = int(m.group(2))
        except ValueError:
            return m.group(0)
        canon = ARCANA_NAMES.get(num)
        if not canon:
            return m.group(0)
        if m.group(4).strip() == canon:
            return m.group(0)
        fixes += 1
        return f"{m.group(1)}{num}{m.group(3)}{canon}{m.group(5)}"

    fixed = _ARCANA_RE.sub(repl, text)
    return fixed, fixes


# Service phrases the model sometimes prepends. Checked case-insensitive,
# trimmed at colon / em-dash / comma.
_SERVICE_HEADS: tuple[str, ...] = (
    "ответ",
    "вот разбор",
    "вот ваш разбор",
    "вот твой разбор",
    "разбор",
    "разбор для тебя",
    "конечно",
    "хорошо",
    "понимаю",
    "вот",
    "итак",
)

_SERVICE_PREFIX_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(s) for s in _SERVICE_HEADS) + r")\b"
    r"[\s,:.—\-]*",
    re.IGNORECASE,
)


def strip_service_preamble(text: str) -> tuple[str, int]:
    """Remove a leading service phrase from the FIRST non-empty line.

    Only matches when the service word is the WHOLE leading token (we
    won't truncate prose that legitimately starts with «Ответственность…»).
    Returns (clean_text, 1 if stripped else 0).
    """
    if not text:
        return text, 0
    # Find first non-blank line offset.
    lead = ""
    rest = text
    for i, ch in enumerate(text):
        if ch.strip():
            lead = text[:i]
            rest = text[i:]
            break
    m = _SERVICE_PREFIX_RE.match(rest)
    if not m:
        return text, 0
    # Make sure what follows starts with a capital letter — otherwise we
    # probably ate into a real word ("ответственность" → "ственность").
    tail = rest[m.end():].lstrip()
    if not tail:
        return text, 0
    if not (tail[0].isupper() or tail[0] in "«\""):
        return text, 0
    return lead + tail, 1


_CODE_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*\n?|\n?```\s*$", re.MULTILINE)
_STRAY_STAR_RE = re.compile(r"(?<!\*)\*(?!\*)")

# Known typos the model emits on domain words. Whole-word, case-insensitive.
# Keep tight — we only ship fixes we've actually seen in production output.
_KNOWN_TYPOS: dict[str, str] = {
    # «аркаом» (missed 'н') seen on a generated «Энергия года» section.
    "аркаом": "арканом",
    "арканмом": "арканом",
    "аркаа": "аркана",
    "арканн": "арканом",
}
_TYPO_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _KNOWN_TYPOS) + r")\b",
    re.IGNORECASE,
)


def fix_known_typos(text: str) -> tuple[str, int]:
    """Apply the tiny domain typo dictionary. Whole-word only, preserves
    sentence-initial capitalisation."""
    fixes = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal fixes
        original = m.group(0)
        canon = _KNOWN_TYPOS[original.lower()]
        fixes += 1
        # Preserve capitalisation of the first letter.
        if original[0].isupper():
            return canon[0].upper() + canon[1:]
        return canon

    return _TYPO_RE.sub(repl, text), fixes


def polish_section_text(text: str) -> tuple[str, dict[str, int]]:
    """Run the full V3 text-polish pipeline on one section.

    Returns (clean_text, stats) where stats is a dict of issue-type
    counts: ``arcana_name_mismatch``, ``leading_service_word``,
    ``code_fence``, ``stray_asterisk``.
    """
    stats = {
        "arcana_name_mismatch": 0,
        "leading_service_word": 0,
        "code_fence": 0,
        "stray_asterisk": 0,
    }
    if not text:
        return text, stats

    # 1) drop code fences (```markdown ... ```)
    fence_hits = len(_CODE_FENCE_RE.findall(text))
    if fence_hits:
        text = _CODE_FENCE_RE.sub("", text)
        stats["code_fence"] = fence_hits

    # 2) strip leading «Ответ:» / «Вот разбор:» style preamble.
    # Loop up to 3 times — sometimes the model stacks two ("Конечно. Вот
    # разбор:") and stripping the first reveals the second.
    total_preamble = 0
    for _ in range(3):
        text, n = strip_service_preamble(text)
        if not n:
            break
        total_preamble += n
    stats["leading_service_word"] = total_preamble

    # 3) canonical arcana names by number
    text, n = fix_arcana_names(text)
    stats["arcana_name_mismatch"] = n

    # 4) leftover single asterisks (markdown italic that the React-side
    #    asterisk-strip already handles client-side, but PDF needs the
    #    same hardening — see commit 40c1d25 history).
    stars = len(_STRAY_STAR_RE.findall(text))
    if stars:
        text = _STRAY_STAR_RE.sub("", text)
        stats["stray_asterisk"] = stars

    # 5) tiny domain-typo dictionary (e.g. «аркаом» → «арканом»).
    text, n = fix_known_typos(text)
    stats["known_typo"] = n

    return text, stats


def aggregate_stats(per_section: Iterable[dict[str, int]]) -> dict[str, int]:
    """Sum stats from several polished sections into one report."""
    out: dict[str, int] = {
        "arcana_name_mismatch": 0,
        "leading_service_word": 0,
        "code_fence": 0,
        "stray_asterisk": 0,
    }
    for s in per_section:
        for k, v in s.items():
            out[k] = out.get(k, 0) + int(v)
    return out
