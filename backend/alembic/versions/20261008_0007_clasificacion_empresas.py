"""clasificacion de empresas proveedor cliente

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column(
            "tipo_relacion",
            sa.String(length=20),
            server_default="SIN_CLASIFICAR",
            nullable=False,
        ),
    )
    op.add_column(
        "empresas",
        sa.Column("clasificacion_proveedor", sa.String(length=1), nullable=True),
    )
    op.create_index(
        op.f("ix_empresas_tipo_relacion"),
        "empresas",
        ["tipo_relacion"],
        unique=False,
    )
    op.create_index(
        op.f("ix_empresas_clasificacion_proveedor"),
        "empresas",
        ["clasificacion_proveedor"],
        unique=False,
    )

    op.execute(
        """
        UPDATE empresas e
        SET tipo_relacion = CASE
            WHEN EXISTS (
                SELECT 1 FROM expedientes x
                WHERE x.emisor_id = e.id AND x.deleted_at IS NULL
            )
            AND EXISTS (
                SELECT 1 FROM expedientes x
                WHERE x.receptor_id = e.id AND x.deleted_at IS NULL
            ) THEN 'AMBOS'
            WHEN EXISTS (
                SELECT 1 FROM expedientes x
                WHERE x.emisor_id = e.id AND x.deleted_at IS NULL
            ) THEN 'PROVEEDOR'
            WHEN EXISTS (
                SELECT 1 FROM expedientes x
                WHERE x.receptor_id = e.id AND x.deleted_at IS NULL
            ) THEN 'CLIENTE'
            ELSE 'SIN_CLASIFICAR'
        END
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_empresas_clasificacion_proveedor"), table_name="empresas")
    op.drop_index(op.f("ix_empresas_tipo_relacion"), table_name="empresas")
    op.drop_column("empresas", "clasificacion_proveedor")
    op.drop_column("empresas", "tipo_relacion")
