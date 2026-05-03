"""Generate the premium natal chart PDF report using ReportLab."""

from __future__ import annotations

import math
import os
import re
from io import BytesIO
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4

# Figma: ASTRO / "PDF Report" / node 5:3.
BG = HexColor("#0a0906")
SURFACE = HexColor("#141210")
BORDER = HexColor("#2e2b24")
GOLD = HexColor("#c4a35a")
GOLD_DARK = HexColor("#8a7240")
GOLD_FAINT = HexColor("#4a3d20")
TEXT = HexColor("#ede8de")
BODY = HexColor("#c8c2b2")
MUTED = HexColor("#7a7468")
DEEP_MUTED = HexColor("#4a4840")
FIRE = HexColor("#a85a5a")
EARTH = HexColor("#5a9e7a")
AIR = HexColor("#c4a35a")
WATER = HexColor("#5a7aa8")

_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
_FONT_REGISTERED = False
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_SERIF = "Times-Roman"
FONT_SERIF_ITALIC = "Times-Italic"

SIGN_ORDER = [
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
]

SIGN_META: dict[str, dict[str, str]] = {
    "aries": {"ru": "Овен", "glyph": "♈", "element": "fire", "quality": "cardinal"},
    "taurus": {"ru": "Телец", "glyph": "♉", "element": "earth", "quality": "fixed"},
    "gemini": {"ru": "Близнецы", "glyph": "♊", "element": "air", "quality": "mutable"},
    "cancer": {"ru": "Рак", "glyph": "♋", "element": "water", "quality": "cardinal"},
    "leo": {"ru": "Лев", "glyph": "♌", "element": "fire", "quality": "fixed"},
    "virgo": {"ru": "Дева", "glyph": "♍", "element": "earth", "quality": "mutable"},
    "libra": {"ru": "Весы", "glyph": "♎", "element": "air", "quality": "cardinal"},
    "scorpio": {"ru": "Скорпион", "glyph": "♏", "element": "water", "quality": "fixed"},
    "sagittarius": {"ru": "Стрелец", "glyph": "♐", "element": "fire", "quality": "mutable"},
    "capricorn": {"ru": "Козерог", "glyph": "♑", "element": "earth", "quality": "cardinal"},
    "aquarius": {"ru": "Водолей", "glyph": "♒", "element": "air", "quality": "fixed"},
    "pisces": {"ru": "Рыбы", "glyph": "♓", "element": "water", "quality": "mutable"},
}

PLANET_SYMBOLS = {
    "sun": "☉",
    "moon": "☽",
    "mercury": "☿",
    "venus": "♀",
    "mars": "♂",
    "jupiter": "♃",
    "saturn": "♄",
    "uranus": "♅",
    "neptune": "♆",
    "pluto": "♇",
}

PLANET_RU = {
    "sun": "Солнце",
    "moon": "Луна",
    "mercury": "Меркурий",
    "venus": "Венера",
    "mars": "Марс",
    "jupiter": "Юпитер",
    "saturn": "Сатурн",
    "uranus": "Уран",
    "neptune": "Нептун",
    "pluto": "Плутон",
}

ASPECT_SYMBOLS = {
    "conjunction": "☌",
    "trine": "△",
    "sextile": "⚹",
    "square": "□",
    "opposition": "☍",
    "quincunx": "⚻",
}

ASPECT_RU = {
    "conjunction": "Соединение",
    "trine": "Трин",
    "sextile": "Секстиль",
    "square": "Квадрат",
    "opposition": "Оппозиция",
    "quincunx": "Квинконс",
}

ASPECT_HINTS = {
    "conjunction": "Слияние энергий",
    "trine": "Гармония и лёгкость",
    "sextile": "Возможность и поддержка",
    "square": "Напряжение и рост",
    "opposition": "Баланс противоположностей",
    "quincunx": "Тонкая настройка",
}

HOUSE_THEMES = {
    1: "Личность",
    2: "Ресурсы",
    3: "Голос",
    4: "Корни",
    5: "Творчество",
    6: "Здоровье",
    7: "Партнёрство",
    8: "Трансформация",
    9: "Смысл",
    10: "Призвание",
    11: "Сообщества",
    12: "Тайны",
}

AXIS_LABELS = {1: "AC", 4: "IC", 7: "DC", 10: "MC"}

SIGN_TRAITS = {
    "aries": ["Инициатива", "Смелость", "Импульс", "Прямота", "Огонь"],
    "taurus": ["Устойчивость", "Чувственность", "Верность", "Ритм", "Опора"],
    "gemini": ["Любопытство", "Гибкость", "Речь", "Связи", "Лёгкость"],
    "cancer": ["Забота", "Память", "Интуиция", "Дом", "Защита"],
    "leo": ["Сердце", "Творчество", "Смелость", "Тепло", "Сцена"],
    "virgo": ["Точность", "Польза", "Анализ", "Ремесло", "Забота"],
    "libra": ["Гармония", "Выбор", "Эстетика", "Тактичность", "Союз"],
    "scorpio": ["Глубина", "Интуиция", "Решимость", "Преданность", "Трансформация"],
    "sagittarius": ["Горизонт", "Смысл", "Вера", "Поиск", "Свобода"],
    "capricorn": ["Структура", "Выдержка", "Цель", "Опыт", "Опора"],
    "aquarius": ["Идеи", "Свобода", "Дружба", "Будущее", "Оригинальность"],
    "pisces": ["Эмпатия", "Сны", "Мягкость", "Воображение", "Служение"],
}

