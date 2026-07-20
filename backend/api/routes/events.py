"""Analytics ingest — product funnel events from the Mini App."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from db.database import get_db
from services.analytics.events import ALLOWED_EVENTS, record_event
from services.users import repository as user_repo

router = APIRouter(prefix="/events", tags=["events"])


class EventIn(BaseModel):
    event: str = Field(max_length=64)
    product_id: str | None = Field(default=None, max_length=64)
    props: dict[str, Any] | None = None


class EventsBatch(BaseModel):
    events: list[EventIn] = Field(min_length=1, max_length=50)


@router.post("")
async def ingest_events(
    body: EventsBatch,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Fire-and-forget batch from the Mini App. Unknown events are skipped."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        # Soft-create from initData so early app_open isn't lost.
        user, _ = await user_repo.get_or_create(
            db,
            tg_user_id=tg_user["id"],
            first_name=tg_user.get("first_name") or "User",
            username=tg_user.get("username"),
            last_name=tg_user.get("last_name"),
            language_code=tg_user.get("language_code") or "ru",
            is_premium=bool(tg_user.get("is_premium")),
        )

    accepted = 0
    skipped = 0
    for item in body.events:
        if item.event not in ALLOWED_EVENTS:
            skipped += 1
            continue
        ok = await record_event(
            db,
            user.id,
            item.event,
            product_id=item.product_id,
            props=item.props,
        )
        if ok:
            accepted += 1
        else:
            skipped += 1

    await db.commit()
    return {"ok": True, "accepted": accepted, "skipped": skipped}
