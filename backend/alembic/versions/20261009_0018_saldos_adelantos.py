"""Saldos pendientes multimes y adelantos escogidos por liquidación.

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pagos_erp", sa.Column("referencia_pago", sa.String(160), nullable=True))
    op.add_column(
        "pagos_erp", sa.Column("observacion_adelantos", sa.String(500), nullable=True)
    )
    op.create_table(
        "saldos_compras_erp",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("periodo_mes", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("detalle", sa.String(500), nullable=False),
        sa.Column("pago_id", sa.Uuid(), sa.ForeignKey("pagos_erp.id"), nullable=True),
        sa.Column(
            "creado_por_cuenta_id", sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"), nullable=False,
        ),
    )
    for nombre in ("tenant_id", "usuario_id", "periodo_mes", "pago_id"):
        op.create_index(
            f"ix_saldos_compras_erp_{nombre}", "saldos_compras_erp", [nombre]
        )
    op.create_table(
        "aplicaciones_adelantos_erp",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("adelanto_id", sa.Uuid(), sa.ForeignKey("adelantos_erp.id"), nullable=False),
        sa.Column("pago_id", sa.Uuid(), sa.ForeignKey("pagos_erp.id"), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "creado_por_cuenta_id", sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"), nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "adelanto_id"),
    )
    for nombre in ("tenant_id", "adelanto_id", "pago_id", "usuario_id"):
        op.create_index(
            f"ix_aplicaciones_adelantos_erp_{nombre}", "aplicaciones_adelantos_erp", [nombre]
        )


def downgrade() -> None:
    for nombre in ("tenant_id", "adelanto_id", "pago_id", "usuario_id"):
        op.drop_index(
            f"ix_aplicaciones_adelantos_erp_{nombre}",
            table_name="aplicaciones_adelantos_erp",
        )
    op.drop_table("aplicaciones_adelantos_erp")
    for nombre in ("tenant_id", "usuario_id", "periodo_mes", "pago_id"):
        op.drop_index(
            f"ix_saldos_compras_erp_{nombre}", table_name="saldos_compras_erp"
        )
    op.drop_table("saldos_compras_erp")
    op.drop_column("pagos_erp", "observacion_adelantos")
    op.drop_column("pagos_erp", "referencia_pago")
