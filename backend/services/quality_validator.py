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
    # Целевой объём секции в словах (из генератора). Если задан, тексты заметно
    # короче цели (< target * _THIN_RATIO) помечаются WARNING TOO_SHORT_THIN.
    # None → thin-проверка выключена: валидатор не знает «правильного» объёма
    # и остаётся самодостаточным (как в standalone-тестах).
    target_words: int | None = None


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

# Полу-заглушка: формально не обрезок, но заметно короче ЦЕЛЕВОГО объёма
# секции. Цель приходит из генератора (ctx.target_words = _MIN_FULL_WORDS),
# а не зашита здесь — иначе порог рассинхронится с промптом и любой штатный
# текст уйдёт в бесконечный repair. Берём долю от цели, чтобы ловить только
# реально проваленные тексты («Венера-60» при цели 90), а не штатный разброс.
_THIN_RATIO = 0.8

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
    "iq",
    "eq",
}

# Завершающие предложение символы — если текст кончается не на них, это обрыв.
_SENTENCE_END = (".", "!", "?", "…", "»", ")", '"', "”")

# Шаблонные фразы-болванки. Каждый матч — отдельный Issue.
# NB: «на личном уровне» и «поколенческий аспект» НЕ добавлены намеренно —
# это легитимные обороты в разборе высших планет (см. позитивный тест
# test_generational_allowed_in_outer_aspect). Ловим только пустые штампы.
_TEMPLATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"аспект возможности"),
    re.compile(r"потенциал раскрыва\w*"),
    re.compile(r"чем точнее орб"),
    re.compile(r"положение в \d*-?\s?м? ?доме уточня\w*"),
    re.compile(r"да[её]т возможность,?\s*котор\w+ важно осознанно использовать"),
    re.compile(r"важно осознанно использова\w*"),
    re.compile(r"это да[её]т возможность"),
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
    # Существительное м.р./ср.р. + (опц. наречие) + краткое прилагательное/прич.
    # ж.р. → битая склейка вроде «результат уже видна цель» (P2-5). Список
    # существительных узкий (частые в астро-текстах м./ср. род), краткие формы
    # ж.р. однозначно сигналят рассогласование.
    re.compile(
        r"\b(?:результат|итог|опыт|выбор|путь|дар|ресурс|потенциал|вектор|"
        r"урок|impulse|импульс|настрой|подход|стиль|характер|разум|ум|страх)\b"
        r"(?:\s+\w+){0,2}\s+(?:видна|видима|нужна|важна|готова|видны|нужны|важны|"
        r"заметна|ясна|сильна)\b",
        re.IGNORECASE | re.UNICODE,
    ),
)

# Падежная ошибка склейки: предлог «на» (требует винительного) + ключевое слово
# дома в именительном падеже. Ловим именно дефект шаблона со списком ключевых
# слов, не нормальные словосочетания вроде «на режим сна».
_CASE_AFTER_PREP = re.compile(
    r"\bна\s+(?:карьера|друзья|кризисы|смыслы|ценности|мышление|творчество|"
    r"партн[её]рство|подсознание|личность)\b"
    r"|\bна\s+[^.!?…]{0,80}\bработа\b",
    re.IGNORECASE | re.UNICODE,
)

# Ложная привязка к Асценденту/Восходу в тексте аспекта («Солнце на Асценденте Льва»).
_FALSE_ASC_ATTRIBUTION = re.compile(
    r"на\s+(?:асцендент\w*|восход\w*)\b", re.IGNORECASE | re.UNICODE
)

# Два одинаковых слова подряд (>=3 буквы).
_WORD_DUP = re.compile(r"\b([^\W\d_]{3,})\s+\1\b", re.IGNORECASE | re.UNICODE)

# Чужой алфавит (не кириллица/латиница) внутри русского текста: CJK, арабица,
# деванагари и т.п. Это всегда мусор генерации (haiku роняет «责任ности»), ловим
# как CRITICAL и регенерим. Латиница ловится отдельно (LATIN_IN_RUSSIAN).
_FOREIGN_SCRIPT = re.compile(
    r"[　-鿿가-힯؀-ۿऀ-ॿ぀-ヿ]",
    re.UNICODE,
)

# Латиница, приклеенная вплотную к кириллице (внутри одного «слова»):
# «Козеrog», «характеr». Это сломанное слово, а не отдельный англицизм —
# CRITICAL. Отдельная латиница (англицизм «Wars») ловится как WARNING ниже.
_MIXED_SCRIPT_WORD = re.compile(r"[А-Яа-яЁё][A-Za-z]|[A-Za-z][А-Яа-яЁё]", re.UNICODE)

