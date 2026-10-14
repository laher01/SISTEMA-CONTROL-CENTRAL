"""Solicitudes de autorización de emisores externos al grupo.

Revision ID: 0035
Revises: 0034
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "solicitudes_carga_emisor",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ruc_emisor", sa.String(11), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), sa.ForeignKey("empresas.id")),
        sa.Column("solicitante_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False),
        sa.Column("usuario_solicitante_id", sa.Uuid(), sa.ForeignKey("miembros.id")),
        sa.Column("gestor_solicitante_id", sa.Uuid(), sa.ForeignKey("gestores.id")),
        sa.Column("gestor_propietario_id", sa.Uuid(), sa.ForeignKey("gestores.id")),
        sa.Column("responsable_propietario_id", sa.Uuid(), sa.ForeignKey("miembros.id")),
        sa.Column("sha256_archivo", sa.String(64), nullable=False),
        sa.Column("ruta_temporal", sa.String(500)),
        sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
        sa.Column("decidido_por_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id")),
        sa.Column("decidido_at", sa.DateTime(timezone=True)),
        sa.Column("observacion", sa.String(500)),
    )
    op.create_index("ix_solicitudes_emisor_pendientes", "solicitudes_carga_emisor", ["tenant_id", "estado"])
    op.create_index("ix_solicitudes_carga_emisor_ruc_emisor", "solicitudes_carga_emisor", ["ruc_emisor"])
    op.create_index("ix_solicitudes_carga_emisor_tenant_id", "solicitudes_carga_emisor", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_solicitudes_carga_emisor_tenant_id", table_name="solicitudes_carga_emisor")
    op.drop_index("ix_solicitudes_carga_emisor_ruc_emisor", table_name="solicitudes_carga_emisor")
    op.drop_index("ix_solicitudes_emisor_pendientes", table_name="solicitudes_carga_emisor")
    op.drop_table("solicitudes_carga_emisor")
