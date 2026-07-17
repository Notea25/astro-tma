"""Server-side country resolution for a user's selected birth location."""

from __future__ import annotations

from typing import Any

import httpx

from core.logging import get_logger

log = get_logger(__name__)

_NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
_NOMINATIM_HEADERS = {"User-Agent": "astro-tma/1.0"}


def normalize_country_code(value: Any) -> str | None:
    """Return an uppercase ISO-3166 alpha-2 code or ``None``."""
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    if len(code) != 2 or not code.isalpha():
        return None
    return code


def country_code_from_nominatim(payload: dict[str, Any]) -> str | None:
    address = payload.get("address") or {}
    if not isinstance(address, dict):
        return None
    return normalize_country_code(address.get("country_code"))


async def reverse_country_code(
    lat: float,
    lng: float,
    *,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """Resolve coordinates through Nominatim without trusting client country data."""
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=8.0)
    try:
        response = await http.get(
            _NOMINATIM_REVERSE_URL,
            params={
                "lat": lat,
                "lon": lng,
                "format": "jsonv2",
                "addressdetails": 1,
                "accept-language": "en",
            },
            headers=_NOMINATIM_HEADERS,
        )
        response.raise_for_status()
        payload = response.json()
        return country_code_from_nominatim(payload if isinstance(payload, dict) else {})
    except Exception as exc:  # noqa: BLE001 - an unavailable geocoder means unknown country
        log.warning("geocode.country_failed", error_type=type(exc).__name__)
        return None
    finally:
        if owns_client:
            await http.aclose()
