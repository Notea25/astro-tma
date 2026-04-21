"""Daily news generation job — detects events in next 48h and writes them to DB."""

from datetime import datetime, timezone

from sqlalchemy import select

from core.logging import get_logger
from db.database import AsyncSessionLocal
from db.models import AstroNews
from services.news.events import detect_events
from services.news.generator import generate_body

log = get_logger(__name__)


async def run_once(lookahead_days: int = 2) -> int:
    """Detect events, generate bodies, insert into astro_news. Returns number of new rows."""
    start = datetime.now(timezone.utc)
    events = detect_events(start, days=lookahead_days)

    created = 0
    async with AsyncSessionLocal() as db:
        for event in events:
            # Dedup by (date, title_ru)
            result = await db.execute(
                select(AstroNews).where(
                    AstroNews.date == event["date"],
                    AstroNews.title_ru == event["title_ru"],
                )
            )
            if result.scalar_one_or_none():
                continue

            body = await generate_body(event)
            row = AstroNews(
                date=event["date"],
                title_ru=event["title_ru"],
                body_md=body,
                category=event["category"],
                priority=event["priority"],
                source_data=event.get("source_data"),
                published=True,
            )
            db.add(row)
            created += 1

        await db.commit()

    log.info("news.scheduler_done", created=created, total_events=len(events))
    return created


async def generate_daily_news() -> None:
    """APScheduler job entry point."""
    try:
        await run_once(lookahead_days=2)
    except Exception as e:
        log.error("news.scheduler_failed", error=str(e))
