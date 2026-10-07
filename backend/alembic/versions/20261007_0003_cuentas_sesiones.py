"""cuentas y sesiones de acceso

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cuentas_acceso",
        sa.Column("login", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=500), nullable=False),
        sa.Column("miembro_id", sa.Uuid(), nullable=True),
        sa.Column("gestor_id", sa.Uuid(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("cambio_clave_obligatorio", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("ultimo_acceso", sa.DateTime(timezone=True), nullable=True),
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
            ["gestor_id"], ["gestores.id"], name=op.f("fk_cuentas_acceso_gestor_id_gestores")
        ),
        sa.ForeignKeyConstraint(
            ["miembro_id"], ["miembros.id"], name=op.f("fk_cuentas_acceso_miembro_id_miembros")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_cuentas_acceso_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cuentas_acceso")),
        sa.UniqueConstraint("tenant_id", "login", name=op.f("uq_cuentas_acceso_tenant_id_login")),
    )
    op.create_index(
        op.f("ix_cuentas_acceso_gestor_id"), "cuentas_acceso", ["gestor_id"], unique=False
    )
    op.create_index(
        op.f("ix_cuentas_acceso_miembro_id"), "cuentas_acceso", ["miembro_id"], unique=False
    )
    op.create_index(
        op.f("ix_cuentas_acceso_tenant_id"), "cuentas_acceso", ["tenant_id"], unique=False
    )

    op.create_table(
        "sesiones_acceso",
        sa.Column("cuenta_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("rol_activo", sa.String(length=20), nullable=False),
        sa.Column("expira_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ultima_actividad",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revocada_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cuenta_id"],
            ["cuentas_acceso.id"],
            name=op.f("fk_sesiones_acceso_cuenta_id_cuentas_acceso"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_sesiones_acceso_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sesiones_acceso")),
    )
    op.create_index(
        op.f("ix_sesiones_acceso_cuenta_id"), "sesiones_acceso", ["cuenta_id"], unique=False
    )
    op.create_index(
        op.f("ix_sesiones_acceso_rol_activo"), "sesiones_acceso", ["rol_activo"], unique=False
    )
    op.create_index(
        op.f("ix_sesiones_acceso_token_hash"), "sesiones_acceso", ["token_hash"], unique=True
    )
    op.create_index(
        op.f("ix_sesiones_acceso_tenant_id"), "sesiones_acceso", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sesiones_acceso_tenant_id"), table_name="sesiones_acceso")
    op.drop_index(op.f("ix_sesiones_acceso_token_hash"), table_name="sesiones_acceso")
    op.drop_index(op.f("ix_sesiones_acceso_rol_activo"), table_name="sesiones_acceso")
    op.drop_index(op.f("ix_sesiones_acceso_cuenta_id"), table_name="sesiones_acceso")
    op.drop_table("sesiones_acceso")

    op.drop_index(op.f("ix_cuentas_acceso_tenant_id"), table_name="cuentas_acceso")
    op.drop_index(op.f("ix_cuentas_acceso_miembro_id"), table_name="cuentas_acceso")
    op.drop_index(op.f("ix_cuentas_acceso_gestor_id"), table_name="cuentas_acceso")
    op.drop_table("cuentas_acceso")
