"""Post-processing for LLM-generated natal/astro prose.

Single responsibility right now: catch the small set of malformed
zodiac-adjective forms Haiku has actually emitted on production
readings. The model knows the sign names («Козерог», «Стрелец») but
sometimes produces garbled adjective stems — «козеджий», «стерельцовский»
etc. — likely a tokenisation artefact on the Russian zodiac vocab.

Whole-word, case-preserving for the first character. Tight dict only —
ship fixes for forms we've actually seen, not speculation.

The same pattern is used by `services.destiny_matrix.text_fix` for the
destiny domain (arcana names, preamble strip). We keep this module
separate because the natal pipeline doesn't import destiny code.
"""

from __future__ import annotations

import re

__all__ = ("polish_natal_text",)


_KNOWN_TYPOS: dict[str, str] = {
    # Capricorn adjective (Козерог → козерожий)
    "козеджий":      "козерожий",
    "козережий":     "козерожий",
    "козедский":     "козерожский",
    "козерогий":     "козерожий",
    # Sagittarius (Стрелец → стрельцовский)
    "стерельцовский": "стрельцовский",
    "стрелльцовский": "стрельцовский",
    "стрелцовский":   "стрельцовский",
    # Aries (Овен → овновский / овенский — both attested; we use овновский)
    "овеновский":  "овновский",
    # Taurus (Телец → тельцовский)
    "телесьцовский": "тельцовский",
    "телецовский":   "тельцовский",
    # Cancer (Рак → раковский)
    "ракoвский":  "раковский",   # mixed latin 'o'
    "ракевский":  "раковский",
    # Scorpio (Скорпион → скорпионий / скорпионский)
    "скорпионовский": "скорпионский",
    # Libra (Весы → весовский)
    "веснодский":  "весовский",
    "весовский":   "весовский",   # idempotent
}


_TYPO_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _KNOWN_TYPOS) + r")\b",
    re.IGNORECASE,
)


def polish_natal_text(text: str) -> tuple[str, int]:
    """Apply the zodiac-adjective typo dictionary. Whole-word, case-
    preserving for the first character so «Козеджий» becomes «Козерожий»
    while «козеджий» becomes «козерожий».

    Returns (clean_text, num_replacements).
    """
    if not text:
        return text, 0
    fixes = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal fixes
        original = m.group(0)
        canon = _KNOWN_TYPOS[original.lower()]
        if canon == original.lower() and canon == original:
            return original
        fixes += 1
        if original[0].isupper():
            return canon[0].upper() + canon[1:]
        return canon

    return _TYPO_RE.sub(repl, text), fixes
