"""Permite reingresar documentos retirados sin borrar su historial.

Revision ID: 0043
Revises: 0042
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Los registros retirados conservan auditoría e identidad histórica.
    # Solo las identidades activas deben impedir una nueva carga.
    op.drop_constraint(
        "uq_expedientes_tenant_id_receptor_id_tipo_comprobante_serie_correlativo_emisor_id",
        "expedientes",
        type_="unique",
    )
    op.create_index(
        "uq_expedientes_identidad_activa",
        "expedientes",
        ["tenant_id", "receptor_id", "tipo_comprobante", "serie", "correlativo", "emisor_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )

    op.drop_constraint("uq_documentos_tenant_id_sha256", "documentos", type_="unique")
    op.create_index(
        "uq_documentos_tenant_sha256_activo",
        "documentos",
        ["tenant_id", "sha256"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )

    op.drop_constraint(
        "uq_documentos_tenant_id_huella_comercial",
        "documentos",
        type_="unique",
    )
    op.create_index(
        "uq_documentos_tenant_huella_comercial_activa",
        "documentos",
        ["tenant_id", "huella_comercial"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND huella_comercial IS NOT NULL"),
        sqlite_where=sa.text("deleted_at IS NULL AND huella_comercial IS NOT NULL"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    conflictos = (
        (
            "documentos SHA",
            """SELECT 1 FROM documentos GROUP BY tenant_id, sha256
               HAVING count(*) > 1 LIMIT 1""",
        ),
        (
            "huella comercial de documentos",
            """SELECT 1 FROM documentos WHERE huella_comercial IS NOT NULL
               GROUP BY tenant_id, huella_comercial HAVING count(*) > 1 LIMIT 1""",
        ),
        (
            "identidad fiscal de expedientes",
            """SELECT 1 FROM expedientes
               GROUP BY tenant_id, receptor_id, tipo_comprobante, serie, correlativo, emisor_id
               HAVING count(*) > 1 LIMIT 1""",
        ),
    )
    for nombre, consulta in conflictos:
        if bind.execute(sa.text(consulta)).first() is not None:
            raise RuntimeError(
                f"No se puede revertir 0043: existen registros históricos y activos con la misma {nombre}; "
                "preserve los datos y mantenga esta migración."
            )

    op.drop_index("uq_documentos_tenant_huella_comercial_activa", table_name="documentos")
    op.create_unique_constraint(
        "uq_documentos_tenant_id_huella_comercial",
        "documentos",
        ["tenant_id", "huella_comercial"],
    )
    op.drop_index("uq_documentos_tenant_sha256_activo", table_name="documentos")
    op.create_unique_constraint(
        "uq_documentos_tenant_id_sha256",
        "documentos",
        ["tenant_id", "sha256"],
    )
    op.drop_index("uq_expedientes_identidad_activa", table_name="expedientes")
    op.create_unique_constraint(
        "uq_expedientes_tenant_id_receptor_id_tipo_comprobante_serie_correlativo_emisor_id",
        "expedientes",
        ["tenant_id", "receptor_id", "tipo_comprobante", "serie", "correlativo", "emisor_id"],
    )