# Рассогласование лица: местоимение «вы» (мн.ч., вежл.) + глагол в форме
# 2 л. ед.ч. («можешь») или 1 л. мн.ч. («можем»). Должно быть «вы можете».
# Список частых глаголов узкий, чтобы не ловить нормальные обороты.
_PERSON_MISMATCH = re.compile(
    r"\bвы\s+(?:\w+\s+){0,2}"
    r"(?:мож(?:ешь|ем)|хоч(?:ешь|ем)|долж(?:ен|на)|умеешь|умеем|"
    r"будешь|будем|зна(?:ешь|ем)|чувству(?:ешь|ем)|стрем(?:ишься|имся))\b",
    re.IGNORECASE | re.UNICODE,
)

# Перепутанный порядок «{знак} в {планета}» вместо «{планета} в {знаке}»:
# «Овен в Марсе», «Телец в Венере». Знаки — в именительном, планеты — в
# предложном (окончание -е/-и). Список планет в предложном падеже узкий.
_SIGN_NOM = "Овен|Телец|Близнецы|Рак|Лев|Дева|Весы|Скорпион|Стрелец|Козерог|Водолей|Рыбы"
_SIGN_PLANET_REVERSED = re.compile(
    rf"\b(?:{_SIGN_NOM})\s+в\s+"
    r"(?:Марсе|Солнце|Луне|Меркурии|Венере|Юпитере|Сатурне|Уране|Нептуне|Плутоне)\b",
    re.UNICODE,
)

# Частые опечатки LLM (морфология русского). Ключ — паттерн, значение — для лога.
_TYPO_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bцену[ею]те\b", re.IGNORECASE | re.UNICODE),  # ценуете → цените
)

_LATIN_TOKEN = re.compile(r"[A-Za-z]{2,}")
# Любой bold-span (для подсчёта слов: тело важнее, заголовки/выделения опускаем).
_HEADING = re.compile(r"\*\*.+?\*\*")
# Только bold, занимающий ВСЮ строку = заголовок секции. Inline-bold внутри
# абзаца (**Wars** посреди предложения) сюда не попадёт — его латиница должна
# ловиться как англицизм (finding №3).
_LINE_HEADING = re.compile(r"^[ \t]*\*\*.+?\*\*[ \t]*$", re.MULTILINE)
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def _strip_headings(text: str) -> str:
    return _HEADING.sub(" ", text)


def _strip_line_headings(text: str) -> str:
    return _LINE_HEADING.sub(" ", text)


def _word_count(text: str) -> int:
    return len(_WORD.findall(_strip_headings(text)))


# Замены лица: «вы можешь / вы можем» → «вы можете». Группа 1 — «вы …» (с
# опциональными словами между), группа 2 — битый глагол, который меняем на
# правильную форму 2 л. мн.ч. из _PERSON_FORMS.
_PERSON_FIX = re.compile(
    r"(\bвы\s+(?:\w+\s+){0,2})"
    r"(мож(?:ешь|ем)|хоч(?:ешь|ем)|зна(?:ешь|ем)|умеешь|умеем|"
    r"чувству(?:ешь|ем)|будешь|будем)\b",
    re.IGNORECASE | re.UNICODE,
)
_PERSON_FORMS = {
    "можешь": "можете",
    "можем": "можете",
    "хочешь": "хотите",
    "хочем": "хотите",
    "знаешь": "знаете",
    "знаем": "знаете",
    "умеешь": "умеете",
    "умеем": "умеете",
    "чувствуешь": "чувствуете",
    "чувствуем": "чувствуете",
    "будешь": "будете",
    "будем": "будете",
}


def _person_repl(m: re.Match[str]) -> str:
    verb = m.group(2)
    fixed = _PERSON_FORMS.get(verb.lower(), verb)
    if verb[:1].isupper():
        fixed = fixed.capitalize()
    return f"{m.group(1)}{fixed}"


