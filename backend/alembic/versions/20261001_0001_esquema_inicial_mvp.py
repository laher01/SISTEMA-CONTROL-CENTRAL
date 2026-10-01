"""esquema inicial mvp

Revision ID: 0001
Revises:
Create Date: 2026-10-01 06:24:46.477836
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    op.create_table(
        "tenants",
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenants")),
        sa.UniqueConstraint("nombre", name=op.f("uq_tenants_nombre")),
    )
    op.create_table(
        "auditoria",
        sa.Column("accion", sa.String(length=60), nullable=False),
        sa.Column("entidad", sa.String(length=40), nullable=False),
        sa.Column("entidad_id", sa.Uuid(), nullable=False),
        sa.Column(
            "datos",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
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
            ["tenant_id"], ["tenants.id"], name=op.f("fk_auditoria_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auditoria")),
    )
    op.create_index(op.f("ix_auditoria_entidad_id"), "auditoria", ["entidad_id"], unique=False)
    op.create_index(op.f("ix_auditoria_tenant_id"), "auditoria", ["tenant_id"], unique=False)
    op.create_table(
        "empresas",
        sa.Column("ruc", sa.String(length=11), nullable=False),
        sa.Column("razon_social", sa.String(length=300), nullable=False),
        sa.Column("autorizada", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("agente_retencion", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_empresas_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_empresas")),
        sa.UniqueConstraint("tenant_id", "ruc", name=op.f("uq_empresas_tenant_id_ruc")),
    )
    op.create_index(op.f("ix_empresas_tenant_id"), "empresas", ["tenant_id"], unique=False)
    op.create_table(
        "gestores",
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_gestores_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gestores")),
        sa.UniqueConstraint("tenant_id", "codigo", name=op.f("uq_gestores_tenant_id_codigo")),
    )
    op.create_index(op.f("ix_gestores_tenant_id"), "gestores", ["tenant_id"], unique=False)
    op.create_table(
        "expedientes",
        sa.Column("receptor_id", sa.Uuid(), nullable=False),
        sa.Column("emisor_id", sa.Uuid(), nullable=False),
        sa.Column("tipo_comprobante", sa.String(length=4), nullable=False),
        sa.Column("serie", sa.String(length=4), nullable=False),
        sa.Column("correlativo", sa.String(length=8), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("importe_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("requiere_guia", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("gestor_id", sa.Uuid(), nullable=True),
        sa.Column("estado", sa.String(length=10), nullable=False),
        sa.Column("pendiente_aprobacion", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["emisor_id"], ["empresas.id"], name=op.f("fk_expedientes_emisor_id_empresas")
        ),
        sa.ForeignKeyConstraint(
            ["gestor_id"], ["gestores.id"], name=op.f("fk_expedientes_gestor_id_gestores")
        ),
        sa.ForeignKeyConstraint(
            ["receptor_id"], ["empresas.id"], name=op.f("fk_expedientes_receptor_id_empresas")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_expedientes_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expedientes")),
        sa.UniqueConstraint(
            "tenant_id",
            "receptor_id",
            "tipo_comprobante",
            "serie",
            "correlativo",
            "emisor_id",
            name=op.f(
                "uq_expedientes_tenant_id_receptor_id_tipo_comprobante_serie_correlativo_emisor_id"
            ),
        ),
    )
    op.create_index(op.f("ix_expedientes_emisor_id"), "expedientes", ["emisor_id"], unique=False)
    op.create_index(op.f("ix_expedientes_estado"), "expedientes", ["estado"], unique=False)
    op.create_index(op.f("ix_expedientes_gestor_id"), "expedientes", ["gestor_id"], unique=False)
    op.create_index(
        op.f("ix_expedientes_receptor_id"), "expedientes", ["receptor_id"], unique=False
    )
    op.create_index(op.f("ix_expedientes_tenant_id"), "expedientes", ["tenant_id"], unique=False)
    op.create_table(
        "alertas",
        sa.Column("expediente_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("mensaje", sa.String(length=500), nullable=False),
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
            ["expediente_id"], ["expedientes.id"], name=op.f("fk_alertas_expediente_id_expedientes")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_alertas_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alertas")),
        sa.UniqueConstraint("expediente_id", "tipo", name=op.f("uq_alertas_expediente_id_tipo")),
    )
    op.create_index(op.f("ix_alertas_expediente_id"), "alertas", ["expediente_id"], unique=False)
    op.create_index(op.f("ix_alertas_resuelta"), "alertas", ["resuelta"], unique=False)
    op.create_index(op.f("ix_alertas_tenant_id"), "alertas", ["tenant_id"], unique=False)
    op.create_table(
        "documentos",
        sa.Column("expediente_id", sa.Uuid(), nullable=True),
        sa.Column("tipo_documento", sa.String(length=6), nullable=True),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("nombre_original", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("tamano_bytes", sa.BigInteger(), nullable=False),
        sa.Column("ruta_storage", sa.String(length=500), nullable=False),
        sa.Column(
            "datos_extraidos",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("gestor_id", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["expediente_id"],
            ["expedientes.id"],
            name=op.f("fk_documentos_expediente_id_expedientes"),
        ),
        sa.ForeignKeyConstraint(
            ["gestor_id"], ["gestores.id"], name=op.f("fk_documentos_gestor_id_gestores")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_documentos_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documentos")),
        sa.UniqueConstraint("tenant_id", "sha256", name=op.f("uq_documentos_tenant_id_sha256")),
    )
    op.create_index(op.f("ix_documentos_estado"), "documentos", ["estado"], unique=False)
    op.create_index(
        op.f("ix_documentos_expediente_id"), "documentos", ["expediente_id"], unique=False
    )
    op.create_index(op.f("ix_documentos_gestor_id"), "documentos", ["gestor_id"], unique=False)
    op.create_index(op.f("ix_documentos_tenant_id"), "documentos", ["tenant_id"], unique=False)


def downgrade() -> None:

    op.drop_index(op.f("ix_documentos_tenant_id"), table_name="documentos")
    op.drop_index(op.f("ix_documentos_gestor_id"), table_name="documentos")
    op.drop_index(op.f("ix_documentos_expediente_id"), table_name="documentos")
    op.drop_index(op.f("ix_documentos_estado"), table_name="documentos")
    op.drop_table("documentos")
    op.drop_index(op.f("ix_alertas_tenant_id"), table_name="alertas")
    op.drop_index(op.f("ix_alertas_resuelta"), table_name="alertas")
    op.drop_index(op.f("ix_alertas_expediente_id"), table_name="alertas")
    op.drop_table("alertas")
    op.drop_index(op.f("ix_expedientes_tenant_id"), table_name="expedientes")
    op.drop_index(op.f("ix_expedientes_receptor_id"), table_name="expedientes")
    op.drop_index(op.f("ix_expedientes_gestor_id"), table_name="expedientes")
    op.drop_index(op.f("ix_expedientes_estado"), table_name="expedientes")
    op.drop_index(op.f("ix_expedientes_emisor_id"), table_name="expedientes")
    op.drop_table("expedientes")
    op.drop_index(op.f("ix_gestores_tenant_id"), table_name="gestores")
    op.drop_table("gestores")
    op.drop_index(op.f("ix_empresas_tenant_id"), table_name="empresas")
    op.drop_table("empresas")
    op.drop_index(op.f("ix_auditoria_tenant_id"), table_name="auditoria")
    op.drop_index(op.f("ix_auditoria_entidad_id"), table_name="auditoria")
    op.drop_table("auditoria")
    op.drop_table("tenants")
