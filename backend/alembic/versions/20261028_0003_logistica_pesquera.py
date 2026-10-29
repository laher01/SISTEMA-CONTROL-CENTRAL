"""amplía la operación pesquera para la logística trazable

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("pesca_documentos") as batch_op:
        batch_op.alter_column("operacion_id", existing_type=sa.Uuid(), nullable=True)
    for name, column in (
        ("armador_reportante", sa.String(200)),
        ("comprador", sa.String(200)),
        ("remitente", sa.String(200)),
        ("destinatario", sa.String(200)),
        ("facturador", sa.String(200)),
        ("toneladas_declaradas", sa.Numeric(14, 3)),
        ("precio_propuesto", sa.Numeric(14, 2)),
        ("precio_confirmado", sa.Numeric(14, 2)),
        ("precio_confirmado_por", sa.String(200)),
        ("precio_confirmado_at", sa.DateTime(timezone=True)),
        ("descarga_prevista", sa.DateTime(timezone=True)),
        ("llegada_planta_prevista", sa.DateTime(timezone=True)),
        ("jefe_bahia", sa.String(200)),
        ("encargado_muelle", sa.String(200)),
        ("apuntador", sa.String(200)),
        ("factura_serie", sa.String(20)),
        ("factura_correlativo", sa.String(30)),
        ("factura_emitida_at", sa.DateTime(timezone=True)),
        ("factura_emitida_por", sa.String(200)),
    ):
        op.add_column("pesca_operaciones", sa.Column(name, column, nullable=True))
    op.add_column("pesca_operaciones", sa.Column("estado_facturacion", sa.String(30), nullable=False, server_default="pendiente"))
    op.add_column("pesca_descargas_embarcacion", sa.Column("peso_declarado_kg", sa.Numeric(14, 3), nullable=True))
    op.add_column("pesca_vehiculos", sa.Column("salida_muelle", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pesca_embarcaciones", sa.Column("armador", sa.String(200), nullable=True))
    op.add_column("pesca_embarcaciones", sa.Column("patron", sa.String(200), nullable=True))
    op.create_table(
        "pesca_documento_embarcaciones",
        sa.Column("documento_id", sa.Uuid(), sa.ForeignKey("pesca_documentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("embarcacion_id", sa.Uuid(), sa.ForeignKey("pesca_embarcaciones.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("documento_id", "embarcacion_id", name="pk_pesca_documento_embarcaciones"),
    )
    op.create_table(
        "pesca_movimientos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("operacion_id", sa.Uuid(), sa.ForeignKey("pesca_operaciones.id", ondelete="CASCADE")),
        sa.Column("clase", sa.String(40), nullable=False),
        sa.Column("pagador", sa.String(200), nullable=False),
        sa.Column("beneficiario", sa.String(200), nullable=False),
        sa.Column("concepto", sa.String(300), nullable=False),
        sa.Column("importe", sa.Numeric(14, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="PEN"),
        sa.Column("cantidad", sa.Numeric(14, 3)),
        sa.Column("tarifa_unitaria", sa.Numeric(14, 2)),
        sa.Column("comprobante_documento_id", sa.Uuid(), sa.ForeignKey("pesca_documentos.id")),
        sa.Column("registrado_por", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(clase = 'prestamo_personal_bahia' AND operacion_id IS NULL) OR "
            "(clase <> 'prestamo_personal_bahia' AND operacion_id IS NOT NULL)",
            name="ck_pesca_movimientos_prestamo_personal_sin_operacion",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pesca_movimientos"),
    )
    op.create_index("ix_pesca_movimientos_tenant_id", "pesca_movimientos", ["tenant_id"])
    op.create_index("ix_pesca_movimientos_operacion_id", "pesca_movimientos", ["operacion_id"])
    op.create_index("ix_pesca_movimientos_clase", "pesca_movimientos", ["clase"])
    op.create_table(
        "pesca_movimiento_abonos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("movimiento_id", sa.Uuid(), sa.ForeignKey("pesca_movimientos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("importe", sa.Numeric(14, 2), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("registrado_por", sa.String(200), nullable=False),
        sa.Column("observacion", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_pesca_movimiento_abonos"),
    )
    op.create_index("ix_pesca_movimiento_abonos_tenant_id", "pesca_movimiento_abonos", ["tenant_id"])
    op.create_index("ix_pesca_movimiento_abonos_movimiento_id", "pesca_movimiento_abonos", ["movimiento_id"])


def downgrade() -> None:
    op.drop_index("ix_pesca_movimiento_abonos_movimiento_id", table_name="pesca_movimiento_abonos")
    op.drop_index("ix_pesca_movimiento_abonos_tenant_id", table_name="pesca_movimiento_abonos")
    op.drop_table("pesca_movimiento_abonos")
    op.drop_index("ix_pesca_movimientos_clase", table_name="pesca_movimientos")
    op.drop_index("ix_pesca_movimientos_operacion_id", table_name="pesca_movimientos")
    op.drop_index("ix_pesca_movimientos_tenant_id", table_name="pesca_movimientos")
    op.drop_table("pesca_movimientos")
    op.drop_table("pesca_documento_embarcaciones")
    with op.batch_alter_table("pesca_documentos") as batch_op:
        batch_op.alter_column("operacion_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("pesca_embarcaciones", "patron")
    op.drop_column("pesca_embarcaciones", "armador")
    op.drop_column("pesca_descargas_embarcacion", "peso_declarado_kg")
    op.drop_column("pesca_vehiculos", "salida_muelle")
    for name in (
        "apuntador",
        "estado_facturacion",
        "factura_emitida_por",
        "factura_emitida_at",
        "factura_correlativo",
        "factura_serie",
        "encargado_muelle",
        "jefe_bahia",
        "llegada_planta_prevista",
        "descarga_prevista",
        "precio_confirmado_at",
        "precio_confirmado_por",
        "precio_confirmado",
        "precio_propuesto",
        "toneladas_declaradas",
        "facturador",
        "destinatario",
        "remitente",
        "comprador",
        "armador_reportante",
    ):
        op.drop_column("pesca_operaciones", name)
