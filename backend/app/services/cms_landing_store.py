"""Persistencia editorial global con exclusión por versión.

No expone endpoints; requiere autorización SUPERADMIN del servicio llamante
y validación editorial antes de aceptar contenido.
"""

import uuid

from sqlalchemy import JSON, Column, ForeignKey, Integer, MetaData, String, Table, Uuid, select
from sqlalchemy.orm import Session

from app.services.cms_landing_core import EstadoEditorial, RevisionEditorial, transicionar

metadata = MetaData()

revision_table = Table(
    "cms_landing_revision",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("version", Integer, nullable=False),
    Column("estado", String(24), nullable=False),
    Column("contenido", JSON, nullable=False),
    Column("actualizado_por", Uuid, ForeignKey("cuentas_acceso.id")),
)

evento_table = Table(
    "cms_landing_evento",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("version_anterior", Integer, nullable=False),
    Column("version_nueva", Integer, nullable=False),
    Column("anterior", String(24), nullable=False),
    Column("nuevo", String(24), nullable=False),
    Column("actor_id", Uuid, ForeignKey("cuentas_acceso.id"), nullable=False),
)


def cambiar_estado(
    session: Session,
    *,
    destino: EstadoEditorial,
    version_esperada: int,
    rol: str,
    actor_id: uuid.UUID,
) -> RevisionEditorial:
    """Aplicar cambio y auditoría en la misma transacción; no publica la landing."""
    if rol != "SUPERADMIN":
        raise PermissionError("Solo SUPERADMIN puede administrar el CMS global")
    if not isinstance(actor_id, uuid.UUID):
        raise PermissionError("Identidad editorial requerida")

    actual = session.execute(
        select(revision_table).where(revision_table.c.id == 1).with_for_update()
    ).mappings().one_or_none()
    if actual is None:
        raise LookupError("Inicialice un borrador aprobado antes de transicionar")

    revision = RevisionEditorial(
        version=actual["version"],
        estado=EstadoEditorial(actual["estado"]),
        contenido=actual["contenido"],
    )
    nueva, evento = transicionar(
        revision,
        destino=destino,
        version_esperada=version_esperada,
        rol=rol,
        actor_id=str(actor_id),
    )
    session.execute(
        revision_table.update()
        .where(revision_table.c.id == 1)
        .where(revision_table.c.version == version_esperada)
        .values(version=nueva.version, estado=nueva.estado.value, actualizado_por=actor_id)
    )
    session.execute(
        evento_table.insert().values(
            id=uuid.uuid4(),
            version_anterior=evento.version_anterior,
            version_nueva=evento.version_nueva,
            anterior=evento.anterior.value,
            nuevo=evento.nuevo.value,
            actor_id=actor_id,
        )
    )
    session.commit()
    return nueva
