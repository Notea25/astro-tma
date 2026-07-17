"""Store the server-resolved birth country code on users.

Revision ID: 025_birth_country_code
Revises: 024_structured_natal_report
"""

import sqlalchemy as sa
from alembic import op

revision = "025_birth_country_code"
down_revision = "024_structured_natal_report"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("birth_country_code", sa.String(length=2), nullable=True),
    )

    # Deterministic legacy backfill only. The companion script resolves the
    # remaining coordinate-bearing rows through Nominatim after human review.
    op.execute(
        sa.text(
            r"""
            UPDATE users
            SET birth_country_code = 'UA'
            WHERE birth_country_code IS NULL
              AND (
                birth_tz IN (
                    'Europe/Kiev',
                    'Europe/Kyiv',
                    'Europe/Uzhgorod',
                    'Europe/Zaporozhye'
                )
                OR COALESCE(birth_city, '') ~*
                    '(^|[,;/|][[:space:]]*)(ukraine|украина|україна)([[:space:]]*([,;/|]|$))'
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("users", "birth_country_code")
