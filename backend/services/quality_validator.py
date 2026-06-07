"""Качество LLM-текстов натального PDF.

Детектор находит «заглушки» и дефекты в сгенерированных интерпретациях до того,
как они попадут в платный PDF: слишком короткие/шаблонные тексты, обрыв на полуслове,
англицизмы в русском, рассогласование рода, поколенческие штампы в индивидуальном
разборе, дубли слов. Модуль самодостаточен и не зависит от astro-пайплайна.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass


class Severity(enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationContext:
    """Контекст проверяемого текста.

    section_kind: "planet_in_sign" | "house" | "aspect" | "synthesis"
    subject:      человекочитаемая тема ("Уран в Водолее", "5 дом", "Юпитер ⚹ Сатурн")
    gender:       "male" | "female" | None
    """

    section_kind: str
    subject: str
    gender: str | None = None


@dataclass(frozen=True)
class Issue:
    code: str
    severity: Severity
    message: str
    snippet: str = ""


# ── Пороги ───────────────────────────────────────────────────────────
# Ниже этого числа слов текст считаем заглушкой/обрезком (critical).
# Калибровка: Уран-кейс (~30 слов) ловится, generational-кейс (~58) и
# хорошие тексты (>100) — нет.
_MIN_WORDS = 50

# Латиница длиной >=2, кроме разрешённых аббревиатур (середина неба и т.п.).
_LATIN_ALLOWLIST = {
    "mc",
    "ic",
    "asc",
    "dsc",
    "pdf",
    "llm",
    "ai",
    "id",
    "ok",
}

# Завершающие предложение символы — если текст кончается не на них, это обрыв.
_SENTENCE_END = (".", "!", "?", "…", "»", ")", '"', "”")

# Шаблонные фразы-болванки. Каждый матч — отдельный Issue.
_TEMPLATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"аспект возможности"),
    re.compile(r"потенциал раскрыва\w* через осознанн"),
    re.compile(r"чем точнее орб,?\s*тем заметнее"),
    re.compile(r"положение в \d+-?\s?м? доме уточня\w*"),
    re.compile(r"да[её]т возможность,?\s*котор\w+ важно осознанно использовать"),
    re.compile(r"любовь и желание текут гармонично"),
    re.compile(r"раскрывает свой стиль через характерные реакции"),
)

# Поколенческие штампы — недопустимы в индивидуальном разборе планет/домов/синтеза,
# но допустимы в поколенческих аспектах (Уран-Плутон и т.п.).
_GENERATIONAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"поколени\w*\s+\d{4}"),
    re.compile(r"цифров\w*\s+поколени"),
)

# Рассогласование рода+числа: глагол/прич. ж.р. ед.ч. рядом с мн.ч.
_GENDER_NUMBER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"остал(?:ась|ся)\s+одни"),
    re.compile(r"одна\s+остал(?:ись)"),
)

# Два одинаковых слова подряд (>=3 буквы).
_WORD_DUP = re.compile(r"\b([^\W\d_]{3,})\s+\1\b", re.IGNORECASE | re.UNICODE)

_LATIN_TOKEN = re.compile(r"[A-Za-z]{2,}")
_HEADING = re.compile(r"\*\*.+?\*\*")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def _strip_headings(text: str) -> str:
    return _HEADING.sub(" ", text)


def _word_count(text: str) -> int:
    return len(_WORD.findall(_strip_headings(text)))


class TextValidator:
    def __init__(self, use_spellchecker: bool = True) -> None:
        self.use_spellchecker = use_spellchecker
        self._spell = None
        if use_spellchecker:
            self._spell = _load_spellchecker()

    def validate(self, text: str, ctx: ValidationContext) -> list[Issue]:
        issues: list[Issue] = []

        if not text or not text.strip():
            return [Issue("EMPTY", Severity.CRITICAL, "Пустой текст", "")]

        stripped = text.strip()
        lower = stripped.lower()

        # ── Длина ────────────────────────────────────────────────────
        words = _word_count(stripped)
        if words < _MIN_WORDS:
            issues.append(
                Issue(
                    "TOO_SHORT_CRITICAL",
                    Severity.CRITICAL,
                    f"Слишком короткий текст ({words} слов, минимум {_MIN_WORDS})",
                    stripped[:80],
                )
            )

        # ── Обрыв на полуслове ───────────────────────────────────────
        if stripped[-1] not in _SENTENCE_END:
            issues.append(
                Issue(
                    "TRUNCATED",
                    Severity.CRITICAL,
                    "Текст обрывается без завершающего знака препинания",
                    stripped[-60:],
                )
            )

        # ── Шаблонные фразы ──────────────────────────────────────────
        for pat in _TEMPLATE_PATTERNS:
            m = pat.search(lower)
            if m:
                issues.append(
                    Issue(
                        "TEMPLATE_PHRASE",
                        Severity.WARNING,
                        "Шаблонная фраза-болванка",
                        stripped[m.start() : m.start() + 80],
                    )
                )

        # ── Поколенческий штамп в индивидуальном разборе ─────────────
        if ctx.section_kind != "aspect":
            for pat in _GENERATIONAL_PATTERNS:
                m = pat.search(lower)
                if m:
                    issues.append(
                        Issue(
                            "GENERATIONAL_IN_INDIVIDUAL",
                            Severity.WARNING,
                            "Поколенческий штамп в индивидуальной интерпретации",
                            stripped[m.start() : m.start() + 80],
                        )
                    )
                    break

        # ── Латиница в русском тексте ────────────────────────────────
        for token in _LATIN_TOKEN.findall(stripped):
            if token.lower() in _LATIN_ALLOWLIST:
                continue
            issues.append(
                Issue(
                    "LATIN_IN_RUSSIAN",
                    Severity.WARNING,
                    f"Латинское слово в русском тексте: {token}",
                    token,
                )
            )
            break

        # ── Рассогласование рода/числа ───────────────────────────────
        for pat in _GENDER_NUMBER_PATTERNS:
            m = pat.search(lower)
            if m:
                issues.append(
                    Issue(
                        "GENDER_NUMBER_MISMATCH",
                        Severity.WARNING,
                        "Рассогласование рода и числа",
                        stripped[m.start() : m.start() + 60],
                    )
                )
                break

        # ── Дубли слов ───────────────────────────────────────────────
        dup = _WORD_DUP.search(stripped)
        if dup:
            issues.append(
                Issue(
                    "WORD_DUPLICATION",
                    Severity.WARNING,
                    f"Повтор слова подряд: {dup.group(1)}",
                    dup.group(0),
                )
            )

        # ── Орфография (опционально) ─────────────────────────────────
        if self._spell is not None:
            issues.extend(self._spellcheck(stripped))

        return issues

    def _spellcheck(self, text: str) -> list[Issue]:
        spell = self._spell
        if spell is None:
            return []
        tokens = [w for w in _WORD.findall(text) if len(w) >= 4]
        unknown = spell.unknown(tokens)
        out: list[Issue] = []
        for word in unknown:
            out.append(
                Issue(
                    "SPELLING",
                    Severity.WARNING,
                    f"Возможная опечатка: {word}",
                    word,
                )
            )
        return out


def _load_spellchecker():
    """Ленивая загрузка pyspellchecker. Нет либы — детектор просто выключен."""
    try:
        from spellchecker import SpellChecker  # type: ignore
    except ImportError:
        return None
    try:
        return SpellChecker(language="ru")
    except Exception:
        return None
