"""Catálogo y líneas de ítems para reportes operativos.

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
        "productos_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("clave_catalogo", sa.String(300), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.Column("categoria", sa.String(80), nullable=False),
        sa.Column("clasificacion_confirmada", sa.Boolean(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("tenant_id", "clave_catalogo"),
    )
    op.create_index("ix_productos_items_tenant_id", "productos_items", ["tenant_id"])
    op.create_table(
        "lineas_comprobantes_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("documento_id", sa.Uuid(), sa.ForeignKey("documentos.id"), nullable=False),
        sa.Column("producto_id", sa.Uuid(), sa.ForeignKey("productos_items.id"), nullable=False),
        sa.Column("numero_linea", sa.Integer(), nullable=False),
        sa.Column("descripcion_original", sa.String(1000), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("unidad", sa.String(40), nullable=False),
        sa.Column("importe_linea", sa.Numeric(18, 2)),
        sa.UniqueConstraint("tenant_id", "documento_id", "numero_linea"),
    )
    op.create_index(
        "ix_lineas_comprobantes_items_tenant_id", "lineas_comprobantes_items", ["tenant_id"])
    op.create_index(
        "ix_lineas_comprobantes_items_documento_id", "lineas_comprobantes_items", ["documento_id"])
    op.create_index(
        "ix_lineas_comprobantes_items_producto_id", "lineas_comprobantes_items", ["producto_id"])
    op.create_table(
        "auditorias_facturas_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expediente_id", sa.Uuid(), sa.ForeignKey("expedientes.id"), nullable=False),
        sa.Column("producto_id", sa.Uuid(), sa.ForeignKey("productos_items.id")),
        sa.Column("estado", sa.String(40), nullable=False),
        sa.Column("motivo", sa.String(1000), nullable=False),
        sa.Column(
            "solicitado_por_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False),
        sa.Column("aprobado_por_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id")),
    )
    op.create_index(
        "ix_auditorias_facturas_items_tenant_id", "auditorias_facturas_items", ["tenant_id"])
    op.create_index(
        "ix_auditorias_facturas_items_expediente_id", "auditorias_facturas_items", ["expediente_id"])
    op.create_index("ix_auditorias_facturas_items_estado", "auditorias_facturas_items", ["estado"])


def downgrade() -> None:
    op.drop_table("auditorias_facturas_items")
    op.drop_table("lineas_comprobantes_items")
    op.drop_table("productos_items")
