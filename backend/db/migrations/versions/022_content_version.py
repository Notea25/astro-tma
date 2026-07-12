"""Version generated content so legacy rows can be regenerated safely.

Revision ID: 022_content_version
Revises: 021_widen_interpretation_keys
"""

import sqlalchemy as sa
from alembic import op

revision = "022_content_version"
down_revision = "021_widen_interpretation_keys"
branch_labels = None
depends_on = None

TABLES = (
    "daily_horoscopes",
    "synastry_interpretations",
    "transit_interpretations",
    "synastry_pair_summaries",
    "destiny_matrix_interpretations",
    "destiny_interpretations_v3",
    "year_energy_interpretations",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "content_version",
                sa.String(length=32),
                nullable=False,
                server_default="legacy",
            ),
        )

    op.drop_constraint(
        "pk_year_energy_interpretations",
        "year_energy_interpretations",
        type_="primary",
    )
    op.create_primary_key(
        "pk_year_energy_interpretations",
        "year_energy_interpretations",
        ["user_id", "year_arcana", "content_version"],
    )

    op.drop_constraint(
        "uq_horoscope", "daily_horoscopes", type_="unique"
    )
    op.create_unique_constraint(
        "uq_daily_horoscope_period_version",
        "daily_horoscopes",
        ["sign", "date", "period", "content_version"],
    )

    op.drop_constraint(
        "uq_synastry_pair_summary_key",
        "synastry_pair_summaries",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_synastry_pair_summary_key_version",
        "synastry_pair_summaries",
        ["key_hash", "content_version"],
    )

    op.drop_constraint(
        "uq_synastry_interp_triple", "synastry_interpretations", type_="unique"
    )
    op.create_unique_constraint(
        "uq_synastry_interp_triple_version",
        "synastry_interpretations",
        ["p1", "p2", "aspect", "content_version"],
    )
    op.drop_constraint(
        "uq_transit_interp_triple", "transit_interpretations", type_="unique"
    )
    op.create_unique_constraint(
        "uq_transit_interp_triple_version",
        "transit_interpretations",
        ["transit_planet", "natal_planet", "aspect", "content_version"],
    )
    op.drop_constraint(
        "uq_dm_interp_reading", "destiny_matrix_interpretations", type_="unique"
    )
    op.create_unique_constraint(
        "uq_dm_interp_reading_version",
        "destiny_matrix_interpretations",
        ["reading_id", "content_version"],
    )
    op.drop_constraint(
        "uq_destiny_v3_user_section", "destiny_interpretations_v3", type_="unique"
    )
    op.create_unique_constraint(
        "uq_destiny_v3_user_section_version",
        "destiny_interpretations_v3",
        ["user_id", "birth_date", "gender", "section", "content_version"],
    )


def downgrade() -> None:
    # Versioned rows may coexist. Keep the oldest row for every legacy key
    # before restoring the pre-version uniqueness constraints.
    op.execute("""
        DELETE FROM daily_horoscopes newer USING daily_horoscopes older
        WHERE newer.sign = older.sign AND newer.date = older.date
          AND newer.period = older.period AND newer.id > older.id
    """)
    op.execute("""
        DELETE FROM synastry_interpretations newer USING synastry_interpretations older
        WHERE newer.p1 = older.p1 AND newer.p2 = older.p2
          AND newer.aspect = older.aspect AND newer.id > older.id
    """)
    op.execute("""
        DELETE FROM transit_interpretations newer USING transit_interpretations older
        WHERE newer.transit_planet = older.transit_planet
          AND newer.natal_planet = older.natal_planet
          AND newer.aspect = older.aspect AND newer.id > older.id
    """)
    op.execute("""
        DELETE FROM destiny_matrix_interpretations newer
        USING destiny_matrix_interpretations older
        WHERE newer.reading_id = older.reading_id AND newer.id > older.id
    """)
    op.execute("""
        DELETE FROM destiny_interpretations_v3 newer
        USING destiny_interpretations_v3 older
        WHERE newer.user_id = older.user_id
          AND newer.birth_date = older.birth_date
          AND newer.gender = older.gender
          AND newer.section = older.section
          AND newer.id > older.id
    """)
    op.execute("""
        DELETE FROM year_energy_interpretations newer
        USING year_energy_interpretations older
        WHERE newer.user_id = older.user_id
          AND newer.year_arcana = older.year_arcana
          AND newer.content_version > older.content_version
    """)
    op.drop_constraint(
        "pk_year_energy_interpretations",
        "year_energy_interpretations",
        type_="primary",
    )
    op.create_primary_key(
        "pk_year_energy_interpretations",
        "year_energy_interpretations",
        ["user_id", "year_arcana"],
    )
    op.drop_constraint(
        "uq_daily_horoscope_period_version", "daily_horoscopes", type_="unique"
    )
    op.create_unique_constraint(
        "uq_horoscope",
        "daily_horoscopes",
        ["sign", "date", "period"],
    )
    op.execute(
        """
        DELETE FROM synastry_pair_summaries newer
        USING synastry_pair_summaries older
        WHERE newer.key_hash = older.key_hash
          AND newer.id > older.id
        """
    )
    op.drop_constraint(
        "uq_synastry_pair_summary_key_version",
        "synastry_pair_summaries",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_synastry_pair_summary_key",
        "synastry_pair_summaries",
        ["key_hash"],
    )
    op.drop_constraint(
        "uq_destiny_v3_user_section_version",
        "destiny_interpretations_v3",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_destiny_v3_user_section",
        "destiny_interpretations_v3",
        ["user_id", "birth_date", "gender", "section"],
    )
    op.drop_constraint(
        "uq_dm_interp_reading_version",
        "destiny_matrix_interpretations",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_dm_interp_reading",
        "destiny_matrix_interpretations",
        ["reading_id"],
    )
    op.drop_constraint(
        "uq_transit_interp_triple_version",
        "transit_interpretations",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_transit_interp_triple",
        "transit_interpretations",
        ["transit_planet", "natal_planet", "aspect"],
    )
    op.drop_constraint(
        "uq_synastry_interp_triple_version",
        "synastry_interpretations",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_synastry_interp_triple",
        "synastry_interpretations",
        ["p1", "p2", "aspect"],
    )
    for table in reversed(TABLES):
        op.drop_column(table, "content_version")
