"""Eligibility rules for payment providers."""

from __future__ import annotations

import re
from typing import Protocol

from services.users.birth_location import normalize_country_code

UKRAINE_COUNTRY_CODE = "UA"

_UKRAINE_COUNTRY_NAMES = {"ukraine", "украина", "україна"}
_UKRAINE_TIMEZONES = {
    "Europe/Kiev",
    "Europe/Kyiv",
    "Europe/Uzhgorod",
    "Europe/Zaporozhye",
}
_LOCATION_PARTS_RE = re.compile(r"[,;/|]")


class BirthLocation(Protocol):
    birth_country_code: str | None
    birth_city: str | None
    birth_tz: str | None


def is_ukraine_birthplace(user: BirthLocation) -> bool:
    """Use canonical country data first, then narrow legacy fallbacks."""
    country_code = normalize_country_code(getattr(user, "birth_country_code", None))
    if country_code is not None:
        return country_code == UKRAINE_COUNTRY_CODE

    city = getattr(user, "birth_city", None) or ""
    location_parts = {
        part.strip().casefold()
        for part in _LOCATION_PARTS_RE.split(city)
        if part.strip()
    }
    if location_parts & _UKRAINE_COUNTRY_NAMES:
        return True

    return (getattr(user, "birth_tz", None) or "") in _UKRAINE_TIMEZONES


def is_yukassa_allowed(user: BirthLocation) -> bool:
    """Ukraine birthplace users may purchase only through Telegram Stars."""
    return not is_ukraine_birthplace(user)
