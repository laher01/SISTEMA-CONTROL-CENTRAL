"""Movimientos parciales de pagos de Responsables.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pagos_responsables_erp",
        sa.Column("fecha_reprogramada", sa.Date(), nullable=True),
    )
    op.create_table(
        "movimientos_pagos_responsables",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "pago_id",
            sa.Uuid(),
            sa.ForeignKey("pagos_responsables_erp.id"),
            nullable=False,
        ),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("referencia", sa.String(160), nullable=False),
        sa.Column("comprobante_archivo", sa.String(255), nullable=False),
        sa.UniqueConstraint("pago_id", "referencia"),
        sa.Column(
            "creado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_movimientos_pagos_responsables_tenant_id",
        "movimientos_pagos_responsables",
        ["tenant_id"],
    )
    op.create_index(
        "ix_movimientos_pagos_responsables_pago_id",
        "movimientos_pagos_responsables",
        ["pago_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_movimientos_pagos_responsables_pago_id",
        table_name="movimientos_pagos_responsables",
    )
    op.drop_index(
        "ix_movimientos_pagos_responsables_tenant_id",
        table_name="movimientos_pagos_responsables",
    )
    op.drop_table("movimientos_pagos_responsables")
    op.drop_column("pagos_responsables_erp", "fecha_reprogramada")
