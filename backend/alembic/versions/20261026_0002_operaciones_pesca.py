"""tablas operativas de descarga y entrega en planta

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id() -> sa.Column[object]:
    return sa.Column("id", sa.Uuid(), nullable=False)


def _tenant() -> sa.Column[object]:
    return sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False)


def _created() -> sa.Column[object]:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "pesca_operaciones",
        sa.Column("fecha_reporte", sa.Date(), nullable=False),
        sa.Column("puerto", sa.String(100), nullable=False),
        sa.Column("muelle", sa.String(200), nullable=False),
        sa.Column("planta", sa.String(200), nullable=False),
        sa.Column("responsable_id", sa.String(200), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="en_descarga"),
        sa.Column("observacion", sa.Text()),
        _id(), _tenant(), _created(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pesca_operaciones")),
    )
    op.create_table(
        "pesca_embarcaciones",
        sa.Column("matricula", sa.String(40), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("patron_armador", sa.String(200), nullable=False),
        sa.Column("intermediario", sa.String(200)),
        _id(), _tenant(), _created(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pesca_embarcaciones")),
        sa.UniqueConstraint("tenant_id", "matricula", name=op.f("uq_pesca_embarcaciones_tenant_id_matricula")),
    )
    op.create_table(
        "pesca_descargas_embarcacion",
        sa.Column("operacion_id", sa.Uuid(), sa.ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("embarcacion_id", sa.Uuid(), sa.ForeignKey("pesca_embarcaciones.id"), nullable=False),
        sa.Column("inicio_descarga", sa.DateTime(timezone=True)),
        sa.Column("fin_descarga", sa.DateTime(timezone=True)),
        _id(), _tenant(), _created(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pesca_descargas_embarcacion")),
        sa.UniqueConstraint("operacion_id", "embarcacion_id", name=op.f("uq_pesca_descargas_embarcacion_operacion_id_embarcacion_id")),
    )
    op.create_table(
        "pesca_vehiculos",
        sa.Column("operacion_id", sa.Uuid(), sa.ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("placa", sa.String(20), nullable=False),
        sa.Column("tipo", sa.String(60), nullable=False),
        sa.Column("chofer", sa.String(200), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="pendiente_planta"),
        sa.Column("fecha_reporte_planta", sa.Date()),
        sa.Column("inicio_planta", sa.DateTime(timezone=True)),
        sa.Column("fin_planta", sa.DateTime(timezone=True)),
        sa.Column("turno", sa.String(80)),
        _id(), _tenant(), _created(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pesca_vehiculos")),
    )
    op.create_table(
        "pesca_cargas",
        sa.Column("descarga_id", sa.Uuid(), sa.ForeignKey("pesca_descargas_embarcacion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehiculo_id", sa.Uuid(), sa.ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("peso_muelle_kg", sa.Numeric(14, 3)),
        sa.Column("cajas", sa.Integer()),
        sa.Column("observacion", sa.Text()),
        _id(), _tenant(), _created(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pesca_cargas")),
    )
    op.create_table(
        "pesca_registros_planta",
        sa.Column("vehiculo_id", sa.Uuid(), sa.ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resultado", sa.String(20), nullable=False),
        sa.Column("peso_aceptado", sa.Numeric(14, 3), nullable=False),
        sa.Column("unidad", sa.String(10), nullable=False, server_default="ton"),
        sa.Column("cajas_rechazadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("motivo_rechazo", sa.String(200)),
        sa.Column("fecha_finalizacion", sa.DateTime(timezone=True)),
        sa.Column("observacion", sa.Text()),
        _id(), _tenant(), _created(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pesca_registros_planta")),
        sa.UniqueConstraint("vehiculo_id", name=op.f("uq_pesca_registros_planta_vehiculo_id")),
    )
    op.create_table(
        "pesca_documentos",
        sa.Column("operacion_id", sa.Uuid(), sa.ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehiculo_id", sa.Uuid(), sa.ForeignKey("pesca_vehiculos.id", ondelete="CASCADE")),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("ruta_storage", sa.String(500), nullable=False),
        sa.Column("subido_por", sa.String(200), nullable=False),
        _id(), _tenant(), _created(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pesca_documentos")),
    )
    op.create_table(
        "pesca_documento_vehiculos",
        sa.Column("documento_id", sa.Uuid(), sa.ForeignKey("pesca_documentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehiculo_id", sa.Uuid(), sa.ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("documento_id", "vehiculo_id", name=op.f("pk_pesca_documento_vehiculos")),
    )
    op.create_table(
        "pesca_historial",
        sa.Column("operacion_id", sa.Uuid(), sa.ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehiculo_id", sa.Uuid(), sa.ForeignKey("pesca_vehiculos.id", ondelete="CASCADE")),
        sa.Column("accion", sa.String(60), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=False),
        _id(), _tenant(), _created(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pesca_historial")),
    )

    for table, column in (
        ("pesca_operaciones", "tenant_id"),
        ("pesca_operaciones", "fecha_reporte"),
        ("pesca_operaciones", "estado"),
        ("pesca_embarcaciones", "tenant_id"),
        ("pesca_descargas_embarcacion", "tenant_id"),
        ("pesca_descargas_embarcacion", "operacion_id"),
        ("pesca_descargas_embarcacion", "embarcacion_id"),
        ("pesca_vehiculos", "tenant_id"),
        ("pesca_vehiculos", "operacion_id"),
        ("pesca_vehiculos", "estado"),
        ("pesca_cargas", "tenant_id"),
        ("pesca_cargas", "descarga_id"),
        ("pesca_cargas", "vehiculo_id"),
        ("pesca_registros_planta", "tenant_id"),
        ("pesca_registros_planta", "vehiculo_id"),
        ("pesca_documentos", "tenant_id"),
        ("pesca_documentos", "operacion_id"),
        ("pesca_documentos", "vehiculo_id"),
        ("pesca_documentos", "tipo"),
        ("pesca_documentos", "sha256"),
        ("pesca_historial", "tenant_id"),
        ("pesca_historial", "operacion_id"),
        ("pesca_historial", "vehiculo_id"),
    ):
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def downgrade() -> None:
    for table in (
        "pesca_historial",
        "pesca_documento_vehiculos",
        "pesca_documentos",
        "pesca_registros_planta",
        "pesca_cargas",
        "pesca_vehiculos",
        "pesca_descargas_embarcacion",
        "pesca_embarcaciones",
        "pesca_operaciones",
    ):
        op.drop_table(table)
