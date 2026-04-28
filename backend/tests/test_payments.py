"""Tests for payment payload parsing."""
import time


def test_payload_format():
    user_id = 12345
    product_id = "natal_full"
    payload = f"{user_id}:{product_id}:{int(time.time())}"
    parts = payload.split(":")
    assert len(parts) == 3
    assert parts[0] == str(user_id)
    assert parts[1] == product_id


def test_products_catalogue():
    from services.payments.stars import PRODUCTS
    assert "subscription_month" in PRODUCTS
    assert "natal_full" in PRODUCTS
    for pid, p in PRODUCTS.items():
        assert "stars" in p
        assert p["stars"] > 0
        assert "name" in p
        assert "type" in p
