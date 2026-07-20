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
from typing import Any, cast

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import Purchase, Subscription
from services.payments.pricing import (
    clear_product_price,
    clear_product_price_rub,
    get_all_overrides,
    get_all_rub_overrides,
    set_product_price,
    set_product_price_rub,
)
from services.payments.stars import PRODUCTS, grant_product_access
from services.analytics.events import FUNNELS, activity_summary, funnel_counts
from services.analytics.acquisition import acquisition_breakdown

log = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
_security = HTTPBasic()


def _esc_html(s: Any) -> str:
    if s is None:
        return "—"
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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


_NAV_LINKS = (
    ("База",       "/admin/",                      "db"),
    ("Аналитика",  "/api/admin/analytics.html",    "analytics"),
    ("Stars",      "/api/admin/stars.html",        "stars"),
    ("Цены",       "/api/admin/products.html",     "prices"),
)


def _admin_nav_html(active: str) -> str:
    """Top nav bar rendered above every custom admin page so the operator
    can jump between SQLAdmin (БД), Stars overview and Prices editor
    without retyping the URL."""
    items = "".join(
        f'<a href="{href}" class="admin-nav__link{" admin-nav__link--active" if key == active else ""}">{label}</a>'
        for label, href, key in _NAV_LINKS
    )
    return (
        '<nav class="admin-nav">'
        '<span class="admin-nav__brand">✦ Astro Admin</span>'
        f'<span class="admin-nav__links">{items}</span>'
        "</nav>"
    )


_NAV_CSS = """
  .admin-nav {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 12px 18px;
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 12px;
    margin-bottom: 18px;
  }
  .admin-nav__brand {
    font-family: "Playfair Display", Georgia, serif;
    color: var(--gold);
    font-weight: 500;
    letter-spacing: 0.04em;
  }
  .admin-nav__links { display: inline-flex; gap: 6px; margin-left: auto; }
  .admin-nav__link {
    color: var(--text);
    text-decoration: none;
    font-size: 13px;
    padding: 6px 14px;
    border-radius: 8px;
    border: 0.5px solid transparent;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
  }
  .admin-nav__link:hover { background: rgba(255,255,255,0.04); }
  .admin-nav__link--active {
    background: rgba(212,178,84,0.12);
    color: var(--gold);
    border-color: var(--border);
  }
"""


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
        purchase_rows = await db.execute(
            select(Purchase).where(Purchase.tg_payment_charge_id.in_(charge_ids))
        )
        for p in purchase_rows.scalars().all():
            if p.tg_payment_charge_id:
                db_purchases[p.tg_payment_charge_id] = p
        subscription_rows = await db.execute(
            select(Subscription).where(
                Subscription.tg_payment_charge_id.in_(charge_ids)
            )
        )
        for s in subscription_rows.scalars().all():
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
        key=lambda x: cast(int, x["stars"]),
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

    def _action_cell(t: dict[str, Any]) -> str:
        if t["matched_in_db"]:
            return "<td></td>"
        cid = _esc(t["charge_id"])
        return (
            f"<td><button class='recon-btn' data-cid='{cid}'>Восстановить</button></td>"
        )

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
        f"{_action_cell(t)}"
        f"</tr>"
        for t in txs
    ) or "<tr><td colspan='7'><em>транзакций пока нет</em></td></tr>"

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
    margin: 0 0 18px;
  }}
  {_NAV_CSS}
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
  .reconcile-bar {{
    display: flex; align-items: center; gap: 16px;
    padding: 12px 16px; margin: 0 0 18px;
    background: rgba(232, 139, 139, 0.08);
    border: 0.5px solid rgba(232, 139, 139, 0.32);
    border-radius: 10px;
    color: var(--red);
    font-size: 13px;
  }}
  .reconcile-bar span {{ flex: 1; }}
  .recon-btn, .recon-all-btn {{
    background: var(--gold);
    color: #0a0906;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.15s;
  }}
  .recon-btn:hover, .recon-all-btn:hover {{ opacity: 0.85; }}
  .recon-btn:disabled, .recon-all-btn:disabled {{
    opacity: 0.5; cursor: progress;
  }}
  .recon-btn.done {{ background: var(--green); }}
  .recon-btn.fail {{ background: var(--red); color: var(--text); }}
</style>
</head>
<body>
{_admin_nav_html("stars")}
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

