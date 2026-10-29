"""añade etapas, revisión y versionado documental pesquero

Revision ID: 0049
Revises: 0048
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0049"
down_revision: str | None = "0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pesca_documentos", sa.Column("etapa", sa.String(length=30), server_default="GENERAL", nullable=False))
    op.add_column("pesca_documentos", sa.Column("estado_revision", sa.String(length=20), server_default="PENDIENTE", nullable=False))
    op.add_column("pesca_documentos", sa.Column("observacion_revision", sa.Text(), nullable=True))
    op.add_column("pesca_documentos", sa.Column("revisado_por", sa.String(length=200), nullable=True))
    op.add_column("pesca_documentos", sa.Column("revisado_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pesca_documentos", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("pesca_documentos", sa.Column("vigente", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("pesca_documentos", sa.Column("documento_anterior_id", sa.Uuid(), nullable=True))
    op.create_check_constraint(
        "ck_pesca_documentos_estado_revision_valido", "pesca_documentos",
        "estado_revision IN ('PENDIENTE', 'VERIFICADO', 'OBSERVADO')",
    )
    op.create_check_constraint(
        "ck_pesca_documentos_version_positiva", "pesca_documentos", "version >= 1",
    )
    op.create_foreign_key(
        "fk_pesca_documentos_anterior", "pesca_documentos", "pesca_documentos",
        ["documento_anterior_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_pesca_documentos_etapa", "pesca_documentos", ["etapa"])
    op.create_index("ix_pesca_documentos_estado_revision", "pesca_documentos", ["estado_revision"])
    op.create_index("ix_pesca_documentos_vigente", "pesca_documentos", ["vigente"])


def downgrade() -> None:
    op.drop_index("ix_pesca_documentos_vigente", table_name="pesca_documentos")
    op.drop_index("ix_pesca_documentos_estado_revision", table_name="pesca_documentos")
    op.drop_index("ix_pesca_documentos_etapa", table_name="pesca_documentos")
    op.drop_constraint("fk_pesca_documentos_anterior", "pesca_documentos", type_="foreignkey")
    op.drop_constraint("ck_pesca_documentos_version_positiva", "pesca_documentos", type_="check")
    op.drop_constraint("ck_pesca_documentos_estado_revision_valido", "pesca_documentos", type_="check")
    op.drop_column("pesca_documentos", "documento_anterior_id")
    op.drop_column("pesca_documentos", "vigente")
    op.drop_column("pesca_documentos", "version")
    op.drop_column("pesca_documentos", "revisado_at")
    op.drop_column("pesca_documentos", "revisado_por")
    op.drop_column("pesca_documentos", "observacion_revision")
    op.drop_column("pesca_documentos", "estado_revision")
    op.drop_column("pesca_documentos", "etapa")
