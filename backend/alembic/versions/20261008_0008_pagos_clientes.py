"""pagos clientes y porcentaje produccion usuario

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "miembros",
        sa.Column("porcentaje_produccion", sa.Numeric(7, 4), nullable=True),
    )
    op.execute(
        """
        UPDATE miembros m
        SET porcentaje_produccion = (
            SELECT p.porcentaje
            FROM planes_liquidacion p
            WHERE p.usuario_id = m.id
              AND p.activo = true
            ORDER BY p.vigencia_desde DESC
            LIMIT 1
        )
        WHERE m.rol = 'USUARIO'
        """
    )

    op.create_table(
        "abonos_cliente_erp",
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("creado_por_cuenta_id", sa.Uuid(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("descripcion", sa.String(length=500), nullable=True),
        sa.Column("referencia", sa.String(length=120), nullable=True),
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
    )
    op.create_index(
        op.f("ix_abonos_cliente_erp_cliente_id"),
        "abonos_cliente_erp",
        ["cliente_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_abonos_cliente_erp_creado_por_cuenta_id"),
        "abonos_cliente_erp",
        ["creado_por_cuenta_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_abonos_cliente_erp_fecha"),
        "abonos_cliente_erp",
        ["fecha"],
        unique=False,
    )
    op.create_index(
        op.f("ix_abonos_cliente_erp_moneda"),
        "abonos_cliente_erp",
        ["moneda"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_abonos_cliente_erp_moneda"), table_name="abonos_cliente_erp")
    op.drop_index(op.f("ix_abonos_cliente_erp_fecha"), table_name="abonos_cliente_erp")
    op.drop_index(
        op.f("ix_abonos_cliente_erp_creado_por_cuenta_id"),
        table_name="abonos_cliente_erp",
    )
    op.drop_index(
        op.f("ix_abonos_cliente_erp_cliente_id"),
        table_name="abonos_cliente_erp",
    )
    op.drop_table("abonos_cliente_erp")
    op.drop_column("miembros", "porcentaje_produccion")
