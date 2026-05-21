"""Admin overview of Telegram Stars revenue.

Pulls getStarTransactions from Telegram, joins it with our purchases /
subscriptions tables, and exposes both:

- JSON at /api/admin/stars
- A self-contained HTML page at /api/admin/stars.html

Both routes share the same HTTP Basic credentials used by the SQLAdmin
panel (ADMIN_USERNAME / ADMIN_PASSWORD from settings).

The HTML view is intentionally inline-styled — no frontend build step,
no auth cookie negotiation, just a single URL you bookmark.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import Purchase, Subscription

log = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
_security = HTTPBasic()


def _require_admin(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    ok_user = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    ok_pass = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


async def _fetch_star_transactions(limit: int = 100) -> list[dict[str, Any]]:
    """Call Bot API getStarTransactions and return the transactions list."""
    url = (
        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
        f"/getStarTransactions?limit={limit}"
    )
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
    data = resp.json()
    if not data.get("ok"):
        log.error("admin_stars.tg_api_failed", response=data)
        return []
    return data["result"].get("transactions", []) or []


def _parse_product(payload: str | None) -> str | None:
    """Our payload shape: '{user_id}:{product_id}:{ts}'."""
    if not payload:
        return None
    parts = payload.split(":", 2)
    return parts[1] if len(parts) >= 2 else None


@router.get("/stars")
async def stars_overview(
    _: str = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """JSON: Telegram star transactions + reconciliation against our DB."""
    transactions = await _fetch_star_transactions(limit=100)

    charge_ids = [t["id"] for t in transactions]

    db_purchases: dict[str, Purchase] = {}
    db_subs: dict[str, Subscription] = {}
    if charge_ids:
        rows = await db.execute(
            select(Purchase).where(Purchase.tg_payment_charge_id.in_(charge_ids))
        )
        for p in rows.scalars().all():
            if p.tg_payment_charge_id:
                db_purchases[p.tg_payment_charge_id] = p
        rows = await db.execute(
            select(Subscription).where(
                Subscription.tg_payment_charge_id.in_(charge_ids)
            )
        )
        for s in rows.scalars().all():
            if s.tg_payment_charge_id:
                db_subs[s.tg_payment_charge_id] = s

    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    enriched: list[dict[str, Any]] = []
    total_amount = 0
    week_amount = 0
    month_amount = 0
    product_counts: dict[str, dict[str, int]] = {}

    for t in transactions:
        amount = int(t.get("amount", 0))
        total_amount += amount
        ts = datetime.fromtimestamp(t.get("date", 0), tz=UTC) if t.get("date") else None
        if ts and ts >= week_ago:
            week_amount += amount
        if ts and ts >= month_ago:
            month_amount += amount

        src = t.get("source") or {}
        payload = src.get("invoice_payload")
        product = _parse_product(payload)
        if product:
            bucket = product_counts.setdefault(product, {"count": 0, "stars": 0})
            bucket["count"] += 1
            bucket["stars"] += amount

        charge_id = t.get("id")
        matched = (charge_id in db_purchases) or (charge_id in db_subs)
        db_kind = (
            "purchase" if charge_id in db_purchases
            else "subscription" if charge_id in db_subs
            else None
        )

        user_id = (src.get("user") or {}).get("id")
        user_name = (src.get("user") or {}).get("first_name")
        user_username = (src.get("user") or {}).get("username")

        enriched.append({
            "charge_id": charge_id,
            "date": ts.isoformat() if ts else None,
            "amount": amount,
            "user_id": user_id,
            "user_name": user_name,
            "user_username": user_username,
            "product_id": product,
            "matched_in_db": matched,
            "db_kind": db_kind,
        })

    top_products = sorted(
        ({"product_id": pid, **stats} for pid, stats in product_counts.items()),
        key=lambda x: x["stars"],
        reverse=True,
    )[:10]

    unmatched_count = sum(1 for t in enriched if not t["matched_in_db"])

    return {
        "totals": {
            "transactions": len(transactions),
            "stars_total": total_amount,
            "stars_week": week_amount,
            "stars_month": month_amount,
            "unmatched": unmatched_count,
        },
        "top_products": top_products,
        "transactions": enriched,
    }


@router.get("/stars.html", response_class=HTMLResponse)
async def stars_overview_html(
    _: str = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """HTML page: same data as /admin/stars but server-side rendered."""
    data = await stars_overview(_=_, db=db)
    totals = data["totals"]
    top_products = data["top_products"]
    txs = data["transactions"]

    def _esc(s: Any) -> str:
        if s is None:
            return "—"
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    top_rows = "".join(
        f"<tr><td>{_esc(p['product_id'])}</td><td>{p['count']}</td>"
        f"<td>{p['stars']} ⭐</td></tr>"
        for p in top_products
    ) or "<tr><td colspan='3'><em>пусто</em></td></tr>"

    tx_rows = "".join(
        f"<tr class='{'ok' if t['matched_in_db'] else 'warn'}'>"
        f"<td>{_esc(t['date'])}</td>"
        f"<td>{t['amount']} ⭐</td>"
        f"<td>{_esc(t['user_name'])} "
        f"<span class='muted'>@{_esc(t['user_username'])}</span> "
        f"<span class='muted'>({_esc(t['user_id'])})</span></td>"
        f"<td>{_esc(t['product_id'])}</td>"
        f"<td>{'✅ ' + (t['db_kind'] or '') if t['matched_in_db'] else '⚠ нет в БД'}</td>"
        f"<td class='charge-id' title='{_esc(t['charge_id'])}'>"
        f"{_esc((t['charge_id'] or '')[:18])}…</td>"
        f"</tr>"
        for t in txs
    ) or "<tr><td colspan='6'><em>транзакций пока нет</em></td></tr>"

    html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Stars · Admin</title>
<style>
  :root {{
    --bg: #0a0906;
    --surface: #141210;
    --border: rgba(196,163,90,0.25);
    --text: #f0ecf8;
    --muted: #8a8492;
    --gold: #c4a35a;
    --green: #8bc89b;
    --red: #e88b8b;
  }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Inter", Roboto, sans-serif;
    margin: 0;
    padding: 24px;
  }}
  h1 {{
    font-family: "Playfair Display", Georgia, serif;
    color: var(--gold);
    font-weight: 500;
    margin: 0 0 24px;
  }}
  .totals {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }}
  .totals .card {{
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 12px;
    padding: 16px;
  }}
  .totals .label {{
    font-size: 11px;
    letter-spacing: 0.14em;
    color: var(--muted);
    text-transform: uppercase;
  }}
  .totals .value {{
    margin-top: 6px;
    font-size: 24px;
    font-weight: 500;
    color: var(--gold);
  }}
  h2 {{
    color: var(--gold);
    font-size: 14px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 24px 0 12px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    font-size: 13px;
  }}
  thead th {{
    text-align: left;
    padding: 12px 14px;
    color: var(--muted);
    font-weight: 500;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.08em;
    border-bottom: 0.5px solid var(--border);
  }}
  tbody td {{
    padding: 10px 14px;
    border-top: 0.5px solid rgba(255,255,255,0.05);
  }}
  tbody tr.ok td {{ }}
  tbody tr.warn td {{ background: rgba(232,139,139,0.06); }}
  .muted {{ color: var(--muted); font-size: 12px; }}
  .charge-id {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; }}
  a {{ color: var(--gold); }}
  .footer {{ margin-top: 24px; color: var(--muted); font-size: 12px; }}
</style>
</head>
<body>
<h1>✦ Stars · Admin</h1>

<div class="totals">
  <div class="card"><div class="label">Транзакций</div>
    <div class="value">{totals['transactions']}</div></div>
  <div class="card"><div class="label">Всего ⭐</div>
    <div class="value">{totals['stars_total']}</div></div>
  <div class="card"><div class="label">За неделю</div>
    <div class="value">{totals['stars_week']}</div></div>
  <div class="card"><div class="label">За 30 дней</div>
    <div class="value">{totals['stars_month']}</div></div>
</div>

{'<p style="color:var(--red);">⚠ ' + str(totals['unmatched']) + ' транзакций не нашлось в нашей БД — оплата прошла у Telegram, но webhook их не обработал.</p>' if totals['unmatched'] else ''}

<h2>Топ продуктов</h2>
<table>
  <thead><tr><th>Продукт</th><th>Покупок</th><th>Сумма</th></tr></thead>
  <tbody>{top_rows}</tbody>
</table>

<h2>Все транзакции (последние 100)</h2>
<table>
  <thead><tr>
    <th>Дата</th><th>⭐</th><th>Пользователь</th><th>Продукт</th>
    <th>Статус в БД</th><th>Charge ID</th>
  </tr></thead>
  <tbody>{tx_rows}</tbody>
</table>

<p class="footer">JSON: <a href="/api/admin/stars">/api/admin/stars</a> ·
Бот: @{_esc(settings.TELEGRAM_BOT_USERNAME or 'astrologiyatut_bot')}</p>
</body>
</html>"""
    return HTMLResponse(html)
