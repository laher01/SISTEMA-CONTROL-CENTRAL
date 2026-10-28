"""Permitir un ingreso nuevo después de retirar identidades anteriores.

Revision ID: 0043
Revises: 0042
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels = None
depends_on = None


_EXPEDIENTE_IDENTITY_COLUMNS = [
    "tenant_id",
    "receptor_id",
    "tipo_comprobante",
    "serie",
    "correlativo",
    "emisor_id",
]


def _nombre_constraint_identidad_expediente(bind) -> str:
    constraints = sa.inspect(bind).get_unique_constraints("expedientes")
    matches = [
        constraint["name"]
        for constraint in constraints
        if constraint.get("column_names") == _EXPEDIENTE_IDENTITY_COLUMNS
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "No se encontró exactamente una restricción única de identidad de expediente"
        )
    return matches[0]


def upgrade() -> None:
    bind = op.get_bind()
    nombre_constraint_expediente = _nombre_constraint_identidad_expediente(bind)
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("solicitudes_retiro_misd") as batch:
            batch.drop_constraint(
                "fk_solicitudes_retiro_misd_expediente_id_expedientes",
                type_="foreignkey",
            )
        with op.batch_alter_table("documentos") as batch:
            batch.drop_constraint("uq_documentos_tenant_id_sha256", type_="unique")
            batch.drop_constraint("uq_documentos_tenant_id_huella_comercial", type_="unique")
        with op.batch_alter_table("expedientes") as batch:
            batch.drop_constraint(nombre_constraint_expediente, type_="unique")
    else:
        op.drop_constraint(
            "fk_solicitudes_retiro_misd_expediente_id_expedientes",
            "solicitudes_retiro_misd",
            type_="foreignkey",
        )
        op.drop_constraint("uq_documentos_tenant_id_sha256", "documentos", type_="unique")
        op.drop_constraint("uq_documentos_tenant_id_huella_comercial", "documentos", type_="unique")
        op.drop_constraint(
            nombre_constraint_expediente,
            "expedientes",
            type_="unique",
        )

    op.create_index(
        "uq_documentos_sha_activo",
        "documentos",
        ["tenant_id", "sha256"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_documentos_huella_activa",
        "documentos",
        ["tenant_id", "huella_comercial"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND huella_comercial IS NOT NULL"),
        sqlite_where=sa.text("deleted_at IS NULL AND huella_comercial IS NOT NULL"),
    )
    op.create_index(
        "uq_expedientes_identidad_activa",
        "expedientes",
        [
            "tenant_id",
            "receptor_id",
            "tipo_comprobante",
            "serie",
            "correlativo",
            "emisor_id",
        ],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    duplicados = bind.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM solicitudes_retiro_misd s LEFT JOIN expedientes e "
            "ON e.id = s.expediente_id WHERE e.id IS NULL) "
            "OR EXISTS (SELECT 1 FROM documentos GROUP BY tenant_id, sha256 "
            "HAVING count(*) > 1) OR EXISTS (SELECT 1 FROM documentos "
            "WHERE huella_comercial IS NOT NULL GROUP BY tenant_id, huella_comercial "
            "HAVING count(*) > 1) OR EXISTS (SELECT 1 FROM expedientes GROUP BY tenant_id, "
            "receptor_id, tipo_comprobante, serie, correlativo, emisor_id HAVING count(*) > 1)"
        )
    ).scalar_one()
    if duplicados:
        raise RuntimeError(
            "No es seguro revertir: hay identidades repetidas en registros eliminados"
        )

    op.drop_index("uq_expedientes_identidad_activa", table_name="expedientes")
    op.drop_index("uq_documentos_huella_activa", table_name="documentos")
    op.drop_index("uq_documentos_sha_activo", table_name="documentos")
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("solicitudes_retiro_misd") as batch:
            batch.create_foreign_key(
                "fk_solicitudes_retiro_misd_expediente_id_expedientes",
                "expedientes",
                ["expediente_id"],
                ["id"],
            )
        with op.batch_alter_table("documentos") as batch:
            batch.create_unique_constraint(
                "uq_documentos_tenant_id_sha256", ["tenant_id", "sha256"]
            )
            batch.create_unique_constraint(
                "uq_documentos_tenant_id_huella_comercial",
                ["tenant_id", "huella_comercial"],
            )
        with op.batch_alter_table("expedientes") as batch:
            batch.create_unique_constraint(
                op.f("uq_exp_ident_legacy"),
                _EXPEDIENTE_IDENTITY_COLUMNS,
            )
    else:
        op.create_foreign_key(
            "fk_solicitudes_retiro_misd_expediente_id_expedientes",
            "solicitudes_retiro_misd",
            "expedientes",
            ["expediente_id"],
            ["id"],
        )
        op.create_unique_constraint(
            "uq_documentos_tenant_id_sha256", "documentos", ["tenant_id", "sha256"]
        )
        op.create_unique_constraint(
            "uq_documentos_tenant_id_huella_comercial",
            "documentos",
            ["tenant_id", "huella_comercial"],
        )
        op.create_unique_constraint(
            op.f("uq_exp_ident_legacy"),
            "expedientes",
            _EXPEDIENTE_IDENTITY_COLUMNS,
        )