SIGN_MOTTO = {
    "aries": "Первый импульс",
    "taurus": "Тело и ценность",
    "gemini": "Живой разум",
    "cancer": "Память сердца",
    "leo": "Свет изнутри",
    "virgo": "Точность заботы",
    "libra": "Искусство равновесия",
    "scorpio": "Глубина и страсть",
    "sagittarius": "Дальний горизонт",
    "capricorn": "Путь вершины",
    "aquarius": "Свобода идеи",
    "pisces": "Тонкие воды",
}

ELEMENT_COPY = {
    "fire": "Ваша карта говорит языком импульса: важно действовать, пробовать и не терять внутренний огонь.",
    "earth": "Сила проявляется через устойчивость, телесность, практичные решения и уважение к реальному ритму.",
    "air": "Ключ к себе лежит через мысли, диалоги, обучение и способность соединять людей и идеи.",
    "water": "Главная настройка карты - чувствительность, память, интуиция и умение слышать подводные течения.",
}

QUALITY_COPY = {
    "cardinal": "Кардинальная энергия запускает процессы и помогает первой делать шаг в новую реальность.",
    "fixed": "Фиксированная энергия удерживает направление, создаёт глубину и не бросает важное на полпути.",
    "mutable": "Мутабельная энергия быстро адаптируется, связывает разные миры и находит обходные маршруты.",
}

ELEMENT_LABELS = {
    "fire": ("Огонь", "△", FIRE),
    "earth": ("Земля", "▽", EARTH),
    "air": ("Воздух", "△", AIR),
    "water": ("Вода", "▽", WATER),
}

QUALITY_LABELS = {
    "cardinal": ("Кардинальные", "инициация, начала"),
    "fixed": ("Фиксированные", "устойчивость, упорство"),
    "mutable": ("Мутабельные", "адаптация, гибкость"),
}


def _try_register_font(name: str, paths: list[str]) -> str | None:
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            return name
        except Exception:
            continue
    return None


def _register_fonts() -> None:
    """Register Cyrillic-capable fonts with macOS/Linux fallbacks."""
    global _FONT_REGISTERED, FONT, FONT_BOLD, FONT_SERIF, FONT_SERIF_ITALIC
    if _FONT_REGISTERED:
        return

    regular = _try_register_font(
        "AstroSans",
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            os.path.join(_FONT_DIR, "DejaVuSans.ttf"),
        ],
    )
    bold = _try_register_font(
        "AstroSans-Bold",
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf"),
        ],
    )
    serif = _try_register_font(
        "AstroSerif",
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        ],
    )
    serif_italic = _try_register_font(
        "AstroSerif-Italic",
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
            "/usr/share/fonts/dejavu/DejaVuSerif-Italic.ttf",
            "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
            "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
        ],
    )

    FONT = regular or FONT
    FONT_BOLD = bold or regular or FONT_BOLD
    FONT_SERIF = serif or regular or FONT_SERIF
    FONT_SERIF_ITALIC = serif_italic or serif or regular or FONT_SERIF_ITALIC
    _FONT_REGISTERED = True


def _top(top: float) -> float:
    return PAGE_H - top


def _baseline(top: float, size: float) -> float:
    return PAGE_H - top - size


def _text(
    c: canvas.Canvas,
    x: float,
    top: float,
    text: str,
    *,
    font: str | None = None,
    size: float = 11,
    color=BODY,
    center: bool = False,
    right: bool = False,
) -> None:
    font = font or FONT
    c.setFillColor(color)
    c.setFont(font, size)
    y = _baseline(top, size * 0.9)
    if center:
        c.drawCentredString(x, y, text)
    elif right:
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)


def _line(c: canvas.Canvas, x1: float, y_top: float, x2: float, y2_top: float, color=GOLD_FAINT) -> None:
    c.setStrokeColor(color)
    c.setLineWidth(0.5)
    c.line(x1, _top(y_top), x2, _top(y2_top))


