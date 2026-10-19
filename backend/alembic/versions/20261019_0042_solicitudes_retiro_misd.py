"""Solicitudes y decisiones auditables de retiro MISD.

Revision ID: 0042
Revises: 0041

La revisión 0042 continúa la 0041 de main; verificar siempre Alembic en CI.
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "solicitudes_retiro_misd",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expediente_id", sa.Uuid(), sa.ForeignKey("expedientes.id"), nullable=False),
        sa.Column(
            "solicitante_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False
        ),
        sa.Column("solicitante_rol", sa.String(20), nullable=False),
        sa.Column("solicitante_miembro_id", sa.Uuid(), sa.ForeignKey("miembros.id")),
        sa.Column("solicitante_gestor_id", sa.Uuid(), sa.ForeignKey("gestores.id")),
        sa.Column("motivo", sa.String(500), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
        sa.Column("notificado_a", sa.JSON(), nullable=False),
        sa.Column("aprobado_por_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id")),
        sa.Column("decidido_at", sa.DateTime(timezone=True)),
        sa.Column("decision_motivo", sa.String(500)),
    )
    op.create_index(
        "ix_solicitudes_retiro_misd_tenant_estado",
        "solicitudes_retiro_misd",
        ["tenant_id", "estado"],
    )
    op.create_index(
        "ix_solicitudes_retiro_misd_expediente_id",
        "solicitudes_retiro_misd",
        ["expediente_id"],
    )
    op.create_index(
        "ix_solicitudes_retiro_misd_solicitante_cuenta_id",
        "solicitudes_retiro_misd",
        ["solicitante_cuenta_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_solicitudes_retiro_misd_solicitante_cuenta_id")
    op.drop_index("ix_solicitudes_retiro_misd_expediente_id")
    op.drop_index("ix_solicitudes_retiro_misd_tenant_estado")
    op.drop_table("solicitudes_retiro_misd")
