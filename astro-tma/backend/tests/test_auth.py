"""
Tests for Telegram initData verification.
Uses real HMAC logic with a fake bot token.
"""

import hashlib, hmac, time, json
from urllib.parse import urlencode

import pytest

FAKE_TOKEN = "1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_init_data(user_id: int = 42, token: str = FAKE_TOKEN) -> str:
    """Construct a valid initData string for testing."""
    user_json = json.dumps({"id": user_id, "first_name": "Test", "language_code": "ru"})
    params = {
        "user": user_json,
        "auth_date": str(int(time.time())),
        "chat_instance": "123456",
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


def test_valid_init_data(monkeypatch):
    monkeypatch.setattr(
        "api.middleware.telegram_auth.settings.TELEGRAM_BOT_TOKEN", FAKE_TOKEN
    )
    from api.middleware.telegram_auth import verify_init_data

    init_data = _make_init_data()
    result = verify_init_data(init_data)
    assert result["user"]["id"] == 42


def test_invalid_hash(monkeypatch):
    monkeypatch.setattr(
        "api.middleware.telegram_auth.settings.TELEGRAM_BOT_TOKEN", FAKE_TOKEN
    )
    from api.middleware.telegram_auth import verify_init_data
    from fastapi import HTTPException

    init_data = _make_init_data() + "&hash=deadbeef"  # append duplicate hash
    with pytest.raises(Exception):
        verify_init_data(init_data)


def test_expired_init_data(monkeypatch):
    monkeypatch.setattr(
        "api.middleware.telegram_auth.settings.TELEGRAM_BOT_TOKEN", FAKE_TOKEN
    )
    # Patch _MAX_AGE_SECONDS to 0 so everything expires
    monkeypatch.setattr("api.middleware.telegram_auth._MAX_AGE_SECONDS", 0)

    from api.middleware.telegram_auth import verify_init_data
    from fastapi import HTTPException

    init_data = _make_init_data()
    with pytest.raises(HTTPException) as exc:
        verify_init_data(init_data)
    assert exc.value.status_code == 401
