"""Generate natal chart PDF report using ReportLab."""
import os
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Register DejaVu Sans — supports Cyrillic + astro symbols
_FONT_DIR = os.path.join(os.path.dirname(__file__), '..', 'fonts')
_FONT_REGISTERED = False

def _register_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    try:
        # Try system DejaVu (available in most Linux Docker images)
        for path in [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/dejavu/DejaVuSans.ttf',
            os.path.join(_FONT_DIR, 'DejaVuSans.ttf'),
        ]:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont('DejaVu', path))
                bold_path = path.replace('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf')
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont('DejaVu-Bold', bold_path))
                else:
                    pdfmetrics.registerFont(TTFont('DejaVu-Bold', path))
                _FONT_REGISTERED = True
                return
    except Exception:
        pass
    _FONT_REGISTERED = True  # avoid retrying

FONT = 'DejaVu'
FONT_BOLD = 'DejaVu-Bold'

# Colors
GOLD = HexColor('#d4b254')
GOLD_DIM = HexColor('#8a7a3a')
TEXT = HexColor('#f0ecf8')
TEXT_DIM = HexColor('#9d97b4')
BG = HexColor('#07060f')
SURFACE = HexColor('#0e0b20')

SIGN_SYMBOLS = {
    'aries': '♈', 'taurus': '♉', 'gemini': '♊', 'cancer': '♋',
    'leo': '♌', 'virgo': '♍', 'libra': '♎', 'scorpio': '♏',
    'sagittarius': '♐', 'capricorn': '♑', 'aquarius': '♒', 'pisces': '♓',
}
SIGN_RU = {
    'aries': 'Овен', 'taurus': 'Телец', 'gemini': 'Близнецы', 'cancer': 'Рак',
    'leo': 'Лев', 'virgo': 'Дева', 'libra': 'Весы', 'scorpio': 'Скорпион',
    'sagittarius': 'Стрелец', 'capricorn': 'Козерог', 'aquarius': 'Водолей', 'pisces': 'Рыбы',
}
PLANET_SYMBOLS = {
    'sun': '☉', 'moon': '☽', 'mercury': '☿', 'venus': '♀', 'mars': '♂',
    'jupiter': '♃', 'saturn': '♄', 'uranus': '♅', 'neptune': '♆', 'pluto': '♇',
}
PLANET_RU = {
    'sun': 'Солнце', 'moon': 'Луна', 'mercury': 'Меркурий', 'venus': 'Венера',
    'mars': 'Марс', 'jupiter': 'Юпитер', 'saturn': 'Сатурн',
    'uranus': 'Уран', 'neptune': 'Нептун', 'pluto': 'Плутон',
}
ASPECT_SYMBOLS = {
    'conjunction': '☌', 'trine': '△', 'sextile': '⚹',
    'square': '□', 'opposition': '☍', 'quincunx': '⚻',
}
ASPECT_RU = {
    'conjunction': 'Соединение', 'trine': 'Трин', 'sextile': 'Секстиль',
    'square': 'Квадрат', 'opposition': 'Оппозиция', 'quincunx': 'Квинконс',
}


