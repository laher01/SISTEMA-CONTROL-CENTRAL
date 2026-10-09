"""Relaciones muchos-a-muchos entre Gerentes y Responsables y origen de pedidos.

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None



def _restriccion_única(tabla: str, columnas: set[str]) -> str:
    for restriccion in sa.inspect(op.get_bind()).get_unique_constraints(tabla):
        if set(restriccion["column_names"]) == columnas and restriccion.get("name"):
            return str(restriccion["name"])
    raise RuntimeError(f"Restricción única esperada no encontrada en {tabla}")


def upgrade() -> None:
    op.create_table(
        "gerentes_responsables",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("gerente_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("responsable_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "gerente_id",
            "responsable_id",
            name="uq_gerentes_responsables_tenant_id_gerente_id_responsable_id",
        ),
    )
    for column in ("tenant_id", "gerente_id", "responsable_id"):
        op.create_index(f"ix_gerentes_responsables_{column}", "gerentes_responsables", [column])
    op.add_column(
        "pedidos_gerencia",
        sa.Column("gerente_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=True),
    )
    op.create_index("ix_pedidos_gerencia_gerente_id", "pedidos_gerencia", ["gerente_id"])
    # Los pedidos históricos conservan NULL hasta completar la atribución
    # individual y auditada; no se adjudican al Gerente equivocado.
    with op.batch_alter_table("pedidos_gerencia") as batch:
        batch.drop_constraint(
            _restriccion_única(
                "pedidos_gerencia",
                {"tenant_id", "cliente_id", "periodo_mes", "moneda"},
            ),
            type_="unique",
        )
        batch.create_unique_constraint(
            "uq_pedidos_gerencia_tenant_id_gerente_id_cliente_id_periodo_mes_moneda",
            ["tenant_id", "gerente_id", "cliente_id", "periodo_mes", "moneda"],
        )


def downgrade() -> None:
    # Debe revisarse antes de revertir si dos Gerentes tienen pedidos
    # del mismo Cliente, mes y moneda.
    with op.batch_alter_table("pedidos_gerencia") as batch:
        batch.drop_constraint(
            "uq_pedidos_gerencia_tenant_id_gerente_id_cliente_id_periodo_mes_moneda",
            type_="unique",
        )
        batch.create_unique_constraint(
            "uq_pedidos_gerencia_tenant_id_cliente_id_periodo_mes_moneda",
            ["tenant_id", "cliente_id", "periodo_mes", "moneda"],
        )
    op.drop_index("ix_pedidos_gerencia_gerente_id", table_name="pedidos_gerencia")
    op.drop_column("pedidos_gerencia", "gerente_id")
    for column in ("tenant_id", "gerente_id", "responsable_id"):
        op.drop_index(f"ix_gerentes_responsables_{column}", table_name="gerentes_responsables")
    op.drop_table("gerentes_responsables")
