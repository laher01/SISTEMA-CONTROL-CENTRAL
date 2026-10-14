"""Titularidad formal de empresa por grupo.

Revision ID: 0036
Revises: 0035
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asignaciones_empresas_gestores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("empresa_id", sa.Uuid(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("gestor_id", sa.Uuid(), sa.ForeignKey("gestores.id"), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("responsable_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column(
            "creado_por_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False
        ),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "empresa_id", name="uq_asignacion_empresa_tenant"),
    )
    op.create_index("ix_asignaciones_empresas_gestores_empresa_id",
        "asignaciones_empresas_gestores", ["empresa_id"])
    op.create_index("ix_asignaciones_empresas_gestores_gestor_id",
        "asignaciones_empresas_gestores", ["gestor_id"])
    op.create_index("ix_asignaciones_empresas_gestores_tenant_id",
        "asignaciones_empresas_gestores", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_asignaciones_empresas_gestores_tenant_id",
        table_name="asignaciones_empresas_gestores")
    op.drop_index("ix_asignaciones_empresas_gestores_gestor_id",
        table_name="asignaciones_empresas_gestores")
    op.drop_index("ix_asignaciones_empresas_gestores_empresa_id",
        table_name="asignaciones_empresas_gestores")
    op.drop_table("asignaciones_empresas_gestores")
