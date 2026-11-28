"""Resultado de la validación CPE por expediente."""

import sqlalchemy as sa

from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column("recuperar_en_ingesta", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("expedientes", sa.Column("cpe_estado", sa.String(12), nullable=True))
    op.add_column("expedientes", sa.Column("cpe_identidad", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("empresas", "recuperar_en_ingesta")
    op.drop_column("expedientes", "cpe_identidad")
    op.drop_column("expedientes", "cpe_estado")
