"""pedidos de gerencia y distribucion

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pedidos_gerencia",
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("creado_por_cuenta_id", sa.Uuid(), nullable=True),
        sa.Column("periodo_mes", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("monto_solicitado", sa.Numeric(14, 2), nullable=False),
        sa.Column("modalidad", sa.String(length=30), nullable=False),
        sa.Column("modo_distribucion", sa.String(length=30), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("observacion", sa.String(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cliente_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["creado_por_cuenta_id"], ["cuentas_acceso.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "cliente_id", "periodo_mes", "moneda"),
    )
    op.create_index(op.f("ix_pedidos_gerencia_cliente_id"), "pedidos_gerencia", ["cliente_id"])
    op.create_index(op.f("ix_pedidos_gerencia_periodo_mes"), "pedidos_gerencia", ["periodo_mes"])
    op.create_index(op.f("ix_pedidos_gerencia_moneda"), "pedidos_gerencia", ["moneda"])
    op.create_index(op.f("ix_pedidos_gerencia_modalidad"), "pedidos_gerencia", ["modalidad"])
    op.create_index(
        op.f("ix_pedidos_gerencia_modo_distribucion"),
        "pedidos_gerencia",
        ["modo_distribucion"],
    )
    op.create_index(op.f("ix_pedidos_gerencia_estado"), "pedidos_gerencia", ["estado"])
    op.create_index(
        op.f("ix_pedidos_gerencia_creado_por_cuenta_id"),
        "pedidos_gerencia",
        ["creado_por_cuenta_id"],
    )
    op.create_index(
        op.f("ix_pedidos_gerencia_tenant_id"),
        "pedidos_gerencia",
        ["tenant_id"],
    )

    op.create_table(
        "asignaciones_pedido_gerencia",
        sa.Column("pedido_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("gestor_id", sa.Uuid(), nullable=True),
        sa.Column("proveedor_id", sa.Uuid(), nullable=True),
        sa.Column("monto_asignado", sa.Numeric(14, 2), nullable=False),
        sa.Column("creado_por_cuenta_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_gerencia.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["miembros.id"]),
        sa.ForeignKeyConstraint(["gestor_id"], ["gestores.id"]),
        sa.ForeignKeyConstraint(["proveedor_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["creado_por_cuenta_id"], ["cuentas_acceso.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asignaciones_pedido_gerencia_pedido_id"),
        "asignaciones_pedido_gerencia",
        ["pedido_id"],
    )
    op.create_index(
        op.f("ix_asignaciones_pedido_gerencia_usuario_id"),
        "asignaciones_pedido_gerencia",
        ["usuario_id"],
    )
    op.create_index(
        op.f("ix_asignaciones_pedido_gerencia_gestor_id"),
        "asignaciones_pedido_gerencia",
        ["gestor_id"],
    )
    op.create_index(
        op.f("ix_asignaciones_pedido_gerencia_proveedor_id"),
        "asignaciones_pedido_gerencia",
        ["proveedor_id"],
    )
    op.create_index(
        op.f("ix_asignaciones_pedido_gerencia_creado_por_cuenta_id"),
        "asignaciones_pedido_gerencia",
        ["creado_por_cuenta_id"],
    )
    op.create_index(
        op.f("ix_asignaciones_pedido_gerencia_tenant_id"),
        "asignaciones_pedido_gerencia",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_asignaciones_pedido_gerencia_tenant_id"),
        table_name="asignaciones_pedido_gerencia",
    )
    op.drop_index(
        op.f("ix_asignaciones_pedido_gerencia_creado_por_cuenta_id"),
        table_name="asignaciones_pedido_gerencia",
    )
    op.drop_index(
        op.f("ix_asignaciones_pedido_gerencia_proveedor_id"),
        table_name="asignaciones_pedido_gerencia",
    )
    op.drop_index(
        op.f("ix_asignaciones_pedido_gerencia_gestor_id"),
        table_name="asignaciones_pedido_gerencia",
    )
    op.drop_index(
        op.f("ix_asignaciones_pedido_gerencia_usuario_id"),
        table_name="asignaciones_pedido_gerencia",
    )
    op.drop_index(
        op.f("ix_asignaciones_pedido_gerencia_pedido_id"),
        table_name="asignaciones_pedido_gerencia",
    )
    op.drop_table("asignaciones_pedido_gerencia")

    op.drop_index(op.f("ix_pedidos_gerencia_tenant_id"), table_name="pedidos_gerencia")
    op.drop_index(
        op.f("ix_pedidos_gerencia_creado_por_cuenta_id"),
        table_name="pedidos_gerencia",
    )
    op.drop_index(op.f("ix_pedidos_gerencia_estado"), table_name="pedidos_gerencia")
    op.drop_index(
        op.f("ix_pedidos_gerencia_modo_distribucion"),
        table_name="pedidos_gerencia",
    )
    op.drop_index(op.f("ix_pedidos_gerencia_modalidad"), table_name="pedidos_gerencia")
    op.drop_index(op.f("ix_pedidos_gerencia_moneda"), table_name="pedidos_gerencia")
    op.drop_index(op.f("ix_pedidos_gerencia_periodo_mes"), table_name="pedidos_gerencia")
    op.drop_index(op.f("ix_pedidos_gerencia_cliente_id"), table_name="pedidos_gerencia")
    op.drop_table("pedidos_gerencia")
