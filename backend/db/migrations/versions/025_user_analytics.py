"""User activity analytics: last_seen + product funnel events.

Revision ID: 025_user_analytics
Revises: 024_structured_natal_report
"""

import sqlalchemy as sa
from alembic import op

revision = "025_user_analytics"
down_revision = "024_structured_natal_report"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_last_seen_at", "users", ["last_seen_at"])

    op.create_table(
        "user_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=True),
        sa.Column("props", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_events_user_id", "user_events", ["user_id"])
    op.create_index("ix_user_events_event", "user_events", ["event"])
    op.create_index("ix_user_events_created_at", "user_events", ["created_at"])
    op.create_index(
        "ix_user_events_event_created",
        "user_events",
        ["event", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_events_event_created", table_name="user_events")
    op.drop_index("ix_user_events_created_at", table_name="user_events")
    op.drop_index("ix_user_events_event", table_name="user_events")
    op.drop_index("ix_user_events_user_id", table_name="user_events")
    op.drop_table("user_events")
    op.drop_index("ix_users_last_seen_at", table_name="users")
    op.drop_column("users", "last_seen_at")
