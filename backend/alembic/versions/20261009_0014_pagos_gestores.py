"""Porcentaje de Gestor y pagos programados separados por nivel jerárquico.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gestores", sa.Column("porcentaje_comision", sa.Numeric(7, 4), nullable=True)
    )
    op.create_table(
        "pagos_gestores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("gestor_id", sa.Uuid(), sa.ForeignKey("gestores.id"), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("creado_por_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id")),
        sa.Column("periodo_desde", sa.Date(), nullable=False),
        sa.Column("periodo_hasta", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("produccion_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("porcentaje", sa.Numeric(7, 4), nullable=False),
        sa.Column("bruto", sa.Numeric(14, 2), nullable=False),
        sa.Column("saldo", sa.Numeric(14, 2), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "gestor_id", "periodo_desde", "periodo_hasta", "moneda",
            name="uq_pagos_gestores_periodo",
        ),
    )
    for col in ("tenant_id", "gestor_id", "usuario_id", "creado_por_cuenta_id"):
        op.create_index(f"ix_pagos_gestores_{col}", "pagos_gestores", [col])


def downgrade() -> None:
    for col in ("tenant_id", "gestor_id", "usuario_id", "creado_por_cuenta_id"):
        op.drop_index(f"ix_pagos_gestores_{col}", table_name="pagos_gestores")
    op.drop_table("pagos_gestores")
    op.drop_column("gestores", "porcentaje_comision")
