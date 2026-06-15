"""Add support_tickets table.

One row per user DM to @astrosupport24_bot. First user message + first
admin reply (MVP v1). No FK to users — people can DM the bot without
having a main-app user row, and tickets should survive user deletion.

Revision ID: 020_support_tickets
Create Date: 2026-06-15
"""

import sqlalchemy as sa  # noqa: I001
from alembic import op

revision = "020_support_tickets"
down_revision = "019_yukassa_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("tg_username", sa.String(64), nullable=True),
        sa.Column("tg_first_name", sa.String(128), nullable=True),
        sa.Column("tg_last_name", sa.String(128), nullable=True),
        sa.Column("user_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("user_message_id", sa.BigInteger(), nullable=True),
        sa.Column("forwarded_msg_id", sa.BigInteger(), nullable=True),
        sa.Column("header_msg_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("open", "answered", name="supportticketstatus"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("admin_reply", sa.Text(), nullable=True),
        sa.Column("admin_user_id", sa.BigInteger(), nullable=True),
        sa.Column("admin_username", sa.String(64), nullable=True),
        sa.Column(
            "answered_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_support_tickets_user_id", "support_tickets", ["user_id"],
    )
    op.create_index(
        "ix_support_tickets_forwarded_msg_id",
        "support_tickets",
        ["forwarded_msg_id"],
    )
    op.create_index(
        "ix_support_tickets_status", "support_tickets", ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index(
        "ix_support_tickets_forwarded_msg_id", table_name="support_tickets",
    )
    op.drop_index("ix_support_tickets_user_id", table_name="support_tickets")
    op.drop_table("support_tickets")
    op.execute("DROP TYPE IF EXISTS supportticketstatus")
