"""jerarquia de miembros usuarios y gestores

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "miembros",
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
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
            ["tenant_id"], ["tenants.id"], name=op.f("fk_miembros_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_miembros")),
        sa.UniqueConstraint("tenant_id", "codigo", name=op.f("uq_miembros_tenant_id_codigo")),
    )
    op.create_index(op.f("ix_miembros_rol"), "miembros", ["rol"], unique=False)
    op.create_index(op.f("ix_miembros_tenant_id"), "miembros", ["tenant_id"], unique=False)

    op.add_column("gestores", sa.Column("usuario_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_gestores_usuario_id_miembros"),
        "gestores",
        "miembros",
        ["usuario_id"],
        ["id"],
    )
    op.create_index(op.f("ix_gestores_usuario_id"), "gestores", ["usuario_id"], unique=False)

    op.add_column("expedientes", sa.Column("usuario_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_expedientes_usuario_id_miembros"),
        "expedientes",
        "miembros",
        ["usuario_id"],
        ["id"],
    )
    op.create_index(op.f("ix_expedientes_usuario_id"), "expedientes", ["usuario_id"], unique=False)

    op.add_column("documentos", sa.Column("usuario_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_documentos_usuario_id_miembros"),
        "documentos",
        "miembros",
        ["usuario_id"],
        ["id"],
    )
    op.create_index(op.f("ix_documentos_usuario_id"), "documentos", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documentos_usuario_id"), table_name="documentos")
    op.drop_constraint(op.f("fk_documentos_usuario_id_miembros"), "documentos", type_="foreignkey")
    op.drop_column("documentos", "usuario_id")

    op.drop_index(op.f("ix_expedientes_usuario_id"), table_name="expedientes")
    op.drop_constraint(op.f("fk_expedientes_usuario_id_miembros"), "expedientes", type_="foreignkey")
    op.drop_column("expedientes", "usuario_id")

    op.drop_index(op.f("ix_gestores_usuario_id"), table_name="gestores")
    op.drop_constraint(op.f("fk_gestores_usuario_id_miembros"), "gestores", type_="foreignkey")
    op.drop_column("gestores", "usuario_id")

    op.drop_index(op.f("ix_miembros_tenant_id"), table_name="miembros")
    op.drop_index(op.f("ix_miembros_rol"), table_name="miembros")
    op.drop_table("miembros")
