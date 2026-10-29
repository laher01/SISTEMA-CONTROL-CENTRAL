"""separa la llegada a planta del inicio de descarga

Revision ID: 0053
Revises: 0052
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pesca_vehiculos", sa.Column("llegada_planta", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute(
        "UPDATE pesca_vehiculos SET llegada_planta = inicio_planta "
        "WHERE llegada_planta IS NULL AND inicio_planta IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("pesca_vehiculos", "llegada_planta")
