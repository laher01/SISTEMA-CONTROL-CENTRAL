"""Solicitudes de cobro de Responsable a Gerencia.

Revision ID: 0044
Revises: 0043
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "solicitudes_cobro_responsables_erp",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("gerente_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("responsable_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("periodo_desde", sa.Date(), nullable=False),
        sa.Column("periodo_hasta", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("produccion_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("comision_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("detalle", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="SOLICITADA"),
        sa.Column("observacion", sa.String(500)),
        sa.Column(
            "creado_por_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False
        ),
    )
    op.create_index(
        "ix_solicitudes_cobro_responsables_erp_tenant_id",
        "solicitudes_cobro_responsables_erp",
        ["tenant_id"],
    )
    op.create_index(
        "ix_solicitudes_cobro_responsables_erp_gerente_id",
        "solicitudes_cobro_responsables_erp",
        ["gerente_id"],
    )
    op.create_index(
        "ix_solicitudes_cobro_responsables_erp_responsable_id",
        "solicitudes_cobro_responsables_erp",
        ["responsable_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_solicitudes_cobro_responsables_erp_responsable_id",
        table_name="solicitudes_cobro_responsables_erp",
    )
    op.drop_index(
        "ix_solicitudes_cobro_responsables_erp_gerente_id",
        table_name="solicitudes_cobro_responsables_erp",
    )
    op.drop_index(
        "ix_solicitudes_cobro_responsables_erp_tenant_id",
        table_name="solicitudes_cobro_responsables_erp",
    )
    op.drop_table("solicitudes_cobro_responsables_erp")