def _deg_str(deg: float) -> str:
    d = int(deg % 30)
    m = int(((deg % 30) - d) * 60)
    return f"{d}°{m:02d}'"


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
) -> bytes:
    """Generate a natal chart PDF and return as bytes."""
    _register_fonts()
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4  # 595 x 842 points

    # ── Page 1: Cover ────────────────────────────────────────────────
    c.setFillColor(BG)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    c.setFillColor(GOLD)
    c.setFont("DejaVu-Bold", 28)
    c.drawCentredString(w/2, h - 200, "НАТАЛЬНАЯ КАРТА")

    c.setFont("DejaVu", 14)
    c.setFillColor(TEXT)
    c.drawCentredString(w/2, h - 240, "Персональный астрологический отчёт")

    c.setFont("DejaVu", 12)
    c.setFillColor(TEXT_DIM)
    c.drawCentredString(w/2, h - 300, user_name)
    c.drawCentredString(w/2, h - 320, f"{birth_date}  {birth_time or ''}")
    c.drawCentredString(w/2, h - 340, birth_city)

    # Sun/Moon/Asc
    c.setFont("DejaVu-Bold", 16)
    c.setFillColor(GOLD)
    y = h - 420
    signs_line = f"☉ {SIGN_RU.get(sun_sign, sun_sign)}"
    if moon_sign:
        signs_line += f"  ·  ☽ {SIGN_RU.get(moon_sign, moon_sign)}"
    if asc_sign:
        signs_line += f"  ·  ↑ {SIGN_RU.get(asc_sign, asc_sign)}"
    c.drawCentredString(w/2, y, signs_line)

    c.setFont("DejaVu", 9)
    c.setFillColor(TEXT_DIM)
    c.drawCentredString(w/2, 60, "Astro TMA · astro-tma.vercel.app")

    c.showPage()

    # ── Page 2: Planets in Signs ─────────────────────────────────────
    c.setFillColor(BG)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    c.setFillColor(GOLD)
    c.setFont("DejaVu-Bold", 20)
    c.drawString(40, h - 50, "Планеты в знаках")

    y = h - 90
    c.setFont("DejaVu", 10)

    for name in ['sun','moon','mercury','venus','mars','jupiter','saturn','uranus','neptune','pluto']:
        p = planets.get(name, {})
        if not p:
            continue

        sign = p.get('sign', '')
        sign_ru = SIGN_RU.get(sign, sign)
        degree = p.get('degree', 0)
        sign_degree = p.get('sign_degree', degree % 30)
        house = p.get('house', 0)
        retro = p.get('retrograde', False)

        c.setFillColor(GOLD)
        c.setFont("DejaVu-Bold", 11)
        c.drawString(40, y, f"{PLANET_SYMBOLS.get(name, '')} {PLANET_RU.get(name, name)}")

        c.setFillColor(TEXT)
        c.setFont("DejaVu", 10)
        retro_str = ' ℞' if retro else ''
        c.drawString(180, y, f"{SIGN_SYMBOLS.get(sign, '')} {sign_ru}  {_deg_str(sign_degree)}{retro_str}")
        c.drawString(380, y, f"Дом {house}")

        y -= 22
        if y < 60:
            c.showPage()
            c.setFillColor(BG)
            c.rect(0, 0, w, h, fill=1, stroke=0)
            y = h - 50

    c.showPage()

    # ── Page 3: House Cusps ──────────────────────────────────────────
    c.setFillColor(BG)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    c.setFillColor(GOLD)
    c.setFont("DejaVu-Bold", 20)
    c.drawString(40, h - 50, "Куспиды домов")

    y = h - 90
    axis_labels = {1: 'Асцендент', 4: 'IC', 7: 'Десцендент', 10: 'MC'}

    for house in houses:
        num = house.get('number', 0)
        sign = house.get('sign', '')
        sign_ru = SIGN_RU.get(sign, sign)
        deg = house.get('degree', 0)

        c.setFillColor(GOLD if num in axis_labels else TEXT_DIM)
        c.setFont("DejaVu-Bold" if num in axis_labels else "DejaVu", 10)
        c.drawString(40, y, f"Дом {num}")

        c.setFillColor(TEXT)
        c.setFont("DejaVu", 10)
        c.drawString(120, y, f"{SIGN_SYMBOLS.get(sign, '')} {sign_ru}")
        c.drawString(250, y, _deg_str(deg))

        if num in axis_labels:
            c.setFillColor(GOLD_DIM)
            c.setFont("DejaVu", 9)
            c.drawString(320, y, f"({axis_labels[num]})")

        y -= 20

    c.showPage()

    # ── Page 4: Aspects ──────────────────────────────────────────────
    c.setFillColor(BG)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    c.setFillColor(GOLD)
    c.setFont("DejaVu-Bold", 20)
    c.drawString(40, h - 50, "Аспекты")

    y = h - 90

    for aspect_type in ['conjunction','trine','sextile','square','opposition','quincunx']:
        group = [a for a in aspects if a.get('aspect') == aspect_type]
        if not group:
            continue

        c.setFillColor(GOLD)
        c.setFont("DejaVu-Bold", 12)
        sym = ASPECT_SYMBOLS.get(aspect_type, '')
        name = ASPECT_RU.get(aspect_type, aspect_type)
        c.drawString(40, y, f"{sym} {name}")
        y -= 18

        for a in group:
            p1 = PLANET_RU.get(a['p1'], a['p1'])
            p2 = PLANET_RU.get(a['p2'], a['p2'])
            orb = a.get('orb', 0)

            c.setFillColor(TEXT)
            c.setFont("DejaVu", 10)
            c.drawString(60, y, f"{PLANET_SYMBOLS.get(a['p1'],'')} {p1}  {sym}  {PLANET_SYMBOLS.get(a['p2'],'')} {p2}")
            c.setFillColor(TEXT_DIM)
            c.drawString(350, y, f"орб {orb:.1f}°")
            y -= 16

        y -= 8
        if y < 60:
            c.showPage()
            c.setFillColor(BG)
            c.rect(0, 0, w, h, fill=1, stroke=0)
            y = h - 50

    c.showPage()

    # ── Page 5: LLM Reading (if available) ───────────────────────────
    if reading:
        c.setFillColor(BG)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        c.setFillColor(GOLD)
        c.setFont("DejaVu-Bold", 20)
        c.drawString(40, h - 50, "Персональная интерпретация")

        # Simple text wrapping
        y = h - 90
        c.setFillColor(TEXT)
        c.setFont("DejaVu", 10)

        for line in reading.split('\n'):
            line = line.strip()
            if not line:
                y -= 10
                continue

            # Bold section headers
            if line.startswith('**') and line.endswith('**'):
                c.setFillColor(GOLD)
                c.setFont("DejaVu-Bold", 11)
                c.drawString(40, y, line.strip('* '))
                c.setFillColor(TEXT)
                c.setFont("DejaVu", 10)
                y -= 18
                continue

            # Word wrap at ~90 chars
            words = line.split()
            current_line = ""
            for word in words:
                test = f"{current_line} {word}".strip()
                if len(test) > 90:
                    c.drawString(40, y, current_line)
                    y -= 14
                    current_line = word
                    if y < 60:
                        c.showPage()
                        c.setFillColor(BG)
                        c.rect(0, 0, w, h, fill=1, stroke=0)
                        y = h - 50
                        c.setFillColor(TEXT)
                        c.setFont("DejaVu", 10)
                else:
                    current_line = test

            if current_line:
                c.drawString(40, y, current_line)
                y -= 14

            if y < 60:
                c.showPage()
                c.setFillColor(BG)
                c.rect(0, 0, w, h, fill=1, stroke=0)
                y = h - 50
                c.setFillColor(TEXT)
                c.setFont("DejaVu", 10)

        c.showPage()

    # ── Final page: Footer ───────────────────────────────────────────
    c.setFillColor(BG)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    c.setFillColor(GOLD)
    c.setFont("DejaVu-Bold", 18)
    c.drawCentredString(w/2, h/2 + 40, "Спасибо")

    c.setFillColor(TEXT_DIM)
    c.setFont("DejaVu", 11)
    c.drawCentredString(w/2, h/2, "Этот отчёт создан для вашего")
    c.drawCentredString(w/2, h/2 - 16, "понимания космического пути.")

    c.setFont("DejaVu", 9)
    c.drawCentredString(w/2, 80, "Astro TMA · astro-tma.vercel.app")

    c.showPage()
    c.save()

    return buf.getvalue()