def _wrap(text: str, width: float, font: str, size: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and pdfmetrics.stringWidth(candidate, font, size) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _paragraph(
    c: canvas.Canvas,
    x: float,
    top: float,
    text: str,
    *,
    width: float = 483,
    font: str | None = None,
    size: float = 11,
    line_height: float = 19,
    color=BODY,
    max_lines: int | None = None,
) -> float:
    font = font or FONT
    lines = _wrap(text, width, font, size)
    if max_lines is not None:
        lines = lines[:max_lines]
    for i, line in enumerate(lines):
        _text(c, x, top + i * line_height, line, font=font, size=size, color=color)
    return top + len(lines) * line_height


def _section_label(c: canvas.Canvas, x: float, top: float, label: str) -> None:
    _text(c, x, top, f"✦   {label.upper()}", font=FONT, size=9, color=GOLD)


def _divider(c: canvas.Canvas, top: float, *, width: float = 86) -> None:
    cx = PAGE_W / 2
    _line(c, cx - width - 14, top, cx - 14, top, GOLD_FAINT)
    _text(c, cx, top - 6, "✦", font=FONT, size=11, color=GOLD, center=True)
    _line(c, cx + 14, top, cx + width + 14, top, GOLD_FAINT)


def _page_frame(c: canvas.Canvas, page_number: int | None = None) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    for x, top in ((28, 28), (555, 28), (28, 802), (555, 802)):
        _text(c, x, top, "✦", font=FONT, size=12, color=GOLD_DARK)
    if page_number:
        _text(
            c,
            PAGE_W / 2,
            804,
            f"{page_number} · ASTROGUIDE",
            font=FONT,
            size=8,
            color=DEEP_MUTED,
            center=True,
        )


def _header(c: canvas.Canvas, chapter: str, title: str) -> None:
    _section_label(c, 56, 56, chapter)
    _text(c, 56, 76, title, font=FONT_BOLD, size=22, color=TEXT)
    _line(c, 56, 110, 116, 110, GOLD_FAINT)


def _card(c: canvas.Canvas, x: float, top: float, w: float, h: float, radius: float = 12) -> None:
    c.setFillColor(SURFACE)
    c.roundRect(x, _top(top + h), w, h, radius, fill=1, stroke=0)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.7)
    c.roundRect(x, _top(top + h), w, h, radius, fill=0, stroke=1)


def _pill(c: canvas.Canvas, x: float, top: float, text: str) -> float:
    width = pdfmetrics.stringWidth(text, FONT, 10) + 24
    c.setFillColor(SURFACE)
    c.roundRect(x, _top(top + 24), width, 24, 12, fill=1, stroke=0)
    c.setStrokeColor(GOLD_FAINT)
    c.setLineWidth(0.6)
    c.roundRect(x, _top(top + 24), width, 24, 12, fill=0, stroke=1)
    _text(c, x + 12, top + 6, text, font=FONT, size=10, color=GOLD)
    return width


def _norm_key(value: Any) -> str:
    return re.sub(r"[^a-z]", "", str(value or "").lower())


def _sign_key(value: Any) -> str:
    key = _norm_key(value)
    aliases = {
        "ari": "aries",
        "tau": "taurus",
        "gem": "gemini",
        "can": "cancer",
        "sco": "scorpio",
        "sag": "sagittarius",
        "cap": "capricorn",
        "aqu": "aquarius",
        "pis": "pisces",
    }
    return aliases.get(key, key)


def _sign_ru(value: Any) -> str:
    key = _sign_key(value)
    return SIGN_META.get(key, {}).get("ru", str(value or "—"))


def _planet_key(value: Any) -> str:
    key = _norm_key(value)
    aliases = {
        "sun": "sun",
        "moon": "moon",
        "mercury": "mercury",
        "venus": "venus",
        "mars": "mars",
        "jupiter": "jupiter",
        "saturn": "saturn",
        "uranus": "uranus",
        "neptune": "neptune",
        "pluto": "pluto",
    }
    return aliases.get(key, key)


