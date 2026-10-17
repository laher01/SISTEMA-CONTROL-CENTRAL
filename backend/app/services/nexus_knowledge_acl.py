"""Politica reusable de acceso a memoria privada NEXUS.

Este modulo NO conecta documentos privados a la biblioteca estatica.
Toda consulta futura a memoria privada debe aplicar este control antes
de ranking, LLM o entrega de metadatos.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum


class Visibilidad(StrEnum):
    PRIVADA = "PRIVATE"
    ROL = "ROLE"
    TENANT = "TENANT"


@dataclass(frozen=True)
class ActorConocimiento:
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    rol: str


@dataclass(frozen=True)
class PermisoConocimiento:
    tenant_id: uuid.UUID
    propietario_id: uuid.UUID
    visibilidad: Visibilidad
    roles_permitidos: frozenset[str] = frozenset()
    revocado: bool = False
    aprobado: bool = False


def acceso_conocimiento(actor: ActorConocimiento, recurso: PermisoConocimiento) -> bool:
    """Fail-closed: un rol nunca sustituye la pertenencia a su Tenant."""
    if actor.tenant_id != recurso.tenant_id or recurso.revocado or not recurso.aprobado:
        return False
    if recurso.visibilidad == Visibilidad.PRIVADA:
        return actor.usuario_id == recurso.propietario_id
    if recurso.visibilidad == Visibilidad.ROL:
        return actor.rol in recurso.roles_permitidos
    if recurso.visibilidad == Visibilidad.TENANT:
        return True
    return False
