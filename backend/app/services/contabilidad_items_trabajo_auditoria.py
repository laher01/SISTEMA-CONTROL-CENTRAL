"""Contrato interno para auditoría de reprocesamientos; NO ejecuta ni persiste trabajos.

Las transiciones y eventos se validan aquí, antes de añadir migraciones y workers.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class EstadoTrabajoXML(StrEnum):
    PENDIENTE = "PENDIENTE"
    EJECUTANDO = "EJECUTANDO"
    PAUSADO = "PAUSADO"
    COMPLETADO = "COMPLETADO"
    FALLIDO = "FALLIDO"


TRANSICIONES_PERMITIDAS: dict[EstadoTrabajoXML, frozenset[EstadoTrabajoXML]] = {
    EstadoTrabajoXML.PENDIENTE: frozenset({EstadoTrabajoXML.EJECUTANDO, EstadoTrabajoXML.FALLIDO}),
    EstadoTrabajoXML.EJECUTANDO: frozenset(
        {EstadoTrabajoXML.PAUSADO, EstadoTrabajoXML.COMPLETADO, EstadoTrabajoXML.FALLIDO}
    ),
    EstadoTrabajoXML.PAUSADO: frozenset({EstadoTrabajoXML.EJECUTANDO, EstadoTrabajoXML.FALLIDO}),
    EstadoTrabajoXML.COMPLETADO: frozenset(),
    EstadoTrabajoXML.FALLIDO: frozenset(),
}


@dataclass(frozen=True)
class EventoAuditoriaXML:
    trabajo_id: uuid.UUID
    tenant_id: uuid.UUID
    actor_cuenta_id: uuid.UUID
    estado_anterior: EstadoTrabajoXML
    estado_nuevo: EstadoTrabajoXML
    ocurrido_en: datetime
    documento_id: uuid.UUID | None = None
    cursor_documento_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if self.estado_nuevo not in TRANSICIONES_PERMITIDAS[self.estado_anterior]:
            raise ValueError("Transición de trabajo XML no permitida")
        if self.ocurrido_en.tzinfo is None or self.ocurrido_en.utcoffset() is None:
            raise ValueError("La auditoría necesita fecha con zona horaria")
        if any(ident.int == 0 for ident in (self.trabajo_id, self.tenant_id, self.actor_cuenta_id)):
            raise ValueError("Identificadores de auditoría XML inválidos")
