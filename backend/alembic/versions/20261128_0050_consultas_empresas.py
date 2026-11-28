"""Configuración de APIPERU por tenant."""

import sqlalchemy as sa

from alembic import op

revision: str = "0050"
down_revision: str = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracion_consultas_empresa",
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("token_cifrado", sa.Text(), nullable=True),
        sa.Column("endpoints", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("configuracion_consultas_empresa")
