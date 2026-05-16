"""Tests for natal PDF generation and temporary download links."""

from types import SimpleNamespace

import pytest
from fastapi.responses import Response

from services import natal_pdf
from services.natal_pdf import generate_natal_pdf


def _sample_chart():
    planets = {
        "sun": {
            "sign": "Scorpio",
            "sign_ru": "Скорпион",
            "degree": 224.1,
            "sign_degree": 14.1,
            "house": 9,
            "retrograde": False,
        },
        "moon": {
            "sign": "Aquarius",
            "sign_ru": "Водолей",
            "degree": 309.2,
            "sign_degree": 9.2,
            "house": 1,
            "retrograde": False,
        },
        "mercury": {
            "sign": "Sagittarius",
            "sign_ru": "Стрелец",
            "degree": 241.0,
            "sign_degree": 1.0,
            "house": 10,
            "retrograde": False,
        },
    }
    houses = [
        {"number": number, "sign": "Aries", "sign_ru": "Овен", "degree": number * 30.0}
        for number in range(1, 13)
    ]
    aspects = [{"p1": "Sun", "p2": "Moon", "aspect": "square", "orb": 1.2}]
    return planets, houses, aspects


def test_generate_natal_pdf_returns_pdf_with_incomplete_descriptions():
    planets, houses, aspects = _sample_chart()

    pdf = generate_natal_pdf(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
        descriptions={
            "planets": {"sun": {"full": "Полное описание Солнца. " * 20}},
            "houses": {},
            "aspects": [],
        },
    )

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 10_000


def test_generate_natal_pdf_does_not_require_dejavu_bold(monkeypatch):
    planets, houses, aspects = _sample_chart()
    monkeypatch.setattr(natal_pdf.os.path, "exists", lambda _path: False)
    monkeypatch.setattr(natal_pdf, "_FONT_REGISTERED", False)
    monkeypatch.setattr(natal_pdf, "FONT", "Helvetica")
    monkeypatch.setattr(natal_pdf, "FONT_BOLD", "Helvetica-Bold")

    pdf = generate_natal_pdf(
        user_name="Андрей",
        birth_date="2000-10-20",
        birth_time="12:00",
        birth_city="Минск",
        sun_sign="Scorpio",
        moon_sign="Aquarius",
        asc_sign="Aries",
        planets=planets,
        houses=houses,
        aspects=aspects,
    )

    assert pdf.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_create_natal_pdf_link_returns_temporary_download_payload(monkeypatch):
    from api.routes import natal

    async def fake_get_user(_db, user_id):
        return SimpleNamespace(id=user_id, tg_first_name="Андрей")

    calls = {}

    async def fake_cache_set(key, value, ttl):
        calls["key"] = key
        calls["value"] = value
        calls["ttl"] = ttl

    monkeypatch.setattr(natal, "_get_pdf_user_or_error", fake_get_user)
    monkeypatch.setattr(natal, "cache_set", fake_cache_set)
    monkeypatch.setattr(natal, "token_urlsafe", lambda _size: "token-123")

    payload = await natal.create_natal_pdf_link(tg_user={"id": 1001}, db=object())

    assert payload == {
        "download_url": "/natal/pdf-download/token-123",
        "filename": "natal_Андрей.pdf",
        "expires_in": 300,
    }
    assert calls == {
        "key": "natal:pdf-download:token-123",
        "value": {"user_id": 1001},
        "ttl": 300,
    }


@pytest.mark.asyncio
async def test_natal_pdf_token_download_does_not_require_telegram_auth(monkeypatch):
    from api.routes import natal

    async def fake_cache_get(key):
        assert key == "natal:pdf-download:token-123"
        return {"user_id": 1001}

    async def fake_get_user(_db, user_id):
        assert user_id == 1001
        return SimpleNamespace(id=user_id)

    async def fake_build_response(_db, user):
        assert user.id == 1001
        return Response(content=b"%PDF-test", media_type="application/pdf")

    monkeypatch.setattr(natal, "cache_get", fake_cache_get)
    monkeypatch.setattr(natal, "_get_pdf_user_or_error", fake_get_user)
    monkeypatch.setattr(natal, "_build_natal_pdf_response", fake_build_response)

    response = await natal.get_natal_pdf_by_token("token-123", db=object())

    assert response.body == b"%PDF-test"
    assert response.media_type == "application/pdf"
