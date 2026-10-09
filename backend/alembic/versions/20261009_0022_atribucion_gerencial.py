"""Atribución explícita del origen de facturas y obligaciones por Gerente.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None



def _restriccion_única(tabla: str, columnas: set[str]) -> str:
    for restriccion in sa.inspect(op.get_bind()).get_unique_constraints(tabla):
        if set(restriccion["column_names"]) == columnas and restriccion.get("name"):
            return str(restriccion["name"])
    raise RuntimeError(f"Restricción única esperada no encontrada en {tabla}")


def upgrade() -> None:
    # NULL conserva como no asignadas las facturas y liquidaciones anteriores.
    op.add_column(
        "expedientes",
        sa.Column("pedido_gerencia_id", sa.Uuid(), sa.ForeignKey("pedidos_gerencia.id")),
    )
    op.add_column(
        "expedientes", sa.Column("gerente_id", sa.Uuid(), sa.ForeignKey("miembros.id"))
    )
    op.create_index("ix_expedientes_pedido_gerencia_id", "expedientes", ["pedido_gerencia_id"])
    op.create_index("ix_expedientes_gerente_id", "expedientes", ["gerente_id"])
    op.add_column(
        "pagos_responsables_erp",
        sa.Column("gerente_id", sa.Uuid(), sa.ForeignKey("miembros.id")),
    )
    op.create_index(
        "ix_pagos_responsables_erp_gerente_id", "pagos_responsables_erp", ["gerente_id"]
    )
    with op.batch_alter_table("pagos_responsables_erp") as batch:
        batch.drop_constraint(
            _restriccion_única("pagos_responsables_erp", {"tenant_id","responsable_id","periodo_desde","periodo_hasta","moneda"}),
            type_="unique",
        )
        batch.create_unique_constraint(
            "uq_pagos_responsables_erp_tenant_id_gerente_id_responsable_id_periodo_desde_periodo_hasta_moneda",
            ["tenant_id", "gerente_id", "responsable_id", "periodo_desde", "periodo_hasta", "moneda"],
        )


def downgrade() -> None:
    # No revertir si existen pagos de diferentes Gerentes en un mismo período.
    with op.batch_alter_table("pagos_responsables_erp") as batch:
        batch.drop_constraint(
            "uq_pagos_responsables_erp_tenant_id_gerente_id_responsable_id_periodo_desde_periodo_hasta_moneda",
            type_="unique",
        )
        batch.create_unique_constraint(
            "uq_pagos_responsables_erp_tenant_id_responsable_id_periodo_desde_periodo_hasta_moneda",
            ["tenant_id", "responsable_id", "periodo_desde", "periodo_hasta", "moneda"],
        )
    op.drop_index(
        "ix_pagos_responsables_erp_gerente_id", table_name="pagos_responsables_erp"
    )
    op.drop_column("pagos_responsables_erp", "gerente_id")
    op.drop_index("ix_expedientes_gerente_id", table_name="expedientes")
    op.drop_index("ix_expedientes_pedido_gerencia_id", table_name="expedientes")
    op.drop_column("expedientes", "gerente_id")
    op.drop_column("expedientes", "pedido_gerencia_id")