{('<div class="reconcile-bar">'
  f'<span>⚠ {totals["unmatched"]} транзакций не нашлось в нашей БД — оплата прошла у Telegram, но webhook их не обработал.</span>'
  '<button class="recon-all-btn" onclick="reconcileAll()">Восстановить все</button>'
  '</div>') if totals['unmatched'] else ''}

<h2>Топ продуктов</h2>
<table>
  <thead><tr><th>Продукт</th><th>Покупок</th><th>Сумма</th></tr></thead>
  <tbody>{top_rows}</tbody>
</table>

<h2>Все транзакции (последние 100)</h2>
<table>
  <thead><tr>
    <th>Дата</th><th>⭐</th><th>Пользователь</th><th>Продукт</th>
    <th>Статус в БД</th><th>Charge ID</th><th></th>
  </tr></thead>
  <tbody>{tx_rows}</tbody>
</table>

<p class="footer">JSON: <a href="/api/admin/stars">/api/admin/stars</a> ·
Бот: @{_esc(settings.TELEGRAM_BOT_USERNAME or 'astrologiyatut_bot')}</p>

<script>
async function reconcileOne(btn) {{
  const cid = btn.dataset.cid;
  if (!cid) return;
  btn.disabled = true;
  btn.textContent = '…';
  try {{
    const r = await fetch('/api/admin/stars/reconcile/' + encodeURIComponent(cid),
                          {{method: 'POST'}});
    const data = await r.json();
    if (data.status === 'granted' || data.status === 'already') {{
      btn.classList.add('done');
      btn.textContent = data.status === 'granted' ? '✓ Выдан' : '✓ Уже есть';
    }} else {{
      btn.classList.add('fail');
      btn.textContent = '✗ ' + (data.status || 'fail');
    }}
  }} catch (e) {{
    btn.classList.add('fail');
    btn.textContent = '✗ ошибка';
  }}
}}
document.querySelectorAll('.recon-btn').forEach(b =>
  b.addEventListener('click', () => reconcileOne(b))
);
async function reconcileAll() {{
  const btn = document.querySelector('.recon-all-btn');
  if (!btn || !confirm('Восстановить все непривязанные транзакции?')) return;
  btn.disabled = true;
  btn.textContent = 'Восстанавливаем…';
  try {{
    const r = await fetch('/api/admin/stars/reconcile-all', {{method: 'POST'}});
    const data = await r.json();
    const s = data.summary || {{}};
    alert('Готово.\\n'
        + 'Выдано: ' + (s.granted || 0) + '\\n'
        + 'Уже было: ' + (s.already || 0) + '\\n'
        + 'Битый payload: ' + (s.bad_payload || 0) + '\\n'
        + 'Без user_id: ' + (s.unknown_user || 0) + '\\n'
        + 'Незнакомый продукт: ' + (s.unknown_product || 0));
    location.reload();
  }} catch (e) {{
    alert('Ошибка: ' + e.message);
    btn.disabled = false;
    btn.textContent = 'Восстановить все';
  }}
}}
</script>
</body>
</html>"""
    return HTMLResponse(html)


# ── Reconciliation: replay grant_product_access for unmatched payments ──────


async def _reconcile_charge(
    db: AsyncSession, tx: dict[str, Any],
) -> dict[str, Any]:
    """Apply the same access-grant the webhook would have performed for
    one Telegram star transaction. Returns a {status, …} dict for the
    caller to assemble a summary.

    Statuses:
      * `granted`      — Purchase / Subscription row created.
      * `already`      — A row with this charge_id already exists.
      * `bad_payload`  — Telegram's payload couldn't be parsed.
      * `unknown_user` — Telegram didn't surface a user.id (rare).
      * `unknown_product` — payload product_id is not in our catalogue.
    """
    charge_id = tx.get("id")
    src = tx.get("source") or {}
    payload = src.get("invoice_payload") or ""
    user = src.get("user") or {}
    user_id = user.get("id")
    user_name = user.get("first_name")
    amount = int(tx.get("amount", 0))

    # Already matched? — skip (idempotent).
    if charge_id:
        existing = await db.execute(
            select(Purchase).where(Purchase.tg_payment_charge_id == charge_id)
        )
        if existing.scalar_one_or_none():
            return {"charge_id": charge_id, "status": "already", "kind": "purchase"}
        existing = await db.execute(
            select(Subscription).where(
                Subscription.tg_payment_charge_id == charge_id
            )
        )
        if existing.scalar_one_or_none():
            return {"charge_id": charge_id, "status": "already", "kind": "subscription"}

    if not user_id:
        return {"charge_id": charge_id, "status": "unknown_user", "payload": payload}

    parts = payload.split(":", 2)
    if len(parts) < 2:
        return {"charge_id": charge_id, "status": "bad_payload", "payload": payload}
    product_id = parts[1]
    if product_id not in PRODUCTS:
        return {
            "charge_id": charge_id, "status": "unknown_product",
            "product_id": product_id,
        }

    try:
        await grant_product_access(db, user_id, product_id, charge_id or "", payload)
    except IntegrityError:
        await db.rollback()
        return {"charge_id": charge_id, "status": "already"}
    return {
        "charge_id": charge_id, "status": "granted",
        "user_id": user_id, "user_name": user_name,
        "product_id": product_id, "amount": amount,
    }


@router.post("/stars/reconcile/{charge_id}")
async def reconcile_one(
    charge_id: str,
    _: str = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Replay one specific unmatched payment by its Telegram charge_id."""
    transactions = await _fetch_star_transactions(limit=100)
    tx = next((t for t in transactions if t.get("id") == charge_id), None)
    if tx is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Transaction not found in Telegram's last 100. "
            "Pull a larger window if it's older.",
        )
    result = await _reconcile_charge(db, tx)
    log.info("admin_stars.reconcile_one", **result)
    return result


