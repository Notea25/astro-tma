"""Unit tests for notification message formatting."""

from datetime import date

from db.models import User
from services.notifications.push import build_daily_message, build_open_app_markup


def _user() -> User:
    return User(id=1001, tg_first_name="Андрей")


def test_daily_message_hides_energy_stats():
    message = build_daily_message(
        _user(),
        sign_ru="Скорпион",
        text_ru="Сегодня лучше не спешить с выводами.",
        energy={"love": 91, "career": 72, "luck": 64},
        message_date=date(2026, 5, 16),
    )

    assert "91%" not in message
    assert "72%" not in message
    assert "64%" not in message
    assert "Любовь" not in message
    assert "Карьера" not in message
    assert "Удача" not in message


def test_daily_message_changes_by_date_even_with_same_horoscope():
    today = build_daily_message(
        _user(),
        sign_ru="Скорпион",
        text_ru="Информация не изменилась, но подача должна быть живой.",
        energy={},
        message_date=date(2026, 5, 16),
    )
    tomorrow = build_daily_message(
        _user(),
        sign_ru="Скорпион",
        text_ru="Информация не изменилась, но подача должна быть живой.",
        energy={},
        message_date=date(2026, 5, 17),
    )

    assert today != tomorrow
    assert "16 мая" in today
    assert "17 мая" in tomorrow


def test_open_app_markup_returns_webapp_button(monkeypatch):
    from core.settings import settings
    monkeypatch.setattr(settings, "TELEGRAM_WEBAPP_URL", "https://example.com/")

    markup = build_open_app_markup("Открыть")

    assert markup is not None
    assert markup["inline_keyboard"][0][0]["text"] == "Открыть"
    assert markup["inline_keyboard"][0][0]["web_app"]["url"] == "https://example.com/"


def test_open_app_markup_returns_none_when_url_missing(monkeypatch):
    from core.settings import settings
    monkeypatch.setattr(settings, "TELEGRAM_WEBAPP_URL", "")

    assert build_open_app_markup() is None
