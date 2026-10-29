"""registra cuadrillas y tareas operativas por vehículo

Revision ID: 0055
Revises: 0054
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pesca_movimientos", sa.Column("tipo_gasto", sa.String(length=30), nullable=True))
    op.add_column(
        "pesca_movimientos", sa.Column("tipo_comprobante", sa.String(length=30), nullable=True)
    )
    op.add_column("pesca_movimientos", sa.Column("motivo_boleta_muelle", sa.Text(), nullable=True))
    op.add_column("pesca_movimientos", sa.Column("voucher_documento_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_pesca_movimiento_voucher",
        "pesca_movimientos",
        "pesca_documentos",
        ["voucher_documento_id"],
        ["id"],
    )
    op.add_column(
        "pesca_movimiento_abonos", sa.Column("voucher_documento_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_pesca_abono_voucher",
        "pesca_movimiento_abonos",
        "pesca_documentos",
        ["voucher_documento_id"],
        ["id"],
    )
    op.add_column(
        "pesca_operaciones",
        sa.Column(
            "precio_acuerdo_embarcacion_confirmado",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "pesca_operaciones",
        sa.Column(
            "precio_acuerdo_embarcacion_confirmado_por", sa.String(length=200), nullable=True
        ),
    )
    op.add_column(
        "pesca_operaciones",
        sa.Column(
            "precio_acuerdo_embarcacion_confirmado_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.create_table(
        "pesca_asignaciones_cuadrilla",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("operacion_id", sa.Uuid(), nullable=False),
        sa.Column("actividad", sa.String(length=20), nullable=False),
        sa.Column("nombre_integrante", sa.String(length=200), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("monto_pago", sa.Numeric(14, 2), nullable=True),
        sa.Column("asignado_por_cuenta_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["asignado_por_cuenta_id"], ["cuentas_acceso.id"]),
        sa.ForeignKeyConstraint(["operacion_id"], ["pesca_operaciones.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "operacion_id", "actividad", "nombre_integrante"),
    )
    op.create_index(
        "ix_pesca_asignaciones_cuadrilla_tenant_id", "pesca_asignaciones_cuadrilla", ["tenant_id"]
    )
    op.create_index(
        "ix_pesca_asignaciones_cuadrilla_operacion_id",
        "pesca_asignaciones_cuadrilla",
        ["operacion_id"],
    )
    op.create_index(
        "ix_pesca_asignaciones_cuadrilla_actividad", "pesca_asignaciones_cuadrilla", ["actividad"]
    )
    op.add_column(
        "pesca_operaciones",
        sa.Column("modalidad_pago_cuadrilla", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "pesca_operaciones", sa.Column("monto_pago_cuadrilla", sa.Numeric(14, 2), nullable=True)
    )
    op.add_column(
        "pesca_operaciones",
        sa.Column("responsable_pesaje_muelle", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "pesca_operaciones",
        sa.Column("responsable_pesaje_muelle_cuenta_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_pesca_operacion_responsable_pesaje",
        "pesca_operaciones",
        "cuentas_acceso",
        ["responsable_pesaje_muelle_cuenta_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "pesca_actividades_cuadrilla",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("operacion_id", sa.Uuid(), nullable=False),
        sa.Column("vehiculo_id", sa.Uuid(), nullable=False),
        sa.Column("actividad", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), server_default="en_proceso", nullable=False),
        sa.Column("cajas", sa.Integer(), nullable=True),
        sa.Column("hielo_kg", sa.Numeric(14, 3), nullable=True),
        sa.Column("verificacion_visual", sa.Boolean(), nullable=True),
        sa.Column("contaminacion_detectada", sa.Boolean(), nullable=True),
        sa.Column("revision_final", sa.Boolean(), nullable=True),
        sa.Column("observacion", sa.Text(), nullable=True),
        sa.Column("actor_cuenta_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["actor_cuenta_id"], ["cuentas_acceso.id"]),
        sa.ForeignKeyConstraint(["operacion_id"], ["pesca_operaciones.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vehiculo_id"], ["pesca_vehiculos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "vehiculo_id", "actividad"),
    )
    op.create_index(
        "ix_pesca_actividades_cuadrilla_tenant_id", "pesca_actividades_cuadrilla", ["tenant_id"]
    )
    op.create_index(
        "ix_pesca_actividades_cuadrilla_operacion_id",
        "pesca_actividades_cuadrilla",
        ["operacion_id"],
    )
    op.create_index(
        "ix_pesca_actividades_cuadrilla_vehiculo_id", "pesca_actividades_cuadrilla", ["vehiculo_id"]
    )
    op.create_index(
        "ix_pesca_actividades_cuadrilla_actividad", "pesca_actividades_cuadrilla", ["actividad"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pesca_actividades_cuadrilla_actividad", table_name="pesca_actividades_cuadrilla"
    )
    op.drop_index(
        "ix_pesca_actividades_cuadrilla_vehiculo_id", table_name="pesca_actividades_cuadrilla"
    )
    op.drop_index(
        "ix_pesca_actividades_cuadrilla_operacion_id", table_name="pesca_actividades_cuadrilla"
    )
    op.drop_index(
        "ix_pesca_actividades_cuadrilla_tenant_id", table_name="pesca_actividades_cuadrilla"
    )
    op.drop_table("pesca_actividades_cuadrilla")
    op.drop_column("pesca_movimientos", "motivo_boleta_muelle")
    op.drop_column("pesca_movimientos", "tipo_comprobante")
    op.drop_column("pesca_movimientos", "tipo_gasto")
    op.drop_constraint("fk_pesca_abono_voucher", "pesca_movimiento_abonos", type_="foreignkey")
    op.drop_column("pesca_movimiento_abonos", "voucher_documento_id")
    op.drop_constraint("fk_pesca_movimiento_voucher", "pesca_movimientos", type_="foreignkey")
    op.drop_column("pesca_movimientos", "voucher_documento_id")
    op.drop_column("pesca_operaciones", "monto_pago_cuadrilla")
    op.drop_column("pesca_operaciones", "modalidad_pago_cuadrilla")
    op.drop_column("pesca_operaciones", "responsable_pesaje_muelle")
    op.drop_constraint(
        "fk_pesca_operacion_responsable_pesaje", "pesca_operaciones", type_="foreignkey"
    )
    op.drop_column("pesca_operaciones", "responsable_pesaje_muelle_cuenta_id")
    op.drop_column("pesca_operaciones", "precio_acuerdo_embarcacion_confirmado_at")
    op.drop_column("pesca_operaciones", "precio_acuerdo_embarcacion_confirmado_por")
    op.drop_column("pesca_operaciones", "precio_acuerdo_embarcacion_confirmado")
    op.drop_index(
        "ix_pesca_asignaciones_cuadrilla_actividad", table_name="pesca_asignaciones_cuadrilla"
    )
    op.drop_index(
        "ix_pesca_asignaciones_cuadrilla_operacion_id", table_name="pesca_asignaciones_cuadrilla"
    )
    op.drop_index(
        "ix_pesca_asignaciones_cuadrilla_tenant_id", table_name="pesca_asignaciones_cuadrilla"
    )
    op.drop_table("pesca_asignaciones_cuadrilla")
