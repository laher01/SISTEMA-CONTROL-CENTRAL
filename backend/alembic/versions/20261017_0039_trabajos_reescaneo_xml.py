"""Auditoría y checkpoints de trabajos XML. Sin activar workers.

Revision ID: 0039
Revises: 0038
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trabajos_reescaneo_xml",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "solicitado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=False,
        ),
        sa.Column("clave_idempotencia", sa.String(100), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("cursor_documento_id", sa.Uuid(), sa.ForeignKey("documentos.id")),
        sa.Column("documentos_procesados", sa.Integer(), nullable=False),
        sa.UniqueConstraint("tenant_id", "clave_idempotencia"),
    )
    op.create_index("ix_trabajos_reescaneo_xml_tenant_id", "trabajos_reescaneo_xml", ["tenant_id"])
    op.create_table(
        "eventos_reescaneo_xml",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "trabajo_id", sa.Uuid(), sa.ForeignKey("trabajos_reescaneo_xml.id"), nullable=False
        ),
        sa.Column("actor_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False),
        sa.Column("estado_anterior", sa.String(30), nullable=False),
        sa.Column("estado_nuevo", sa.String(30), nullable=False),
        sa.Column("documento_id", sa.Uuid(), sa.ForeignKey("documentos.id")),
        sa.Column("cursor_documento_id", sa.Uuid(), sa.ForeignKey("documentos.id")),
        sa.Column("ocurrido_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_eventos_reescaneo_xml_tenant_id", "eventos_reescaneo_xml", ["tenant_id"])
    op.create_index("ix_eventos_reescaneo_xml_trabajo_id", "eventos_reescaneo_xml", ["trabajo_id"])


def downgrade() -> None:
    op.drop_table("eventos_reescaneo_xml")
    op.drop_table("trabajos_reescaneo_xml")
