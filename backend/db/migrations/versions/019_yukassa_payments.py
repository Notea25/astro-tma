"""Add YuKassa payment columns to purchases + subscriptions.

We now accept payments via two providers: Telegram Stars (historical)
and YuKassa (Russian card-payment gateway). Both kinds end up in the
existing `purchases` / `subscriptions` tables; the additional columns
let us tell them apart and idempotently process YuKassa webhooks.

Columns added to BOTH tables:
  - payment_provider: VARCHAR(16) NOT NULL DEFAULT 'stars'
                      ('stars' for legacy/Stars rows, 'yukassa' for card)
  - yukassa_payment_id: VARCHAR(64) NULL UNIQUE
                        (UUID from YuKassa's payment object; idempotency key
                        for retried webhooks)
  - rub_amount_kopecks: INTEGER NULL
                        (net amount in kopecks; NULL on Stars rows)

For `subscriptions` we also drop NOT NULL from `tg_payment_charge_id`
because YuKassa-bought subscriptions don't have one.

Revision ID: 019_yukassa_payments
Create Date: 2026-06-13
"""

import sqlalchemy as sa  # noqa: I001
from alembic import op

revision = "019_yukassa_payments"
down_revision = "018_transit_extras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── purchases ──────────────────────────────────────────────────────
    op.add_column(
        "purchases",
        sa.Column(
            "payment_provider",
            sa.String(16),
            nullable=False,
            server_default="stars",
        ),
    )
    op.add_column(
        "purchases",
        sa.Column("yukassa_payment_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "purchases",
        sa.Column("rub_amount_kopecks", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_purchases_yukassa_payment_id",
        "purchases",
        ["yukassa_payment_id"],
    )

    # ── subscriptions ──────────────────────────────────────────────────
    op.add_column(
        "subscriptions",
        sa.Column(
            "payment_provider",
            sa.String(16),
            nullable=False,
            server_default="stars",
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column("yukassa_payment_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("rub_amount_kopecks", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_subscriptions_yukassa_payment_id",
        "subscriptions",
        ["yukassa_payment_id"],
    )
    # YuKassa-bought subs don't carry a Telegram charge id.
    op.alter_column(
        "subscriptions",
        "tg_payment_charge_id",
        existing_type=sa.String(256),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "subscriptions",
        "tg_payment_charge_id",
        existing_type=sa.String(256),
        nullable=False,
    )
    op.drop_constraint(
        "uq_subscriptions_yukassa_payment_id",
        "subscriptions",
        type_="unique",
    )
    op.drop_column("subscriptions", "rub_amount_kopecks")
    op.drop_column("subscriptions", "yukassa_payment_id")
    op.drop_column("subscriptions", "payment_provider")

    op.drop_constraint(
        "uq_purchases_yukassa_payment_id",
        "purchases",
        type_="unique",
    )
    op.drop_column("purchases", "rub_amount_kopecks")
    op.drop_column("purchases", "yukassa_payment_id")
    op.drop_column("purchases", "payment_provider")
