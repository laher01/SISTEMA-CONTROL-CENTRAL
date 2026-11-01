"""Pagos documentales y asignaciones a expedientes.

Revision ID: 0045
Revises: 0044
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pagos_documentales",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("documento_id", sa.Uuid(), sa.ForeignKey("documentos.id"), nullable=False),
        sa.Column("huella_operacion", sa.String(64)),
        sa.Column("banco", sa.String(80)),
        sa.Column("tipo_operacion", sa.String(30), nullable=False, server_default="OTRO"),
        sa.Column("fecha_hora", sa.DateTime(timezone=True)),
        sa.Column("numero_operacion", sa.String(40)),
        sa.Column("beneficiario", sa.String(300)),
        sa.Column("cuenta_beneficiario", sa.String(80)),
        sa.Column("agencia", sa.String(80)),
        sa.Column("moneda", sa.String(3)),
        sa.Column("importe", sa.Numeric(14, 2)),
        sa.Column("remitente", sa.String(300)),
        sa.Column("cuenta_remitente", sa.String(80)),
        sa.Column("estado", sa.String(30), nullable=False, server_default="PENDIENTE_REVISION"),
        sa.Column("conciliado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("tenant_id", "documento_id", name="uq_pago_documental_documento"),
        sa.UniqueConstraint("tenant_id", "huella_operacion", name="uq_pago_documental_operacion"),
    )
    op.create_index("ix_pagos_documentales_tenant_id", "pagos_documentales", ["tenant_id"])
    op.create_index("ix_pagos_documentales_documento_id", "pagos_documentales", ["documento_id"])
    op.create_index("ix_pagos_documentales_estado", "pagos_documentales", ["estado"])
    op.create_index(
        "ix_pagos_documentales_tenant_estado", "pagos_documentales", ["tenant_id", "estado"]
    )

    op.create_table(
        "asignaciones_pagos_documentales",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("pago_id", sa.Uuid(), sa.ForeignKey("pagos_documentales.id"), nullable=False),
        sa.Column("expediente_id", sa.Uuid(), sa.ForeignKey("expedientes.id"), nullable=False),
        sa.Column("importe_asignado", sa.Numeric(14, 2), nullable=False),
        sa.Column("evidencia", sa.String(500), nullable=False),
        sa.Column("confianza", sa.Numeric(5, 4)),
        sa.Column("referencia_confirmada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint(
            "tenant_id", "pago_id", "expediente_id", name="uq_asignacion_pago_expediente"
        ),
    )
    op.create_index(
        "ix_asignaciones_pagos_documentales_tenant_id",
        "asignaciones_pagos_documentales",
        ["tenant_id"],
    )
    op.create_index(
        "ix_asignaciones_pagos_documentales_pago_id",
        "asignaciones_pagos_documentales",
        ["pago_id"],
    )
    op.create_index(
        "ix_asignaciones_pagos_documentales_expediente_id",
        "asignaciones_pagos_documentales",
        ["expediente_id"],
    )


def downgrade() -> None:
    op.drop_table("asignaciones_pagos_documentales")
    op.drop_table("pagos_documentales")
