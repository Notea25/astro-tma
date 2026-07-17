"""Tests for payment payload parsing and per-user provider eligibility."""

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


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


@pytest.mark.parametrize(
    ("country_code", "birth_city", "birth_tz", "expected"),
    [
        ("UA", "Київ, Україна", "Europe/Kyiv", True),
        (" ua ", "Kyiv", "Europe/Kyiv", True),
        ("RU", "Київ, Україна", "Europe/Kyiv", False),
        (None, "Киев, Украина", None, True),
        (None, "Kyiv, Ukraine", None, True),
        (None, "Київ, Україна", None, True),
        (None, "Украинка, Киевская область", None, False),
        (None, "Киев", "Europe/Kiev", True),
        (None, "Минск, Беларусь", "Europe/Minsk", False),
        (None, None, None, False),
    ],
)
def test_ukraine_birthplace_policy(
    country_code,
    birth_city,
    birth_tz,
    expected,
):
    from services.payments.policy import is_ukraine_birthplace

    user = SimpleNamespace(
        birth_country_code=country_code,
        birth_city=birth_city,
        birth_tz=birth_tz,
    )
    assert is_ukraine_birthplace(user) is expected


def test_nominatim_country_code_is_normalized():
    from services.users.birth_location import country_code_from_nominatim

    assert country_code_from_nominatim({"address": {"country_code": "ua"}}) == "UA"
    assert country_code_from_nominatim({"address": {"country_code": "unknown"}}) is None
    assert country_code_from_nominatim({}) is None


@pytest.mark.asyncio
async def test_products_hide_yukassa_for_ukraine_birthplace(monkeypatch):
    from api.routes.payments import list_products

    user = SimpleNamespace(
        id=42,
        birth_country_code="UA",
        birth_city="Київ, Україна",
        birth_tz="Europe/Kyiv",
    )
    monkeypatch.setattr("api.routes.payments.yk.is_configured", lambda: True)
    monkeypatch.setattr(
        "api.routes.payments.user_repo.get_for_payment_policy",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(
        "api.routes.payments.get_product_price",
        AsyncMock(side_effect=lambda _pid, default: default),
    )
    monkeypatch.setattr(
        "api.routes.payments.get_product_price_rub",
        AsyncMock(side_effect=lambda _pid, default: default),
    )

    response = await list_products(tg_user={"id": 42}, db=AsyncMock())

    assert response.card_payments_available is False
    assert response.products
    assert all(product.stars > 0 for product in response.products)


@pytest.mark.asyncio
@pytest.mark.parametrize("payment_method", ["bank_card", "sbp"])
async def test_yukassa_create_is_blocked_before_price_or_provider_call(
    monkeypatch,
    payment_method,
):
    from api.routes.payments import YukassaCreateRequest, create_yukassa_payment

    user = SimpleNamespace(
        id=42,
        birth_country_code="UA",
        birth_city="Київ, Україна",
        birth_tz="Europe/Kyiv",
    )
    get_price = AsyncMock(return_value=490)
    create_payment = AsyncMock()
    # Eligibility must be enforced independently of provider configuration.
    monkeypatch.setattr("api.routes.payments.yk.is_configured", lambda: False)
    monkeypatch.setattr("api.routes.payments.yk.create_payment", create_payment)
    monkeypatch.setattr("api.routes.payments.get_product_price_rub", get_price)
    monkeypatch.setattr(
        "api.routes.payments.user_repo.get_for_payment_policy",
        AsyncMock(return_value=user),
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_yukassa_payment(
            YukassaCreateRequest(
                product_id="natal_full",
                email="reader@example.com",
                payment_method=payment_method,
            ),
            tg_user={"id": 42},
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == (
        "Оплата картой и через СБП недоступна. Используйте Telegram Stars."
    )
    get_price.assert_not_awaited()
    create_payment.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payment_method", ["bank_card", "sbp"])
async def test_yukassa_create_remains_available_for_other_countries(
    monkeypatch,
    payment_method,
):
    from api.routes.payments import YukassaCreateRequest, create_yukassa_payment

    user = SimpleNamespace(
        id=42,
        birth_country_code="BY",
        birth_city="Минск, Беларусь",
        birth_tz="Europe/Minsk",
    )
    create_payment = AsyncMock(
        return_value={
            "id": "payment-id",
            "confirmation": {"confirmation_url": "https://pay.example.test"},
        }
    )
    monkeypatch.setattr("api.routes.payments.yk.is_configured", lambda: True)
    monkeypatch.setattr("api.routes.payments.yk.create_payment", create_payment)
    monkeypatch.setattr(
        "api.routes.payments.get_product_price_rub",
        AsyncMock(return_value=490),
    )
    monkeypatch.setattr(
        "api.routes.payments.user_repo.get_for_payment_policy",
        AsyncMock(return_value=user),
    )

    response = await create_yukassa_payment(
        YukassaCreateRequest(
            product_id="natal_full",
            email="reader@example.com",
            payment_method=payment_method,
        ),
        tg_user={"id": 42},
        db=AsyncMock(),
    )

    assert response.payment_id == "payment-id"
    assert response.rub_amount == 490
    assert create_payment.await_args.kwargs["payment_method"] == payment_method


@pytest.mark.asyncio
async def test_stars_invoice_is_not_affected_by_birth_country(monkeypatch):
    from api.routes.payments import CreateInvoiceRequest, create_invoice

    create_link = AsyncMock(return_value="https://t.me/invoice")
    monkeypatch.setattr("api.routes.payments.create_invoice_link", create_link)

    response = await create_invoice(
        CreateInvoiceRequest(product_id="natal_full"),
        tg_user={"id": 42},
    )

    assert response.invoice_url == "https://t.me/invoice"
    assert response.stars_amount > 0
    create_link.assert_awaited_once_with(42, "natal_full")


@pytest.mark.asyncio
async def test_update_birth_data_persists_country_code():
    from services.users.repository import update_birth_data

    user = SimpleNamespace(id=42)
    db = AsyncMock()

    await update_birth_data(
        db,
        user,
        birth_date=SimpleNamespace(),
        birth_time_known=True,
        birth_city="Київ, Україна",
        lat=50.4501,
        lng=30.5234,
        tz_str="Europe/Kyiv",
        country_code="UA",
        sun_sign="Aries",
    )

    assert user.birth_country_code == "UA"
    db.flush.assert_awaited_once()