def _degree(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def _degree_str(deg: float) -> str:
    deg = deg % 30
    d = int(deg)
    m = int(round((deg - d) * 60))
    if m == 60:
        d += 1
        m = 0
    return f"{d}°{m:02d}′"


def _house_roman(num: int) -> str:
    romans = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
    return romans[num] if 0 < num < len(romans) else str(num)


def _format_birth_date(value: str) -> str:
    try:
        year, month, day = value[:10].split("-")
    except ValueError:
        return value
    months = [
        "",
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ]
    return f"{int(day)} {months[int(month)]} {year}"


def _coords(lat: float | None, lng: float | None, tz: str | None) -> str:
    parts: list[str] = []
    if lat is not None and lng is not None:
        ns = "N" if lat >= 0 else "S"
        ew = "E" if lng >= 0 else "W"
        parts.append(f"{abs(lat):.4f}° {ns} · {abs(lng):.4f}° {ew}")
    if tz:
        parts.append(tz)
    return " · ".join(parts)


def _planet(planets: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    return planets.get(key) or planets.get(key.capitalize()) or {}


def _dominant(values: dict[str, int]) -> str:
    if not values:
        return ""
    return max(values.items(), key=lambda item: item[1])[0]


def _element_counts(planets: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {key: 0 for key in ELEMENT_LABELS}
    for data in planets.values():
        element = SIGN_META.get(_sign_key(data.get("sign")), {}).get("element")
        if element in counts:
            counts[element] += 1
    return counts


def _quality_counts(planets: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {key: 0 for key in QUALITY_LABELS}
    for data in planets.values():
        quality = SIGN_META.get(_sign_key(data.get("sign")), {}).get("quality")
        if quality in counts:
            counts[quality] += 1
    return counts


def _moon_phase(planets: dict[str, dict[str, Any]]) -> tuple[str, int]:
    sun = _degree(_planet(planets, "sun").get("degree"))
    moon = _degree(_planet(planets, "moon").get("degree"))
    angle = (moon - sun) % 360
    illumination = int(round((1 - math.cos(math.radians(angle))) / 2 * 100))
    phases = [
        (22.5, "Новолуние"),
        (67.5, "Растущий серп"),
        (112.5, "Первая четверть"),
        (157.5, "Растущая луна"),
        (202.5, "Полнолуние"),
        (247.5, "Убывающая луна"),
        (292.5, "Третья четверть"),
        (337.5, "Убывающий серп"),
        (360.0, "Новолуние"),
    ]
    return next(name for limit, name in phases if angle < limit), illumination


def _draw_birth_wheel(c: canvas.Canvas, cx: float, cy_top: float, radius: float, *, labels: bool = True) -> None:
    cy = _top(cy_top)
    c.setStrokeColor(GOLD_FAINT)
    c.setLineWidth(0.75)
    c.circle(cx, cy, radius, fill=0, stroke=1)
    c.setDash(3, 4)
    c.circle(cx, cy, radius - 30, fill=0, stroke=1)
    c.setDash()
    c.circle(cx, cy, radius - 60, fill=0, stroke=1)

    for idx in range(12):
        angle = math.radians(90 - idx * 30)
        x1 = cx + math.cos(angle) * (radius - 60)
        y1 = cy + math.sin(angle) * (radius - 60)
        x2 = cx + math.cos(angle) * (radius - 30)
        y2 = cy + math.sin(angle) * (radius - 30)
        c.line(x1, y1, x2, y2)

    if labels:
        for idx, sign in enumerate(SIGN_ORDER):
            angle = math.radians(90 - idx * 30)
            x = cx + math.cos(angle) * (radius + 1)
            y = cy + math.sin(angle) * (radius + 1) - 6
            _text(c, x, PAGE_H - y - 9, SIGN_META[sign]["glyph"], font=FONT, size=18, color=GOLD, center=True)

    c.setFillColor(GOLD)
    c.circle(cx, cy, 8, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.circle(cx, cy, 18, fill=0, stroke=1)


def _draw_cover(
    c: canvas.Canvas,
    *,
    user_name: str,
    birth_date: str,
    birth_time: str | None,
    birth_city: str,
    asc_sign: str | None,
    birth_lat: float | None,
    birth_lng: float | None,
    birth_tz: str | None,
) -> None:
    _page_frame(c)
    _text(c, PAGE_W / 2, 84, "✦   ✦   ✦", font=FONT, size=10, color=GOLD, center=True)
    _text(c, PAGE_W / 2, 110, "НАТАЛЬНАЯ КАРТА", font=FONT_BOLD, size=10, color=GOLD, center=True)
    _draw_birth_wheel(c, PAGE_W / 2, 320, 140)

    asc = _sign_ru(asc_sign).upper() if asc_sign else "ВОСХОДЯЩИЙ ЗНАК"
    _text(c, PAGE_W / 2, 506, f"✦   {asc} ВОСХОДЯЩИЙ   ✦", font=FONT, size=10, color=GOLD, center=True)
    _text(c, PAGE_W / 2, 540, user_name, font=FONT_BOLD, size=32, color=TEXT, center=True)
    _text(c, PAGE_W / 2, 588, "«Рождённый звёздами»", font=FONT_SERIF_ITALIC, size=18, color=BODY, center=True)
    _divider(c, 644)

    date_line = _format_birth_date(birth_date)
    if birth_time:
        date_line = f"{date_line} · {birth_time}"
    _text(c, PAGE_W / 2, 670, date_line, font=FONT, size=13, color=BODY, center=True)
    _text(c, PAGE_W / 2, 692, birth_city or "Место рождения не указано", font=FONT, size=11, color=MUTED, center=True)
    _text(c, PAGE_W / 2, 712, _coords(birth_lat, birth_lng, birth_tz), font=FONT, size=9, color=DEEP_MUTED, center=True)
    _text(c, PAGE_W / 2, 772, "ASTROGUIDE", font=FONT_BOLD, size=10, color=GOLD, center=True)
    _text(
        c,
        PAGE_W / 2,
        792,
        "Ваша карта неба, рассказанная звёздами",
        font=FONT_SERIF_ITALIC,
        size=11,
        color=DEEP_MUTED,
        center=True,
    )


def _draw_intro(c: canvas.Canvas, *, sun_sign: str, moon_sign: str, asc_sign: str | None) -> None:
    _page_frame(c, 2)
    _header(c, "Вступление", "Ваша карта неба")

    c.setFillColor(GOLD)
    c.rect(56, _top(236), 4, 80, fill=1, stroke=0)
    quote = "«Я родился в момент, когда звёзды складывались именно так - и никогда более не сложатся точно так же.»"
    _paragraph(c, 76, 156, quote, width=260, font=FONT_SERIF_ITALIC, size=18, line_height=22, color=TEXT)

    y = 280
    y = _paragraph(
        c,
        56,
        y,
        "В момент вашего рождения небо имело уникальную конфигурацию. Эта карта - письмо от Вселенной, адресованное лично вам.",
        size=11,
        line_height=19,
        color=BODY,
    )
    y = _paragraph(
        c,
        56,
        y + 17,
        "В отчёте собраны главные опоры карты: Солнце, Луна, восходящий знак, дома, аспекты, стихии и качества.",
        size=11,
        line_height=19,
        color=BODY,
    )
    _paragraph(
        c,
        56,
        y + 17,
        "Читайте медленно. Карта рождения - не предсказание, а зеркало, в котором можно увидеть свой способ идти по миру.",
        size=11,
        line_height=19,
        color=BODY,
    )

    _divider(c, 516, width=106)
    _section_label(c, 56, 552, "Содержание")
    rows = [
        ("I", "Внутреннее Я", f"Солнце · {_sign_ru(sun_sign)}"),
        ("II", "Эмоциональный мир", f"Луна · {_sign_ru(moon_sign)}"),
        ("III", "Структура жизни", "12 домов · оси и углы"),
        ("IV", "Голос планет", "Аспекты и их интерпретация"),
        ("V", "Стихии и качества", "Распределение энергий"),
    ]
    for i, (num, title, meta) in enumerate(rows):
        row_top = 580 + i * 34
        _text(c, 56, row_top, num, font=FONT, size=12, color=GOLD)
        _text(c, 100, row_top, title, font=FONT_BOLD, size=13, color=TEXT)
        _text(c, 100, row_top + 18, meta, font=FONT, size=10, color=MUTED)
        _line(c, 56, row_top + 38, 539, row_top + 38, BORDER)

    if asc_sign:
        _text(c, 56, 768, f"AC · {_sign_ru(asc_sign)}", font=FONT, size=10, color=GOLD)


def _chapter_copy(sign: str, planet: str, house: int | None) -> list[str]:
    sign_key = _sign_key(sign)
    element = SIGN_META.get(sign_key, {}).get("element", "")
    quality = SIGN_META.get(sign_key, {}).get("quality", "")
    house_text = f" в {house}-м доме" if house else ""
    planet_ru = "Солнце" if planet == "sun" else "Луна"
    first = (
        f"{planet_ru} в знаке {_sign_ru(sign)}{house_text} показывает, как ваша энергия "
        f"ищет естественный путь выражения. {ELEMENT_COPY.get(element, '')}"
    )
    second = QUALITY_COPY.get(quality, "")
    if planet == "moon":
        second = (
            f"В эмоциональном мире знак {_sign_ru(sign)} раскрывается тоньше: через реакции, "
            f"привязанности, интуицию и способ восстанавливать внутреннее равновесие. {second}"
        )
    else:
        second = (
            f"Это не маска и не роль, а ядро воли. Когда вы действуете из сильной стороны "
            f"этого знака, решения становятся яснее. {second}"
        )
    third = (
        "Главная задача - не усиливать себя до напряжения, а найти форму, где природный ритм "
        "становится устойчивой опорой."
    )
    return [first, second, third]


def _draw_planet_orb(c: canvas.Canvas, x: float, top: float, symbol: str) -> None:
    cx = x + 48
    cy_top = top + 48
    cy = _top(cy_top)
    c.setStrokeColor(GOLD_FAINT)
    c.setLineWidth(0.75)
    c.circle(cx, cy, 48, fill=0, stroke=1)
    c.circle(cx, cy, 30, fill=0, stroke=1)
    c.circle(cx, cy, 10, fill=0, stroke=1)
    _text(c, cx, top + 24, symbol, font=FONT, size=36, color=GOLD, center=True)


def _draw_planet_chapter(
    c: canvas.Canvas,
    *,
    page_number: int,
    chapter: str,
    title: str,
    planet_key: str,
    planets: dict[str, dict[str, Any]],
) -> None:
    _page_frame(c, page_number)
    _header(c, chapter, title)

    planet = _planet(planets, planet_key)
    sign = planet.get("sign", "")
    house = planet.get("house")
    sign_degree = _degree(planet.get("sign_degree", planet.get("degree", 0)))
    sign_key = _sign_key(sign)

    _draw_planet_orb(c, 82, 140, PLANET_SYMBOLS[planet_key])
    _text(c, 220, 168, PLANET_RU[planet_key].upper(), font=FONT_BOLD, size=9, color=GOLD_DARK)
    _text(c, 220, 184, _sign_ru(sign), font=FONT_BOLD, size=32, color=TEXT)
    house_num = int(house or 0)
    house_line = f"{_degree_str(sign_degree)} · {_house_roman(house_num)} дом" if house_num else _degree_str(sign_degree)
    _text(c, 220, 224, house_line, font=FONT, size=12, color=MUTED)
    _text(
        c,
        220,
        250,
        f"«{SIGN_MOTTO.get(sign_key, 'Звёздный путь')}»",
        font=FONT_SERIF_ITALIC,
        size=16,
        color=GOLD,
    )

    c.setFillColor(GOLD)
    c.rect(56, _top(412), 4, 100, fill=1, stroke=0)
    quote = (
        "«Там, где карта показывает напряжение, часто спрятан самый точный источник силы.»"
        if planet_key == "sun"
        else "«Лунные воды текут там, где разум молчит. Это язык, на котором с вами говорит душа.»"
    )
    _paragraph(c, 76, 312, quote, width=260, font=FONT_SERIF_ITALIC, size=17, line_height=22, color=TEXT)

    y = 446 if planet_key == "sun" else 426
    for paragraph in _chapter_copy(sign, planet_key, house_num):
        y = _paragraph(c, 56, y, paragraph, size=10.5, line_height=19, color=BODY) + 12

    if planet_key == "sun":
        _divider(c, 666)
        _section_label(c, 56, 696, "Ключевые черты")
        x = 56
        for trait in SIGN_TRAITS.get(sign_key, SIGN_TRAITS["scorpio"]):
            x += _pill(c, x, 722, trait) + 6
    else:
        phase, illumination = _moon_phase(planets)
        _divider(c, 646)
        _section_label(c, 56, 678, "Луна в момент рождения")
        _card(c, 56, 696, 483, 60)
        _text(c, 76, 712, phase, font=FONT_BOLD, size=12, color=TEXT)
        element = SIGN_META.get(sign_key, {}).get("element", "")
        element_label = ELEMENT_LABELS.get(element, ("Стихия", "", GOLD))[0]
        _text(c, 76, 730, f"Освещённость {illumination}% · стихия {element_label}", font=FONT, size=10, color=MUTED)

    _text(c, 539, 770, "— из звёздных архивов", font=FONT_SERIF_ITALIC, size=10, color=GOLD, right=True)


def _draw_houses_wheel(c: canvas.Canvas, houses: list[dict[str, Any]]) -> None:
    cx, cy_top, radius = 200, 280, 110
    cy = _top(cy_top)
    c.setStrokeColor(GOLD_FAINT)
    c.setLineWidth(0.75)
    c.circle(cx, cy, radius, fill=0, stroke=1)
    c.circle(cx, cy, 70, fill=0, stroke=1)
    for idx in range(12):
        angle = math.radians(90 - idx * 30)
        c.line(
            cx + math.cos(angle) * 70,
            cy + math.sin(angle) * 70,
            cx + math.cos(angle) * radius,
            cy + math.sin(angle) * radius,
        )
        label_angle = math.radians(75 - idx * 30)
        _text(
            c,
            cx + math.cos(label_angle) * 92,
            PAGE_H - (cy + math.sin(label_angle) * 92) - 7,
            _house_roman(idx + 1),
            font=FONT,
            size=9,
            color=GOLD,
            center=True,
        )
    _text(c, cx - radius - 18, cy_top - 6, "AC", font=FONT_BOLD, size=10, color=GOLD)
    _text(c, cx, cy_top - radius - 16, "MC", font=FONT_BOLD, size=10, color=GOLD, center=True)
    _text(c, cx + radius + 18, cy_top - 6, "DC", font=FONT_BOLD, size=10, color=GOLD)

    for house in houses[:6]:
        num = int(house.get("number", 0))
        top = 180 + (num - 1) * 22
        _text(c, 340, top, _house_roman(num), font=FONT_BOLD, size=11, color=GOLD)
        _text(c, 372, top, HOUSE_THEMES.get(num, ""), font=FONT, size=11, color=BODY)


def _draw_houses(c: canvas.Canvas, houses: list[dict[str, Any]]) -> None:
    _page_frame(c, 5)
    _header(c, "Глава V", "Структура жизни")
    _draw_houses_wheel(c, houses)
    _paragraph(
        c,
        56,
        440,
        "12 домов натальной карты - это сферы жизни, через которые планеты выражают свою энергию. Каждый дом отвечает за свою область: от личности до коллективного бессознательного.",
        size=11,
        line_height=19,
        color=BODY,
    )
    _divider(c, 516)
    _section_label(c, 56, 552, "Вершины домов (куспиды)")

    for idx, house in enumerate(houses[:12]):
        col_x = 56 if idx < 6 else 336
        row = idx if idx < 6 else idx - 6
        top = 580 + row * 24
        num = int(house.get("number", idx + 1))
        sign = house.get("sign", "")
        deg = _degree(house.get("degree"))
        _text(c, col_x, top, _house_roman(num), font=FONT_BOLD, size=11, color=GOLD)
        _text(c, col_x + 28, top, _sign_ru(sign), font=FONT, size=11, color=BODY)
        axis = f" · {AXIS_LABELS[num]}" if num in AXIS_LABELS else ""
        _text(c, col_x + 110, top, f"{_degree_str(deg)}{axis}", font=FONT, size=10, color=MUTED)
        _line(c, col_x, top + 18, col_x + 220, top + 18, BORDER)


def _draw_aspect_type_card(c: canvas.Canvas, x: float, top: float, aspect: str) -> None:
    _text(c, x, top, f"{ASPECT_SYMBOLS[aspect]} {ASPECT_RU[aspect]}", font=FONT_BOLD, size=11, color=TEXT)
    _text(c, x, top + 15, ASPECT_HINTS[aspect], font=FONT, size=9, color=MUTED)


def _draw_aspects(c: canvas.Canvas, aspects: list[dict[str, Any]]) -> None:
    _page_frame(c, 6)
    _header(c, "Глава VI", "Голос планет")
    _paragraph(
        c,
        56,
        156,
        "Аспекты - это геометрические углы между планетами в вашей карте. Они рассказывают о внутренних диалогах: где гармония, где напряжение, где встречаются противоположности.",
        size=11,
        line_height=19,
        color=BODY,
    )

    _card(c, 56, 240, 483, 100)
    _section_label(c, 76, 256, "Типы аспектов")
    for i, aspect in enumerate(["trine", "square", "conjunction", "opposition"]):
        x = 90 if i % 2 == 0 else 320
        top = 280 if i < 2 else 304
        c.setFillColor(GOLD)
        c.circle(x - 11, _top(top + 5), 3, fill=1, stroke=0)
        _draw_aspect_type_card(c, x, top, aspect)

    _section_label(c, 56, 376, "Ваши ключевые аспекты")
    y = 400
    sorted_aspects = sorted(aspects, key=lambda item: _degree(item.get("orb")))[:7]
    if not sorted_aspects:
        _paragraph(c, 56, y, "В карте пока нет сохранённых аспектов для отображения.", size=11, color=BODY)
        return

    for aspect in sorted_aspects:
        aspect_type = _norm_key(aspect.get("aspect"))
        sym = ASPECT_SYMBOLS.get(aspect_type, "✦")
        p1 = _planet_key(aspect.get("p1"))
        p2 = _planet_key(aspect.get("p2"))
        _card(c, 56, y, 483, 50, radius=9)
        c.setFillColor(GOLD)
        c.rect(56, _top(y + 40), 3, 30, fill=1, stroke=0)
        line = (
            f"{PLANET_SYMBOLS.get(p1, '')} {PLANET_RU.get(p1, str(aspect.get('p1', '')))} "
            f"{sym} {PLANET_SYMBOLS.get(p2, '')} {PLANET_RU.get(p2, str(aspect.get('p2', '')))}"
        )
        _text(c, 76, y + 8, line, font=FONT_BOLD, size=12, color=TEXT)
        _text(c, 76, y + 28, ASPECT_HINTS.get(aspect_type, ASPECT_RU.get(aspect_type, aspect_type)), font=FONT, size=10, color=MUTED)
        _text(c, 485, y + 18, f"{_degree(aspect.get('orb')):.2f}°", font=FONT, size=10, color=BODY, right=True)
        y += 56


def _draw_element_card(
    c: canvas.Canvas,
    x: float,
    top: float,
    key: str,
    count: int,
    total: int,
) -> None:
    label, glyph, color = ELEMENT_LABELS[key]
    _card(c, x, top, 220, 76)
    c.setStrokeColor(color)
    c.setLineWidth(0.7)
    c.circle(x + 34, _top(top + 38), 18, fill=0, stroke=1)
    _text(c, x + 34, top + 28, glyph, font=FONT_BOLD, size=14, color=GOLD, center=True)
    _text(c, x + 64, top + 16, label, font=FONT_BOLD, size=14, color=TEXT)
    _text(c, x + 64, top + 36, f"{count} планет из {total}", font=FONT, size=10, color=MUTED)
    c.setFillColor(BORDER)
    c.roundRect(x + 64, _top(top + 59), 140, 3, 1.5, fill=1, stroke=0)
    c.setFillColor(color)
    c.roundRect(x + 64, _top(top + 59), 140 * (count / max(total, 1)), 3, 1.5, fill=1, stroke=0)


def _draw_quality_row(c: canvas.Canvas, top: float, key: str, count: int, total: int) -> None:
    label, desc = QUALITY_LABELS[key]
    _text(c, 56, top, label, font=FONT_BOLD, size=12, color=GOLD)
    _text(c, 200, top + 1, desc, font=FONT, size=10, color=MUTED)
    for i in range(10):
        c.setFillColor(GOLD if i < round((count / max(total, 1)) * 10) else BORDER)
        c.circle(383 + i * 10, _top(top + 8), 3, fill=1, stroke=0)


def _draw_elements_closing(c: canvas.Canvas, planets: dict[str, dict[str, Any]]) -> None:
    _page_frame(c, 7)
    _header(c, "Глава VII", "Стихии и качества")
    element_counts = _element_counts(planets)
    quality_counts = _quality_counts(planets)
    total = len([p for p in planets.values() if p])

    _section_label(c, 56, 156, "Распределение стихий")
    _draw_element_card(c, 56, 184, "fire", element_counts["fire"], total)
    _draw_element_card(c, 296, 184, "earth", element_counts["earth"], total)
    _draw_element_card(c, 56, 274, "air", element_counts["air"], total)
    _draw_element_card(c, 296, 274, "water", element_counts["water"], total)

    _divider(c, 386)
    _section_label(c, 56, 416, "Качества")
    _draw_quality_row(c, 444, "cardinal", quality_counts["cardinal"], total)
    _draw_quality_row(c, 472, "fixed", quality_counts["fixed"], total)
    _draw_quality_row(c, 500, "mutable", quality_counts["mutable"], total)

    _divider(c, 546)
    _section_label(c, 56, 580, "Заключение")
    dominant_element = _dominant(element_counts)
    dominant_quality = _dominant(quality_counts)
    closing = "Карта рождения - это не предсказание. Это карта местности, по которой вам идти. Дорогу выбираете вы."
    _paragraph(c, 56, 600, f"«{closing}»", width=330, font=FONT_SERIF_ITALIC, size=17, line_height=22, color=TEXT)
    if dominant_element and dominant_quality:
        _paragraph(
            c,
            56,
            666,
            f"Главный акцент отчёта: {_sign_ru(dominant_element) if dominant_element in SIGN_META else ELEMENT_LABELS[dominant_element][0].lower()} "
            f"и {QUALITY_LABELS[dominant_quality][0].lower()} качества.",
            width=430,
            font=FONT,
            size=9,
            line_height=14,
            color=DEEP_MUTED,
        )
    _divider(c, 698, width=126)
    _text(c, PAGE_W / 2, 730, "ASTROGUIDE", font=FONT_BOLD, size=11, color=GOLD, center=True)
    _text(
        c,
        PAGE_W / 2,
        752,
        "Ваша карта неба, рассказанная звёздами",
        font=FONT_SERIF_ITALIC,
        size=11,
        color=BODY,
        center=True,
    )
    _text(c, PAGE_W / 2, 776, "✦   astroguide.app   ✦", font=FONT, size=9, color=DEEP_MUTED, center=True)


def generate_natal_pdf(
    user_name: str,
    birth_date: str,
    birth_time: str | None,
    birth_city: str,
    sun_sign: str,
    moon_sign: str,
    asc_sign: str | None,
    planets: dict,
    houses: list,
    aspects: list,
    reading: str | None = None,
    birth_lat: float | None = None,
    birth_lng: float | None = None,
    birth_tz: str | None = None,
) -> bytes:
    """Generate a Figma-inspired natal chart report and return PDF bytes."""
    _register_fonts()

    clean_planets: dict[str, dict[str, Any]] = {
        _planet_key(key): value for key, value in dict(planets or {}).items() if isinstance(value, dict)
    }
    clean_houses = [house for house in list(houses or []) if isinstance(house, dict)]
    clean_aspects = [aspect for aspect in list(aspects or []) if isinstance(aspect, dict)]

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Natal Chart Report")
    c.setAuthor("AstroGuide")

    _draw_cover(
        c,
        user_name=(user_name or "Гость").strip(),
        birth_date=birth_date or "",
        birth_time=birth_time,
        birth_city=birth_city or "",
        asc_sign=asc_sign,
        birth_lat=birth_lat,
        birth_lng=birth_lng,
        birth_tz=birth_tz,
    )
    c.showPage()

    _draw_intro(c, sun_sign=sun_sign, moon_sign=moon_sign, asc_sign=asc_sign)
    c.showPage()

    _draw_planet_chapter(
        c,
        page_number=3,
        chapter="Глава I",
        title="Внутреннее Я",
        planet_key="sun",
        planets=clean_planets,
    )
    c.showPage()

    _draw_planet_chapter(
        c,
        page_number=4,
        chapter="Глава II",
        title="Эмоциональный мир",
        planet_key="moon",
        planets=clean_planets,
    )
    c.showPage()

    _draw_houses(c, clean_houses)
    c.showPage()

    _draw_aspects(c, clean_aspects)
    c.showPage()

    _draw_elements_closing(c, clean_planets)
    c.showPage()

    # Keep the public argument intentionally: route compatibility and future
    # personalization are preserved, while this fixed 7-page design stays stable.
    _ = reading

    c.save()
    return buf.getvalue()
