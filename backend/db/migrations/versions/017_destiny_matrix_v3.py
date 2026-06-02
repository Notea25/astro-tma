"""Destiny Matrix V3 — interpretation pipeline tables.

Adds 4 new tables, leaves all existing destiny-matrix tables alone so the
current octagram + 8-section narrative keep working until V3 ships
end-to-end on the frontend.

    arcana_base
        22 rows × {num, name_ru, essence, mission, shadow, healing,
        activities, famous_people}. Seeded from `book_arcana_base.json`
        (Ладини canon, the source for the V3 LLM prompts).

    karmic_programs
        Up to ~26 unique karmic-tail programs keyed by the
        ``bottom-bottom_1-bottom_2`` triple (e.g. "19-22-3"
        «Нерождённое дитя»). Filled by a one-off Sonnet generator with
        manual editing.

    destiny_interpretations_v3
        Per-user × per-birth_date × per-gender × per-section LLM
        narrative. One row per section (15 of them) so the frontend
        accordion can load + regenerate one card at a time. Permanent
        cache — the matrix doesn't change.

    year_energy_interpretations
        Per-user × per-year_arcana yearly forecast. Refreshed on the
        user's birthday by a cron job; before then it's the
        previous-year reading.

Revision ID: 017_destiny_matrix_v3
Revises: 016_interp_gender_used
Create Date: 2026-06-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP

revision = "017_destiny_matrix_v3"
down_revision = "016_interp_gender_used"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── arcana_base ───────────────────────────────────────────────────
    op.create_table(
        "arcana_base",
        sa.Column("num", sa.SmallInteger, primary_key=True),
        sa.Column("name_ru", sa.Text, nullable=False),
        sa.Column("essence", sa.Text, nullable=False),
        sa.Column("mission", sa.Text, nullable=False),
        sa.Column("shadow", sa.Text, nullable=False),
        sa.Column("healing", sa.Text, nullable=False),
        sa.Column("activities", sa.Text, nullable=False),
        sa.Column("famous_people", sa.Text, nullable=True),
        sa.CheckConstraint("num BETWEEN 1 AND 22", name="ck_arcana_base_num"),
    )

    # ── karmic_programs ───────────────────────────────────────────────
    op.create_table(
        "karmic_programs",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("manifestations", sa.Text, nullable=False),
        sa.Column("how_to_heal", sa.Text, nullable=False),
    )

    # ── destiny_interpretations_v3 ────────────────────────────────────
    op.create_table(
        "destiny_interpretations_v3",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("birth_date", sa.Date, nullable=False),
        # 'male' / 'female' / 'any'; mismatch with current profile ⇒ stale
        sa.Column("gender", sa.String(8), nullable=False),
        # snake_case section keys: visitka, drk, higher_self, …, year_energy
        sa.Column("section", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "birth_date", "gender", "section",
            name="uq_destiny_v3_user_section",
        ),
    )
    op.create_index(
        "idx_destiny_v3_user_bd",
        "destiny_interpretations_v3",
        ["user_id", "birth_date"],
    )

    # ── year_energy_interpretations ───────────────────────────────────
    op.create_table(
        "year_energy_interpretations",
        sa.Column(
            "user_id",
            sa.BigInteger,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # arcana 1..22 for the current life year (recalculated annually)
        sa.Column("year_arcana", sa.SmallInteger, primary_key=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "year_arcana BETWEEN 1 AND 22",
            name="ck_year_energy_arcana",
        ),
    )


def downgrade() -> None:
    op.drop_table("year_energy_interpretations")
    op.drop_index("idx_destiny_v3_user_bd", table_name="destiny_interpretations_v3")
    op.drop_table("destiny_interpretations_v3")
    op.drop_table("karmic_programs")
    op.drop_table("arcana_base")
