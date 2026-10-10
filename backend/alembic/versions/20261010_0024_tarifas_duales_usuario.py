"""Tarifas independientes del Usuario con/sin agente de retención.

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
    op.add_column("miembros", sa.Column("porcentaje_sin_retencion", sa.Numeric(7, 4), nullable=True))
    op.add_column("miembros", sa.Column("porcentaje_con_retencion", sa.Numeric(7, 4), nullable=True))
    # Nunca inventar tasa con retención a partir de la tasa única anterior.
    op.execute(
        """UPDATE miembros
        SET porcentaje_sin_retencion = porcentaje_produccion
        WHERE rol = 'USUARIO' AND porcentaje_produccion IS NOT NULL"""
    )
    op.create_check_constraint(
        "porcentaje_sin_retencion_rango", "miembros",
        "porcentaje_sin_retencion IS NULL OR (porcentaje_sin_retencion >= 0 AND porcentaje_sin_retencion <= 100)",
    )
    op.create_check_constraint(
        "porcentaje_con_retencion_rango", "miembros",
        "porcentaje_con_retencion IS NULL OR (porcentaje_con_retencion >= 0 AND porcentaje_con_retencion <= 100)",
    )


def downgrade() -> None:
    op.drop_constraint("porcentaje_con_retencion_rango", "miembros", type_="check")
    op.drop_constraint("porcentaje_sin_retencion_rango", "miembros", type_="check")
    op.drop_column("miembros", "porcentaje_con_retencion")
    op.drop_column("miembros", "porcentaje_sin_retencion")
