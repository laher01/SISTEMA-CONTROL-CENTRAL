"""Ampliar correlativos fiscales sin modificar identificadores históricos.

Revision ID: 0040
Revises: 0039
"""
import sqlalchemy as sa

from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for tabla in ("expedientes", "referencias_gre"):
        op.alter_column(
            tabla, "correlativo", existing_type=sa.String(length=8),
            type_=sa.String(length=32), existing_nullable=False,
        )


    op.add_column(
        "expedientes", sa.Column("correlativo_original", sa.String(length=32), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("expedientes", "correlativo_original")
    conexion = op.get_bind()
    for tabla in ("expedientes", "referencias_gre"):
        excedentes = conexion.execute(
            sa.text(f"SELECT COUNT(*) FROM {tabla} WHERE length(correlativo) > 8")
        ).scalar_one()
        if excedentes:
            raise RuntimeError(
                f"No se puede reducir {tabla}.correlativo: hay valores de más de 8 caracteres"
            )
        op.alter_column(
            tabla, "correlativo", existing_type=sa.String(length=32),
            type_=sa.String(length=8), existing_nullable=False,
        )
