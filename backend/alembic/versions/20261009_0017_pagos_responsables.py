"""Reglas de comisión y pagos de Gerencia a Responsables.

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comisiones_responsable_reglas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("responsable_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("porcentaje", sa.Numeric(7, 4), nullable=False),
        sa.Column(
            "creado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "responsable_id", "cliente_id"),
    )
    op.create_index(
        "ix_comisiones_responsable_reglas_responsable_id",
        "comisiones_responsable_reglas",
        ["responsable_id"],
    )
    op.create_index(
        "ix_comisiones_responsable_reglas_cliente_id",
        "comisiones_responsable_reglas",
        ["cliente_id"],
    )
    op.create_index(
        "ix_comisiones_responsable_reglas_tenant_id",
        "comisiones_responsable_reglas",
        ["tenant_id"],
    )
    op.create_table(
        "pagos_responsables_erp",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responsable_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("periodo_desde", sa.Date(), nullable=False),
        sa.Column("periodo_hasta", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("produccion_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("comision_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("detalle", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=True),
        sa.Column("observacion", sa.String(500), nullable=True),
        sa.Column(
            "creado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=False,
        ),
        sa.Column(
            "pagado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=True,
        ),
        sa.Column("referencia_pago", sa.String(160), nullable=True),
        sa.UniqueConstraint(
            "tenant_id", "responsable_id", "periodo_desde", "periodo_hasta", "moneda"
        ),
    )
    op.create_index(
        "ix_pagos_responsables_erp_responsable_id",
        "pagos_responsables_erp",
        ["responsable_id"],
    )
    op.create_index("ix_pagos_responsables_erp_estado", "pagos_responsables_erp", ["estado"])
    op.create_index("ix_pagos_responsables_erp_tenant_id", "pagos_responsables_erp", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_pagos_responsables_erp_tenant_id", table_name="pagos_responsables_erp")
    op.drop_index("ix_pagos_responsables_erp_estado", table_name="pagos_responsables_erp")
    op.drop_index("ix_pagos_responsables_erp_responsable_id", table_name="pagos_responsables_erp")
    op.drop_table("pagos_responsables_erp")
    op.drop_index(
        "ix_comisiones_responsable_reglas_cliente_id", table_name="comisiones_responsable_reglas"
    )
    op.drop_index(
        "ix_comisiones_responsable_reglas_responsable_id",
        table_name="comisiones_responsable_reglas",
    )
    op.drop_index(
        "ix_comisiones_responsable_reglas_tenant_id", table_name="comisiones_responsable_reglas"
    )
    op.drop_table("comisiones_responsable_reglas")