@router.post("/stars/reconcile-all")
async def reconcile_all(
    _: str = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Walk every Telegram transaction in the recent window and grant
    access for any that aren't yet in our DB. Idempotent — already-matched
    rows are skipped via the charge_id UNIQUE constraint."""
    transactions = await _fetch_star_transactions(limit=100)
    summary: dict[str, int] = {
        "granted": 0, "already": 0, "bad_payload": 0,
        "unknown_user": 0, "unknown_product": 0,
    }
    details: list[dict[str, Any]] = []
    for tx in transactions:
        result = await _reconcile_charge(db, tx)
        summary[result["status"]] = summary.get(result["status"], 0) + 1
        if result["status"] == "granted":
            details.append(result)
    log.info("admin_stars.reconcile_all", **summary)
    return {"summary": summary, "granted": details}


# ── Pricing management ───────────────────────────────────────────────────────


@router.get("/products")
async def admin_list_products(_: str = Depends(_require_admin)) -> dict[str, Any]:
    """Per-product effective price (Stars + rubles). Each price has its
    own override → catalogue default fall-through."""
    star_overrides = await get_all_overrides(list(PRODUCTS.keys()))
    rub_overrides = await get_all_rub_overrides(list(PRODUCTS.keys()))
    items: list[dict[str, Any]] = []
    for pid, product in PRODUCTS.items():
        s_override = star_overrides.get(pid)
        r_override = rub_overrides.get(pid)
        default_rub = int(product.get("price_rub") or 0)
        items.append(
            {
                "id": pid,
                "name": product["name"],
                "type": product["type"],
                "default_stars": product["stars"],
                "current_stars": (
                    s_override if s_override is not None else product["stars"]
                ),
                "is_overridden": s_override is not None,
                "default_rub": default_rub,
                "current_rub": r_override if r_override is not None else default_rub,
                "is_overridden_rub": r_override is not None,
            }
        )
    return {"products": items}


@router.post("/products/{product_id}/price")
async def admin_set_price(
    product_id: str,
    payload: dict[str, Any],
    _: str = Depends(_require_admin),
) -> dict[str, Any]:
    if product_id not in PRODUCTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown product")
    try:
        stars = int(payload.get("stars", 0))
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "stars must be an integer")
    if stars < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "stars must be ≥ 1")
    await set_product_price(product_id, stars)
    log.info("admin.price_set", product=product_id, stars=stars)
    return {"product_id": product_id, "stars": stars, "ok": True}


@router.delete("/products/{product_id}/price")
async def admin_clear_price(
    product_id: str,
    _: str = Depends(_require_admin),
) -> dict[str, Any]:
    if product_id not in PRODUCTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown product")
    await clear_product_price(product_id)
    log.info("admin.price_cleared", product=product_id)
    return {"product_id": product_id, "ok": True}


# ── Ruble price (UI-only, no YuKassa flow yet) ──────────────────────────────


@router.post("/products/{product_id}/price-rub")
async def admin_set_price_rub(
    product_id: str,
    payload: dict[str, Any],
    _: str = Depends(_require_admin),
) -> dict[str, Any]:
    if product_id not in PRODUCTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown product")
    try:
        rub = int(payload.get("rub", 0))
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "rub must be an integer")
    if rub < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "rub must be ≥ 1")
    await set_product_price_rub(product_id, rub)
    log.info("admin.price_rub_set", product=product_id, rub=rub)
    return {"product_id": product_id, "rub": rub, "ok": True}


@router.delete("/products/{product_id}/price-rub")
async def admin_clear_price_rub(
    product_id: str,
    _: str = Depends(_require_admin),
) -> dict[str, Any]:
    if product_id not in PRODUCTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown product")
    await clear_product_price_rub(product_id)
    log.info("admin.price_rub_cleared", product=product_id)
    return {"product_id": product_id, "ok": True}


@router.get("/products.html", response_class=HTMLResponse)
async def admin_products_html(_: str = Depends(_require_admin)) -> Response:
    """Inline HTML page to edit prices per product. Two parallel columns:
    Stars (live, wired to invoices) and rubles (UI-only for screenshots
    until YuKassa is connected)."""
    star_overrides = await get_all_overrides(list(PRODUCTS.keys()))
    rub_overrides = await get_all_rub_overrides(list(PRODUCTS.keys()))

    def _badge(is_override: bool) -> str:
        if is_override:
            return "<span class='badge override'>override</span>"
        return "<span class='badge default'>default</span>"

    rows = []
    for pid, product in PRODUCTS.items():
        s_override = star_overrides.get(pid)
        r_override = rub_overrides.get(pid)
        current_stars = s_override if s_override is not None else product["stars"]
        default_rub = int(product.get("price_rub") or 0)
        current_rub = r_override if r_override is not None else default_rub
        rows.append(
            f"<tr data-product-id='{pid}'>"
            f"<td><strong>{product['name']}</strong>"
            f"<div class='muted'>{pid}</div></td>"
            f"<td>{product['type']}</td>"
            # ── Stars column ──
            f"<td class='price-cell'>"
            f"<div class='catalog'>{product['stars']} ⭐</div>"
            f"<input type='number' min='1' value='{current_stars}' class='price-input stars-input' />"
            f"{_badge(s_override is not None)}"
            f"<div class='actions'>"
            f"<button class='save stars-save'>Сохранить ⭐</button> "
            f"<button class='reset stars-reset'>Сбросить</button>"
            f"</div>"
            f"</td>"
            # ── Rubles column ──
            f"<td class='price-cell'>"
            f"<div class='catalog'>{default_rub} ₽</div>"
            f"<input type='number' min='1' value='{current_rub}' class='price-input rub-input' />"
            f"{_badge(r_override is not None)}"
            f"<div class='actions'>"
            f"<button class='save rub-save'>Сохранить ₽</button> "
            f"<button class='reset rub-reset'>Сбросить</button>"
            f"</div>"
            f"</td>"
            f"</tr>"
        )
    rows_html = "".join(rows) or "<tr><td colspan='4'><em>пусто</em></td></tr>"

    html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Products · Admin</title>
<style>
  :root {{
    --bg: #0a0906; --surface: #141210; --border: rgba(196,163,90,0.25);
    --text: #f0ecf8; --muted: #8a8492; --gold: #c4a35a;
    --green: #8bc89b; --red: #e88b8b;
  }}
  body {{
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Inter", Roboto, sans-serif;
    margin: 0; padding: 24px;
  }}
  h1 {{
    font-family: "Playfair Display", Georgia, serif;
    color: var(--gold); font-weight: 500; margin: 0 0 12px;
  }}
  .hint {{ color: var(--muted); font-size: 13px; margin: 0 0 20px; }}
  table {{
    width: 100%; border-collapse: collapse;
    background: var(--surface); border: 0.5px solid var(--border);
    border-radius: 12px; overflow: hidden; font-size: 13px;
  }}
  thead th {{
    text-align: left; padding: 12px 14px; color: var(--muted);
    font-weight: 500; text-transform: uppercase; font-size: 11px;
    letter-spacing: 0.08em; border-bottom: 0.5px solid var(--border);
  }}
  tbody td {{ padding: 12px 14px; border-top: 0.5px solid rgba(255,255,255,0.05); vertical-align: top; }}
  .muted {{ color: var(--muted); font-size: 11px; }}
  .price-cell {{ min-width: 200px; }}
  .price-cell .catalog {{ color: var(--muted); font-size: 11px; margin-bottom: 4px; }}
  .price-cell .actions {{ margin-top: 8px; display: flex; gap: 6px; }}
  .price-input {{
    width: 90px; padding: 6px 8px;
    background: rgba(255,255,255,0.04); border: 0.5px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: 14px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }}
  .badge {{
    margin-left: 8px; padding: 2px 8px; border-radius: 999px;
    font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
  }}
  .badge.override {{ background: rgba(212,178,84,0.18); color: var(--gold); }}
  .badge.default {{ background: rgba(255,255,255,0.06); color: var(--muted); }}
  button {{
    background: var(--gold); color: #0a0906; border: none;
    padding: 6px 14px; border-radius: 8px; cursor: pointer;
    font-size: 12px; font-weight: 500;
  }}
  button.reset {{ background: transparent; color: var(--muted); border: 0.5px solid var(--border); }}
  button:disabled {{ opacity: 0.5; cursor: wait; }}
  .toast {{
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    background: var(--surface); border: 0.5px solid var(--gold-border);
    color: var(--text); padding: 10px 18px; border-radius: 10px;
    font-size: 13px; opacity: 0; transition: opacity 0.2s;
  }}
  .toast.show {{ opacity: 1; }}
  a {{ color: var(--gold); }}
  .footer {{ margin-top: 24px; color: var(--muted); font-size: 12px; }}
  {_NAV_CSS}
</style>
</head>
<body>
{_admin_nav_html("prices")}
<h1>✦ Цены продуктов</h1>
<p class="hint">Изменения применяются мгновенно ко всем новым инвойсам. Чтобы вернуться к каталожной цене — нажмите «Сбросить».</p>

<table>
  <thead><tr>
    <th>Продукт</th><th>Тип</th>
    <th>⭐ Звёзды</th><th>₽ Рубли</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>

<div class="toast" id="toast"></div>

<script>
function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2200);
}}

async function postPrice(pid, currency, value) {{
  const path = currency === 'rub' ? 'price-rub' : 'price';
  const body = currency === 'rub' ? {{ rub: value }} : {{ stars: value }};
  const resp = await fetch(`/api/admin/products/${{pid}}/${{path}}`, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(body),
    credentials: 'include',
  }});
  if (!resp.ok) throw new Error(`HTTP ${{resp.status}}`);
}}

async function deletePrice(pid, currency) {{
  const path = currency === 'rub' ? 'price-rub' : 'price';
  const resp = await fetch(`/api/admin/products/${{pid}}/${{path}}`, {{
    method: 'DELETE',
    credentials: 'include',
  }});
  if (!resp.ok) throw new Error(`HTTP ${{resp.status}}`);
}}

document.querySelectorAll('tr[data-product-id]').forEach(row => {{
  const pid = row.dataset.productId;

  function bind(saveSel, resetSel, inputSel, currency, label) {{
    const saveBtn = row.querySelector(saveSel);
    const resetBtn = row.querySelector(resetSel);
    const input = row.querySelector(inputSel);
    saveBtn.addEventListener('click', async () => {{
      const value = parseInt(input.value, 10);
      if (!value || value < 1) {{ showToast('Цена должна быть ≥ 1'); return; }}
      saveBtn.disabled = true;
      try {{
        await postPrice(pid, currency, value);
        showToast(`${{pid}}: ${{value}} ${{label}} сохранено`);
        setTimeout(() => location.reload(), 600);
      }} catch (e) {{
        showToast(`Ошибка: ${{e.message}}`);
        saveBtn.disabled = false;
      }}
    }});
    resetBtn.addEventListener('click', async () => {{
      resetBtn.disabled = true;
      try {{
        await deletePrice(pid, currency);
        showToast(`${{pid}}: ${{label}} сброшено к каталогу`);
        setTimeout(() => location.reload(), 600);
      }} catch (e) {{
        showToast(`Ошибка: ${{e.message}}`);
        resetBtn.disabled = false;
      }}
    }});
  }}

  bind('.stars-save', '.stars-reset', '.stars-input', 'stars', '⭐');
  bind('.rub-save', '.rub-reset', '.rub-input', 'rub', '₽');
}});
</script>

<p class="footer">
  JSON: <a href="/api/admin/products">/api/admin/products</a>
</p>
</body>
</html>"""
    return HTMLResponse(html)


# ── Product analytics ────────────────────────────────────────────────────────


@router.get("/analytics")
async def admin_analytics_json(
    days: int = 7,
    _: str = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    days = max(1, min(days, 90))
    summary = await activity_summary(db)
    funnels = {
        name: await funnel_counts(db, steps, days=days)
        for name, steps in FUNNELS.items()
    }
    # Product-scoped pay funnel for the main paid SKUs
    products = [
        "natal_full",
        "destiny_matrix_full",
        "synastry",
        "subscription_month",
        "subscription_year",
    ]
    by_product = {}
    for pid in products:
        by_product[pid] = await funnel_counts(
            db, FUNNELS["pay_generic"], days=days, product_id=pid,
        )
    return {
        "days": days,
        "summary": summary,
        "funnels": funnels,
        "pay_by_product": by_product,
        "acquisition": await acquisition_breakdown(db, days=days),
    }


@router.get("/analytics.html", response_class=HTMLResponse)
async def admin_analytics_html(
    days: int = 7,
    _: str = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    days = max(1, min(days, 90))
    summary = await activity_summary(db)
    funnels = {
        name: await funnel_counts(db, steps, days=days)
        for name, steps in FUNNELS.items()
    }
    products = [
        "natal_full",
        "destiny_matrix_full",
        "synastry",
        "subscription_month",
        "subscription_year",
    ]
    by_product = {
        pid: await funnel_counts(db, FUNNELS["pay_generic"], days=days, product_id=pid)
        for pid in products
    }
    acquisition = await acquisition_breakdown(db, days=days)

    def _funnel_table(title: str, steps: list[dict[str, Any]]) -> str:
        rows = "".join(
            "<tr>"
            f"<td>{_esc_html(s['event'])}</td>"
            f"<td class='num'>{s['users']}</td>"
            f"<td class='num'>{'—' if s['drop_pct'] is None else str(s['drop_pct']) + '%'}</td>"
            "</tr>"
            for s in steps
        )
        return (
            f"<section class='card'><h2>{_esc_html(title)}</h2>"
            "<table><thead><tr><th>Шаг</th><th>Юзеры</th><th>Drop</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></section>"
        )

    funnel_html = "".join(
        _funnel_table(name, steps) for name, steps in funnels.items()
    )
    product_html = "".join(
        _funnel_table(pid, steps) for pid, steps in by_product.items()
    )
    screens = "".join(
        f"<tr><td>{_esc_html(s['screen'])}</td><td class='num'>{s['users']}</td></tr>"
        for s in summary.get("top_screens_7d") or []
    ) or "<tr><td colspan='2' class='muted'>Пока нет screen_view</td></tr>"

    acq_rows = "".join(
        "<tr>"
        f"<td><code>{_esc_html(r['source'])}</code></td>"
        f"<td class='num'>{r['users']}</td>"
        f"<td class='num'>{r['onboarded']}"
        f"<span class='pct'>{r['onboard_pct']}%</span></td>"
        f"<td class='num'>{r['active_7d']}</td>"
        f"<td class='num'>{r['paid']}"
        f"<span class='pct'>{r['paid_pct']}%</span></td>"
        "</tr>"
        for r in acquisition
    ) or (
        "<tr><td colspan='5' class='muted'>"
        "Пока нет данных — используйте ссылки "
        "<code>?start=ad_имя</code> / <code>?startapp=ad_имя</code>"
        "</td></tr>"
    )

    s = summary
    html = f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Аналитика — Astro Admin</title>
<style>
  :root {{
    --bg:#0e0c12; --surface:#17141e; --border:#2a2433;
    --text:#f2ebe3; --muted:#9a8f9f; --gold:#d4b254;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 20px; font-family: system-ui, sans-serif;
    background: var(--bg); color: var(--text); max-width: 1100px; margin-inline: auto;
  }}
  h1 {{ font-family: Georgia, serif; font-weight: 500; margin: 0 0 8px; }}
  h2 {{ font-size: 15px; color: var(--gold); margin: 0 0 10px; font-weight: 500; }}
  .hint {{ color: var(--muted); font-size: 13px; margin-bottom: 18px; }}
  .kpis {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 10px; margin-bottom: 18px;
  }}
  .kpi {{
    background: var(--surface); border: 0.5px solid var(--border);
    border-radius: 12px; padding: 14px;
  }}
  .kpi .v {{ font-size: 22px; font-weight: 600; }}
  .kpi .l {{ font-size: 11px; color: var(--muted); margin-top: 4px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }}
  .card {{
    background: var(--surface); border: 0.5px solid var(--border);
    border-radius: 12px; padding: 14px;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 8px 10px; border-bottom: 0.5px solid var(--border); text-align: left; vertical-align: middle; }}
  th {{ color: var(--muted); font-weight: 500; font-size: 11px; text-transform: uppercase; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  th.num {{ text-align: right; }}
  table.acq {{ table-layout: fixed; }}
  table.acq th:nth-child(1), table.acq td:nth-child(1) {{ width: 28%; }}
  table.acq th:nth-child(n+2), table.acq td:nth-child(n+2) {{ width: 18%; }}
  table.acq code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px; color: var(--gold);
    background: rgba(212,178,84,0.08); padding: 2px 6px; border-radius: 4px;
  }}
  .pct {{ display: block; font-size: 11px; color: var(--muted); font-weight: 400; }}
  .muted {{ color: var(--muted); }}
  code {{ font-size: 12px; }}
  .tabs a {{
    color: var(--muted); text-decoration: none; margin-right: 10px; font-size: 13px;
  }}
  .tabs a.active {{ color: var(--gold); }}
  {_NAV_CSS}
</style>
</head>
<body>
{_admin_nav_html("analytics")}
<h1>Аналитика</h1>
<p class="hint">Уникальные юзеры на шаге за окно (не строгая когорта). Drop = падение к предыдущему шагу.</p>
<div class="tabs">
  <a href="/api/admin/analytics.html?days=1" class="{'active' if days==1 else ''}">1д</a>
  <a href="/api/admin/analytics.html?days=7" class="{'active' if days==7 else ''}">7д</a>
  <a href="/api/admin/analytics.html?days=30" class="{'active' if days==30 else ''}">30д</a>
</div>

<div class="kpis">
  <div class="kpi"><div class="v">{s['dau']}</div><div class="l">DAU (24ч)</div></div>
  <div class="kpi"><div class="v">{s['wau']}</div><div class="l">WAU (7д)</div></div>
  <div class="kpi"><div class="v">{s['mau']}</div><div class="l">MAU (30д)</div></div>
  <div class="kpi"><div class="v">{s['users_total']}</div><div class="l">Всего юзеров</div></div>
  <div class="kpi"><div class="v">{s['users_onboarded']}</div><div class="l">С онбордингом</div></div>
  <div class="kpi"><div class="v">{s['active_premium']}</div><div class="l">Active Premium</div></div>
  <div class="kpi"><div class="v">{s['purchases_7d']}</div><div class="l">Покупки 7д</div></div>
</div>

<section class="card" style="margin-bottom:16px">
  <h2>Источники трафика ({days}д)</h2>
  <p class="hint" style="margin-top:0">First-touch: ссылки
    <code>t.me/bot?start=ad_vk_group1</code> или
    <code>?startapp=ad_vk_group1</code>. Без метки → <code>organic</code>.
  </p>
  <table class="acq">
    <thead><tr>
      <th>Источник</th>
      <th class="num">Юзеры</th>
      <th class="num">Онбординг</th>
      <th class="num">Active 7д</th>
      <th class="num">Купили</th>
    </tr></thead>
    <tbody>{acq_rows}</tbody>
  </table>
</section>

<div class="grid">
{funnel_html}
</div>

<h2 style="margin:22px 0 10px">Оплата по продуктам ({days}д)</h2>
<div class="grid">{product_html}</div>

<section class="card" style="margin-top:16px">
  <h2>Топ экранов (7д)</h2>
  <table><thead><tr><th>Экран</th><th>Юзеры</th></tr></thead>
  <tbody>{screens}</tbody></table>
</section>

<p class="footer muted" style="margin-top:18px;font-size:12px">
  JSON: <a href="/api/admin/analytics?days={days}">/api/admin/analytics?days={days}</a>
  · окно воронок: {days}д
</p>
</body></html>"""
    return HTMLResponse(html)
