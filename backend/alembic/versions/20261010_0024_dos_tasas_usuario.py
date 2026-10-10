"""Dos porcentajes contractuales por Usuario.

Revision ID: 0024
Revises: 0023
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("miembros", sa.Column("porcentaje_con_agente", sa.Numeric(7, 4), nullable=True))
    op.add_column("miembros", sa.Column("porcentaje_sin_agente", sa.Numeric(7, 4), nullable=True))
    op.execute(
        """
        UPDATE miembros
        SET porcentaje_con_agente = COALESCE(porcentaje_produccion, 1.5000),
            porcentaje_sin_agente = COALESCE(porcentaje_produccion, 1.5000)
        WHERE rol = 'USUARIO'
        """
    )


def downgrade() -> None:
    op.drop_column("miembros", "porcentaje_sin_agente")
    op.drop_column("miembros", "porcentaje_con_agente")
