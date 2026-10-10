"""Tablas de recepcion documental por correo.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columnas_base() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    ]


def upgrade() -> None:
    op.create_table(
        "correo_buzones",
        *_columnas_base(),
        sa.Column("direccion", sa.String(length=320), nullable=False),
        sa.Column("proveedor", sa.String(length=20), nullable=False),
        sa.Column("responsable_id", sa.Uuid(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("cursor", sa.String(length=500), nullable=True),
        sa.Column("ultimo_error", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["responsable_id"], ["miembros.id"]),
        sa.UniqueConstraint("tenant_id", "direccion"),
    )
    op.create_index(op.f("ix_correo_buzones_tenant_id"), "correo_buzones", ["tenant_id"])
    op.create_index(op.f("ix_correo_buzones_responsable_id"), "correo_buzones", ["responsable_id"])
    op.create_table(
        "correo_remitentes",
        *_columnas_base(),
        sa.Column("direccion", sa.String(length=320), nullable=False),
        sa.Column("gestor_id", sa.Uuid(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["gestor_id"], ["gestores.id"]),
        sa.UniqueConstraint("tenant_id", "gestor_id", "direccion"),
    )
    op.create_index(op.f("ix_correo_remitentes_tenant_id"), "correo_remitentes", ["tenant_id"])
    op.create_index(op.f("ix_correo_remitentes_gestor_id"), "correo_remitentes", ["gestor_id"])
    op.create_table(
        "correo_mensajes",
        *_columnas_base(),
        sa.Column("buzon_id", sa.Uuid(), nullable=False),
        sa.Column("identificador_externo", sa.String(length=500), nullable=False),
        sa.Column("remitente", sa.String(length=320), nullable=False),
        sa.Column("gestor_id", sa.Uuid(), nullable=True),
        sa.Column("estado", sa.String(length=32), server_default="PENDIENTE", nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["buzon_id"], ["correo_buzones.id"]),
        sa.ForeignKeyConstraint(["gestor_id"], ["gestores.id"]),
        sa.UniqueConstraint("buzon_id", "identificador_externo"),
    )
    op.create_index(op.f("ix_correo_mensajes_tenant_id"), "correo_mensajes", ["tenant_id"])
    op.create_index(op.f("ix_correo_mensajes_buzon_id"), "correo_mensajes", ["buzon_id"])
    op.create_index(op.f("ix_correo_mensajes_gestor_id"), "correo_mensajes", ["gestor_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_correo_mensajes_gestor_id"), table_name="correo_mensajes")
    op.drop_index(op.f("ix_correo_mensajes_buzon_id"), table_name="correo_mensajes")
    op.drop_index(op.f("ix_correo_mensajes_tenant_id"), table_name="correo_mensajes")
    op.drop_table("correo_mensajes")
    op.drop_index(op.f("ix_correo_remitentes_gestor_id"), table_name="correo_remitentes")
    op.drop_index(op.f("ix_correo_remitentes_tenant_id"), table_name="correo_remitentes")
    op.drop_table("correo_remitentes")
    op.drop_index(op.f("ix_correo_buzones_responsable_id"), table_name="correo_buzones")
    op.drop_index(op.f("ix_correo_buzones_tenant_id"), table_name="correo_buzones")
    op.drop_table("correo_buzones")
