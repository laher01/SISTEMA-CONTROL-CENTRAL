"""Núcleo editorial puro; aún sin persistencia, API ni publicación web.

No sustituye autorización del servidor ni el gate fail-closed de landing.
"""
from dataclasses import dataclass, replace
from enum import StrEnum


class EstadoEditorial(StrEnum):
    BORRADOR = "borrador"
    VISTA_PREVIA = "vista_previa"
    APROBADO = "aprobado"
    PUBLICADO = "publicado"


@dataclass(frozen=True)
class RevisionEditorial:
    version: int
    estado: EstadoEditorial
    contenido: dict[str, object]


@dataclass(frozen=True)
class EventoEditorial:
    version_anterior: int
    version_nueva: int
    anterior: EstadoEditorial
    nuevo: EstadoEditorial
    actor_id: str


TRANSICIONES = {
    EstadoEditorial.BORRADOR: {EstadoEditorial.VISTA_PREVIA},
    EstadoEditorial.VISTA_PREVIA: {EstadoEditorial.APROBADO, EstadoEditorial.BORRADOR},
    EstadoEditorial.APROBADO: {EstadoEditorial.PUBLICADO, EstadoEditorial.BORRADOR},
    EstadoEditorial.PUBLICADO: {EstadoEditorial.BORRADOR},
}


def transicionar(
    revision: RevisionEditorial,
    *,
    destino: EstadoEditorial,
    version_esperada: int,
    rol: str,
    actor_id: str,
) -> tuple[RevisionEditorial, EventoEditorial]:
    """Validar reglas; persistencia/atomicidad deben implementarse en servicio transaccional."""
    if rol != "SUPERADMIN" or not actor_id:
        raise PermissionError("Solo SUPERADMIN puede administrar el CMS global")
    if version_esperada != revision.version:
        raise ValueError("Conflicto de versión editorial")
    if destino not in TRANSICIONES[revision.estado]:
        raise ValueError("Transición editorial no permitida")
    actualizado = replace(revision, version=revision.version + 1, estado=destino)
    evento = EventoEditorial(revision.version, actualizado.version, revision.estado, destino, actor_id)
    return actualizado, evento