def sanitize_ru_text(text: str) -> str:
    """Last-resort чистка текста перед записью в PDF/кеш.

    Снимает мусор генерации, который мог просочиться мимо регенерации:
    символы чужого алфавита (CJK и т.п.) и рассогласование лица («вы можешь»
    → «вы можете»). Чистый русский текст возвращается без изменений. Латиница
    НЕ трогается (легитимные аббревиатуры MC/IC/asc), её ловит валидатор.
    """
    if not text:
        return text
    # Чужой алфавит — просто выкидываем символы (они всегда мусор внутри слова).
    out = _FOREIGN_SCRIPT.sub("", text)
    # Лицо глагола: «вы можешь/можем» → «вы можете».
    out = _PERSON_FIX.sub(_person_repl, out)
    # Частая опечатка: «ценуете/ценуюте» → «цените».
    out = re.sub(r"\bцену([ею])те\b", "цените", out, flags=re.IGNORECASE | re.UNICODE)
    return out


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
        elif ctx.target_words:
            thin_floor = int(ctx.target_words * _THIN_RATIO)
            if words < thin_floor:
                issues.append(
                    Issue(
                        "TOO_SHORT_THIN",
                        Severity.WARNING,
                        f"Текст короче целевого объёма ({words} слов, "
                        f"цель ~{ctx.target_words}, порог {thin_floor})",
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

        # ── Чужой алфавит (CJK и т.п.) ───────────────────────────────
        # Мусор генерации haiku: «责任ности». Всегда CRITICAL → регенерация.
        m = _FOREIGN_SCRIPT.search(stripped)
        if m:
            issues.append(
                Issue(
                    "FOREIGN_SCRIPT",
                    Severity.CRITICAL,
                    "Символы чужого алфавита в русском тексте",
                    stripped[max(0, m.start() - 8) : m.start() + 12],
                )
            )

        # ── Сломанное слово: латиница вплотную к кириллице ───────────
        # «Козеrog», «характеr» — слово развалилось на двух алфавитах.
        # CRITICAL: это не англицизм, а битая генерация → регенерация.
        m = _MIXED_SCRIPT_WORD.search(_strip_line_headings(stripped))
        if m:
            issues.append(
                Issue(
                    "MIXED_SCRIPT_WORD",
                    Severity.CRITICAL,
                    "Слово из вперемешку кириллицы и латиницы",
                    stripped[max(0, m.start() - 6) : m.start() + 8],
                )
            )

        # ── Латиница в русском тексте ────────────────────────────────
        # Заголовки-строки **...** могут легитимно содержать латиницу (имена
        # секций), их вырезаем. Inline-bold **Wars** внутри абзаца НЕ заголовок —
        # его латиница остаётся под проверкой (finding №3).
        for token in _LATIN_TOKEN.findall(_strip_line_headings(stripped)):
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

        # ── Рассогласование лица: «вы можешь / вы можем» ─────────────
        m = _PERSON_MISMATCH.search(lower)
        if m:
            issues.append(
                Issue(
                    "PERSON_MISMATCH",
                    Severity.WARNING,
                    "Рассогласование лица глагола после «вы»",
                    stripped[m.start() : m.start() + 40],
                )
            )

        # ── Падежная ошибка «на» + именительный ──────────────────────
        m = _CASE_AFTER_PREP.search(lower)
        if m:
            issues.append(
                Issue(
                    "CASE_AFTER_PREP",
                    Severity.WARNING,
                    "Падежная ошибка: «на» + именительный падеж",
                    stripped[m.start() : m.start() + 60],
                )
            )

        # ── Ложная привязка к Асценденту в аспекте ───────────────────
        if ctx.section_kind == "aspect":
            m = _FALSE_ASC_ATTRIBUTION.search(lower)
            if m:
                issues.append(
                    Issue(
                        "FALSE_ASC_ATTRIBUTION",
                        Severity.WARNING,
                        "Ложная привязка аспекта к Асценденту/Восходу",
                        stripped[m.start() : m.start() + 60],
                    )
                )

        # ── Перепутанный порядок «знак в планете» ────────────────────
        m = _SIGN_PLANET_REVERSED.search(stripped)
        if m:
            issues.append(
                Issue(
                    "SIGN_PLANET_REVERSED",
                    Severity.WARNING,
                    "Перепутан порядок: «{знак} в {планете}» вместо «{планета} в {знаке}»",
                    stripped[m.start() : m.start() + 40],
                )
            )

        # ── Опечатки ─────────────────────────────────────────────────
        for pat in _TYPO_PATTERNS:
            m = pat.search(lower)
            if m:
                issues.append(
                    Issue(
                        "TYPO",
                        Severity.WARNING,
                        "Вероятная опечатка",
                        stripped[m.start() : m.start() + 30],
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
