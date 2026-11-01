"""Devengar comisiones por factura para pagos parciales de periodo.

Revision ID: 0047
Revises: 0046
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devengos_comision_usuario_erp",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("expediente_id", sa.Uuid(), sa.ForeignKey("expedientes.id"), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("agente_retencion", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("base_factura", sa.Numeric(14, 2), nullable=False),
        sa.Column("porcentaje", sa.Numeric(7, 4), nullable=False),
        sa.Column("monto_comision", sa.Numeric(14, 2), nullable=False),
        sa.Column("pago_id", sa.Uuid(), sa.ForeignKey("pagos_erp.id"), nullable=True),
        sa.Column(
            "creado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "expediente_id", name="uq_devengo_comision_expediente"),
    )
    op.create_index(
        "ix_devengos_comision_usuario_erp_usuario_id",
        "devengos_comision_usuario_erp",
        ["usuario_id"],
    )
    op.create_index(
        "ix_devengos_comision_usuario_erp_expediente_id",
        "devengos_comision_usuario_erp",
        ["expediente_id"],
    )
    op.create_index(
        "ix_devengos_comision_usuario_erp_fecha_emision",
        "devengos_comision_usuario_erp",
        ["fecha_emision"],
    )
    op.create_index(
        "ix_devengos_comision_usuario_erp_moneda",
        "devengos_comision_usuario_erp",
        ["moneda"],
    )
    op.create_index(
        "ix_devengos_comision_usuario_erp_pago_id",
        "devengos_comision_usuario_erp",
        ["pago_id"],
    )


def downgrade() -> None:
    op.drop_table("devengos_comision_usuario_erp")
