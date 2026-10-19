"""Persistencia editorial global con exclusión por versión.

No expone endpoints; requiere autorización SUPERADMIN del servicio llamante
y validación editorial antes de aceptar contenido.
"""

import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    func,
    select,
)
from sqlalchemy.orm import Session

from app.models import Base
from app.services.cms_landing_core import EstadoEditorial, RevisionEditorial, transicionar

metadata = Base.metadata

revision_table = Table(
    "cms_landing_revision",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("version", Integer, nullable=False),
    Column("estado", String(24), nullable=False),
    Column("contenido", JSON, nullable=False),
    Column("actualizado_por", Uuid, ForeignKey("cuentas_acceso.id")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
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
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("version_nueva", name="uq_cms_landing_evento_version"),
)

publicacion_table = Table(
    "cms_landing_publicacion",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("version_editorial", Integer, nullable=False),
    Column("contenido", JSON, nullable=False),
    Column("publicado_por", Uuid, ForeignKey("cuentas_acceso.id"), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
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

    consulta = select(revision_table).where(revision_table.c.id == 1).with_for_update()
    filas = session.execute(consulta)
    actual = filas.mappings().one_or_none()
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
    resultado = session.execute(
        revision_table.update()
        .where(revision_table.c.id == 1)
        .where(revision_table.c.version == version_esperada)
        .values(
            version=nueva.version,
            estado=nueva.estado.value,
            actualizado_por=actor_id,
        )
    )
    if getattr(resultado, "rowcount", None) != 1:
        session.rollback()
        raise ValueError("Conflicto concurrente de versión")
    try:
        if destino == EstadoEditorial.PUBLICADO:
            # Snapshot reemplazado atomica y exclusivamente al publicar.
            sesion_publica = session.execute(
                select(publicacion_table.c.id).where(publicacion_table.c.id == 1).with_for_update()
            ).scalar_one_or_none()
            if sesion_publica is None:
                session.execute(
                    publicacion_table.insert().values(
                        id=1,
                        version_editorial=nueva.version,
                        contenido=dict(nueva.contenido),
                        publicado_por=actor_id,
                    )
                )
            else:
                session.execute(
                    publicacion_table.update()
                    .where(publicacion_table.c.id == 1)
                    .values(
                        version_editorial=nueva.version,
                        contenido=dict(nueva.contenido),
                        publicado_por=actor_id,
                        published_at=func.now(),
                    )
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
    except Exception:
        session.rollback()
        raise
    return nueva


def guardar_borrador(
    session: Session,
    *,
    contenido: dict[str, object],
    version_esperada: int,
    rol: str,
    actor_id: uuid.UUID,
) -> RevisionEditorial:
    """Crear o editar borrador con versionado; nunca afecta la landing pública."""
    if rol != "SUPERADMIN" or not isinstance(actor_id, uuid.UUID):
        raise PermissionError("Solo SUPERADMIN puede administrar el CMS")
    consulta = select(revision_table).where(revision_table.c.id == 1).with_for_update()
    actual = session.execute(consulta).mappings().one_or_none()
    if actual is None:
        if version_esperada != 0:
            raise ValueError("Conflicto de versión editorial")
        nueva = RevisionEditorial(1, EstadoEditorial.BORRADOR, contenido)
        session.execute(
            revision_table.insert().values(
                id=1,
                version=1,
                estado=nueva.estado.value,
                contenido=contenido,
                actualizado_por=actor_id,
            )
        )
        anterior_version = 0
    else:
        if actual["version"] != version_esperada:
            raise ValueError("Conflicto de versión editorial")
        if actual["estado"] != EstadoEditorial.BORRADOR.value:
            raise ValueError("Solo se puede editar un borrador")
        nueva = RevisionEditorial(version_esperada + 1, EstadoEditorial.BORRADOR, contenido)
        cambiado = session.execute(
            revision_table.update()
            .where(revision_table.c.id == 1)
            .where(revision_table.c.version == version_esperada)
            .values(
                contenido=contenido,
                version=nueva.version,
                actualizado_por=actor_id,
            )
        )
        if getattr(cambiado, "rowcount", None) != 1:
            session.rollback()
            raise ValueError("Conflicto concurrente de versión")
        anterior_version = version_esperada
    try:
        session.execute(
            evento_table.insert().values(
                id=uuid.uuid4(),
                version_anterior=anterior_version,
                version_nueva=nueva.version,
                anterior=EstadoEditorial.BORRADOR.value,
                nuevo=EstadoEditorial.BORRADOR.value,
                actor_id=actor_id,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return nueva
