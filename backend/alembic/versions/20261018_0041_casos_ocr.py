"""Etapa 8: casos OCR y reglas versionadas.

Revision ID: 0041
Revises: 0040
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "casos_ocr",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("documento_id", sa.Uuid(), sa.ForeignKey("documentos.id"), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="PENDIENTE"),
        sa.Column("motivo", sa.String(500), nullable=False),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("regla_version", sa.String(80)),
        sa.Column("ultimo_resultado", sa.JSON().with_variant(postgresql.JSONB(), "postgresql")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "documento_id"),
    )
    op.create_index("ix_casos_ocr_tenant_id", "casos_ocr", ["tenant_id"])
    op.create_index("ix_casos_ocr_documento_id", "casos_ocr", ["documento_id"])
    op.create_table(
        "reglas_ocr",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "definicion",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("estado", sa.String(20), nullable=False, server_default="BORRADOR"),
        sa.Column("aprobada_por", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id")),
        sa.Column("aprobada_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", "nombre", "version"),
    )
    op.create_index("ix_reglas_ocr_tenant_id", "reglas_ocr", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_reglas_ocr_tenant_id", "reglas_ocr")
    op.drop_table("reglas_ocr")
    op.drop_index("ix_casos_ocr_documento_id", "casos_ocr")
    op.drop_index("ix_casos_ocr_tenant_id", "casos_ocr")
    op.drop_table("casos_ocr")
