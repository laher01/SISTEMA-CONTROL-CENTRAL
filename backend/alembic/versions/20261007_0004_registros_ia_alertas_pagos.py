"""registros ia alertas permisos y pagos erp

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documentos", sa.Column("formato_origen", sa.String(length=30), nullable=True))
    op.create_index(
        op.f("ix_documentos_formato_origen"),
        "documentos",
        ["formato_origen"],
        unique=False,
    )

    op.create_table(
        "perfiles_extraccion",
        sa.Column("ruc", sa.String(length=11), nullable=False),
        sa.Column("tipo_parte", sa.String(length=10), nullable=False),
        sa.Column("formato", sa.String(length=30), nullable=False),
        sa.Column("razon_social", sa.String(length=300), nullable=False),
        sa.Column("confianza", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("usos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_perfiles_extraccion_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_perfiles_extraccion")),
        sa.UniqueConstraint(
            "tenant_id",
            "ruc",
            "tipo_parte",
            "formato",
            name=op.f("uq_perfiles_extraccion_tenant_id_ruc_tipo_parte_formato"),
        ),
    )
    op.create_index(
        op.f("ix_perfiles_extraccion_ruc"),
        "perfiles_extraccion",
        ["ruc"],
        unique=False,
    )
    op.create_index(
        op.f("ix_perfiles_extraccion_formato"),
        "perfiles_extraccion",
        ["formato"],
        unique=False,
    )
    op.create_index(
        op.f("ix_perfiles_extraccion_tenant_id"),
        "perfiles_extraccion",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "correcciones_ia",
        sa.Column("documento_id", sa.Uuid(), nullable=False),
        sa.Column("actor_codigo", sa.String(length=100), nullable=False),
        sa.Column("actor_rol", sa.String(length=20), nullable=False),
        sa.Column("formato", sa.String(length=30), nullable=True),
        sa.Column(
            "resultado_original",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "resultado_corregido",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("motivo", sa.String(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["documento_id"],
            ["documentos.id"],
            name=op.f("fk_correcciones_ia_documento_id_documentos"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_correcciones_ia_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_correcciones_ia")),
    )
    op.create_index(
        op.f("ix_correcciones_ia_documento_id"),
        "correcciones_ia",
        ["documento_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correcciones_ia_formato"),
        "correcciones_ia",
        ["formato"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correcciones_ia_tenant_id"),
        "correcciones_ia",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "alertas_manuales",
        sa.Column("expediente_id", sa.Uuid(), nullable=True),
        sa.Column("creado_por_codigo", sa.String(length=100), nullable=False),
        sa.Column("creado_por_rol", sa.String(length=20), nullable=False),
        sa.Column("destinatario_usuario_id", sa.Uuid(), nullable=True),
        sa.Column("destinatario_gestor_id", sa.Uuid(), nullable=True),
        sa.Column("para_administracion", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("asunto", sa.String(length=200), nullable=False),
        sa.Column("mensaje", sa.String(length=1000), nullable=False),
        sa.Column("resuelta", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("resuelta_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["destinatario_gestor_id"],
            ["gestores.id"],
            name=op.f("fk_alertas_manuales_destinatario_gestor_id_gestores"),
        ),
        sa.ForeignKeyConstraint(
            ["destinatario_usuario_id"],
            ["miembros.id"],
            name=op.f("fk_alertas_manuales_destinatario_usuario_id_miembros"),
        ),
        sa.ForeignKeyConstraint(
            ["expediente_id"],
            ["expedientes.id"],
            name=op.f("fk_alertas_manuales_expediente_id_expedientes"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_alertas_manuales_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alertas_manuales")),
    )
    op.create_index(
        op.f("ix_alertas_manuales_destinatario_gestor_id"),
        "alertas_manuales",
        ["destinatario_gestor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_alertas_manuales_destinatario_usuario_id"),
        "alertas_manuales",
        ["destinatario_usuario_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_alertas_manuales_expediente_id"),
        "alertas_manuales",
        ["expediente_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_alertas_manuales_resuelta"),
        "alertas_manuales",
        ["resuelta"],
        unique=False,
    )
    op.create_index(
        op.f("ix_alertas_manuales_tenant_id"),
        "alertas_manuales",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "permisos_configurados",
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("permiso", sa.String(length=80), nullable=False),
        sa.Column("habilitado", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_permisos_configurados_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permisos_configurados")),
        sa.UniqueConstraint(
            "tenant_id",
            "rol",
            "permiso",
            name=op.f("uq_permisos_configurados_tenant_id_rol_permiso"),
        ),
    )
    op.create_index(
        op.f("ix_permisos_configurados_permiso"),
        "permisos_configurados",
        ["permiso"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permisos_configurados_rol"),
        "permisos_configurados",
        ["rol"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permisos_configurados_tenant_id"),
        "permisos_configurados",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "planes_liquidacion",
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("porcentaje", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("vigencia_desde", sa.Date(), nullable=False),
        sa.Column("vigencia_hasta", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_planes_liquidacion_tenant_id_tenants"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["miembros.id"],
            name=op.f("fk_planes_liquidacion_usuario_id_miembros"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_planes_liquidacion")),
    )
    op.create_index(
        op.f("ix_planes_liquidacion_tenant_id"),
        "planes_liquidacion",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_planes_liquidacion_usuario_id"),
        "planes_liquidacion",
        ["usuario_id"],
        unique=False,
    )

    op.create_table(
        "cuentas_pago_erp",
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("titular", sa.String(length=200), nullable=False),
        sa.Column("banco", sa.String(length=120), nullable=False),
        sa.Column("tipo_cuenta", sa.String(length=50), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("numero_cuenta", sa.String(length=80), nullable=True),
        sa.Column("cci", sa.String(length=40), nullable=True),
        sa.Column("porcentaje_distribucion", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_cuentas_pago_erp_tenant_id_tenants"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["miembros.id"],
            name=op.f("fk_cuentas_pago_erp_usuario_id_miembros"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cuentas_pago_erp")),
    )
    op.create_index(
        op.f("ix_cuentas_pago_erp_tenant_id"),
        "cuentas_pago_erp",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cuentas_pago_erp_usuario_id"),
        "cuentas_pago_erp",
        ["usuario_id"],
        unique=False,
    )

    op.create_table(
        "adelantos_erp",
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("monto", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("descripcion", sa.String(length=500), nullable=True),
        sa.Column("aplicado", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_adelantos_erp_tenant_id_tenants"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["miembros.id"],
            name=op.f("fk_adelantos_erp_usuario_id_miembros"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_adelantos_erp")),
    )
    op.create_index(
        op.f("ix_adelantos_erp_tenant_id"),
        "adelantos_erp",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adelantos_erp_usuario_id"),
        "adelantos_erp",
        ["usuario_id"],
        unique=False,
    )

    op.create_table(
        "pagos_erp",
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column("periodo_desde", sa.Date(), nullable=False),
        sa.Column("periodo_hasta", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("produccion_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("porcentaje", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("bruto", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("adelantos", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("ajustes", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("saldo", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("fecha_programada", sa.Date(), nullable=True),
        sa.Column("fecha_pago", sa.Date(), nullable=True),
        sa.Column("voucher_documento_id", sa.Uuid(), nullable=True),
        sa.Column("conciliado", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["planes_liquidacion.id"],
            name=op.f("fk_pagos_erp_plan_id_planes_liquidacion"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_pagos_erp_tenant_id_tenants"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["miembros.id"],
            name=op.f("fk_pagos_erp_usuario_id_miembros"),
        ),
        sa.ForeignKeyConstraint(
            ["voucher_documento_id"],
            ["documentos.id"],
            name=op.f("fk_pagos_erp_voucher_documento_id_documentos"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pagos_erp")),
        sa.UniqueConstraint(
            "tenant_id",
            "usuario_id",
            "periodo_desde",
            "periodo_hasta",
            "moneda",
            name=op.f(
                "uq_pagos_erp_tenant_id_usuario_id_periodo_desde_periodo_hasta_moneda"
            ),
        ),
    )
    op.create_index(op.f("ix_pagos_erp_estado"), "pagos_erp", ["estado"], unique=False)
    op.create_index(op.f("ix_pagos_erp_plan_id"), "pagos_erp", ["plan_id"], unique=False)
    op.create_index(op.f("ix_pagos_erp_tenant_id"), "pagos_erp", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_pagos_erp_usuario_id"), "pagos_erp", ["usuario_id"], unique=False)
    op.create_index(
        op.f("ix_pagos_erp_voucher_documento_id"),
        "pagos_erp",
        ["voucher_documento_id"],
        unique=False,
    )


def downgrade() -> None:
    for index in (
        "ix_pagos_erp_voucher_documento_id",
        "ix_pagos_erp_usuario_id",
        "ix_pagos_erp_tenant_id",
        "ix_pagos_erp_plan_id",
        "ix_pagos_erp_estado",
    ):
        op.drop_index(op.f(index), table_name="pagos_erp")
    op.drop_table("pagos_erp")

    op.drop_index(op.f("ix_adelantos_erp_usuario_id"), table_name="adelantos_erp")
    op.drop_index(op.f("ix_adelantos_erp_tenant_id"), table_name="adelantos_erp")
    op.drop_table("adelantos_erp")

    op.drop_index(op.f("ix_cuentas_pago_erp_usuario_id"), table_name="cuentas_pago_erp")
    op.drop_index(op.f("ix_cuentas_pago_erp_tenant_id"), table_name="cuentas_pago_erp")
    op.drop_table("cuentas_pago_erp")

    op.drop_index(op.f("ix_planes_liquidacion_usuario_id"), table_name="planes_liquidacion")
    op.drop_index(op.f("ix_planes_liquidacion_tenant_id"), table_name="planes_liquidacion")
    op.drop_table("planes_liquidacion")

    op.drop_index(op.f("ix_permisos_configurados_tenant_id"), table_name="permisos_configurados")
    op.drop_index(op.f("ix_permisos_configurados_rol"), table_name="permisos_configurados")
    op.drop_index(op.f("ix_permisos_configurados_permiso"), table_name="permisos_configurados")
    op.drop_table("permisos_configurados")

    op.drop_index(op.f("ix_alertas_manuales_tenant_id"), table_name="alertas_manuales")
    op.drop_index(op.f("ix_alertas_manuales_resuelta"), table_name="alertas_manuales")
    op.drop_index(op.f("ix_alertas_manuales_expediente_id"), table_name="alertas_manuales")
    op.drop_index(
        op.f("ix_alertas_manuales_destinatario_usuario_id"),
        table_name="alertas_manuales",
    )
    op.drop_index(
        op.f("ix_alertas_manuales_destinatario_gestor_id"),
        table_name="alertas_manuales",
    )
    op.drop_table("alertas_manuales")

    op.drop_index(op.f("ix_correcciones_ia_tenant_id"), table_name="correcciones_ia")
    op.drop_index(op.f("ix_correcciones_ia_formato"), table_name="correcciones_ia")
    op.drop_index(op.f("ix_correcciones_ia_documento_id"), table_name="correcciones_ia")
    op.drop_table("correcciones_ia")

    op.drop_index(op.f("ix_perfiles_extraccion_tenant_id"), table_name="perfiles_extraccion")
    op.drop_index(op.f("ix_perfiles_extraccion_formato"), table_name="perfiles_extraccion")
    op.drop_index(op.f("ix_perfiles_extraccion_ruc"), table_name="perfiles_extraccion")
    op.drop_table("perfiles_extraccion")

    op.drop_index(op.f("ix_documentos_formato_origen"), table_name="documentos")
    op.drop_column("documentos", "formato_origen")
