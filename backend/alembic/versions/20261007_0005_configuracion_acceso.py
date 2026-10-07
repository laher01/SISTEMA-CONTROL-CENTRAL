"""configuracion de acceso y rol superadmin

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cuentas_acceso", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column(
        "cuentas_acceso",
        sa.Column("email_verificado", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "cuentas_acceso",
        sa.Column("intentos_fallidos", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "cuentas_acceso",
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_cuentas_acceso_email"), "cuentas_acceso", ["email"], unique=False)
    op.create_unique_constraint(
        op.f("uq_cuentas_acceso_tenant_id_email"),
        "cuentas_acceso",
        ["tenant_id", "email"],
    )

    op.create_table(
        "configuracion_acceso",
        sa.Column("registro_publico", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("requiere_aprobacion", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("solo_correos_autorizados", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "requiere_email_verificado",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "proveedor_email_configurado",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("acceso_cloudflare_activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("duracion_sesion_horas", sa.Integer(), server_default="12", nullable=False),
        sa.Column("intentos_fallidos_max", sa.Integer(), server_default="5", nullable=False),
        sa.Column("bloqueo_minutos", sa.Integer(), server_default="15", nullable=False),
        sa.Column("clave_min_longitud", sa.Integer(), server_default="10", nullable=False),
        sa.Column("clave_requiere_letra", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("clave_requiere_numero", sa.Boolean(), server_default="true", nullable=False),
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
            name=op.f("fk_configuracion_acceso_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_configuracion_acceso")),
        sa.UniqueConstraint("tenant_id", name=op.f("uq_configuracion_acceso_tenant_id")),
    )
    op.create_index(
        op.f("ix_configuracion_acceso_tenant_id"),
        "configuracion_acceso",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "correos_autorizados",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("rol_sugerido", sa.String(length=20), nullable=True),
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
            name=op.f("fk_correos_autorizados_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_correos_autorizados")),
        sa.UniqueConstraint(
            "tenant_id",
            "email",
            name=op.f("uq_correos_autorizados_tenant_id_email"),
        ),
    )
    op.create_index(
        op.f("ix_correos_autorizados_email"),
        "correos_autorizados",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correos_autorizados_tenant_id"),
        "correos_autorizados",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "solicitudes_acceso",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("codigo_solicitado", sa.String(length=50), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("rol_asignado", sa.String(length=20), nullable=True),
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
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_solicitudes_acceso_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_solicitudes_acceso")),
        sa.UniqueConstraint(
            "tenant_id",
            "email",
            name=op.f("uq_solicitudes_acceso_tenant_id_email"),
        ),
    )
    op.create_index(
        op.f("ix_solicitudes_acceso_email"),
        "solicitudes_acceso",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_solicitudes_acceso_estado"),
        "solicitudes_acceso",
        ["estado"],
        unique=False,
    )
    op.create_index(
        op.f("ix_solicitudes_acceso_tenant_id"),
        "solicitudes_acceso",
        ["tenant_id"],
        unique=False,
    )

    # Promueve únicamente la cuenta administrativa principal existente.
    # El resto de administradores conserva su rol operativo.
    op.execute(
        "UPDATE miembros SET rol = 'SUPERADMIN' "
        "WHERE rol = 'ADMINISTRADOR' AND codigo = 'ADMIN01'"
    )


def downgrade() -> None:
    op.execute("UPDATE miembros SET rol = 'ADMINISTRADOR' WHERE rol = 'SUPERADMIN'")
    for table in ("solicitudes_acceso", "correos_autorizados", "configuracion_acceso"):
        op.drop_table(table)
    op.drop_constraint(
        op.f("uq_cuentas_acceso_tenant_id_email"),
        "cuentas_acceso",
        type_="unique",
    )
    op.drop_index(op.f("ix_cuentas_acceso_email"), table_name="cuentas_acceso")
    op.drop_column("cuentas_acceso", "bloqueado_hasta")
    op.drop_column("cuentas_acceso", "intentos_fallidos")
    op.drop_column("cuentas_acceso", "email_verificado")
    op.drop_column("cuentas_acceso", "email")
