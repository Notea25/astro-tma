"""Tests for premium natal PDF rendering."""

from services.natal_pdf import generate_natal_pdf


def test_generate_natal_pdf_smoke():
    planets = {
        "sun": {"sign": "Scorpio", "degree": 232.25, "sign_degree": 22.25, "house": 4},
        "moon": {"sign": "Pisces", "degree": 338.72, "sign_degree": 8.72, "house": 8},
        "mercury": {"sign": "Scorpio", "degree": 224.1, "sign_degree": 14.1, "house": 4},
        "venus": {"sign": "Libra", "degree": 199.4, "sign_degree": 19.4, "house": 3},
        "mars": {"sign": "Gemini", "degree": 76.2, "sign_degree": 16.2, "house": 11},
        "jupiter": {"sign": "Leo", "degree": 128.5, "sign_degree": 8.5, "house": 1},
        "saturn": {"sign": "Capricorn", "degree": 289.6, "sign_degree": 19.6, "house": 6},
        "uranus": {"sign": "Capricorn", "degree": 278.1, "sign_degree": 8.1, "house": 6},
        "neptune": {"sign": "Capricorn", "degree": 284.0, "sign_degree": 14.0, "house": 6},
        "pluto": {"sign": "Scorpio", "degree": 218.3, "sign_degree": 8.3, "house": 4},
    }
    houses = [
        {"number": i + 1, "sign": sign, "degree": i * 30 + 14.22}
        for i, sign in enumerate(
            [
                "Leo",
                "Virgo",
                "Libra",
                "Scorpio",
                "Sagittarius",
                "Capricorn",
                "Aquarius",
                "Pisces",
                "Aries",
                "Taurus",
                "Gemini",
                "Cancer",
            ]
        )
    ]
    aspects = [
        {"p1": "sun", "p2": "moon", "aspect": "trine", "orb": 2.15},
        {"p1": "venus", "p2": "mercury", "aspect": "conjunction", "orb": 0.44},
    ]

    pdf = generate_natal_pdf(
        "Антон Нечаев",
        "1990-11-15",
        "14:30",
        "Москва, Россия",
        "Scorpio",
        "Pisces",
        "Scorpio",
        planets,
        houses,
        aspects,
        birth_lat=55.7558,
        birth_lng=37.6173,
        birth_tz="Europe/Moscow",
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 50_000
    assert pdf.count(b"/Type /Page") >= 7
