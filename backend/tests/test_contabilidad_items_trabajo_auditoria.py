"""Transiciones auditables: contrato previo a persistencia durable."""

import uuid
from datetime import UTC, datetime

import pytest

from app.services.contabilidad_items_trabajo_auditoria import (
    EstadoTrabajoXML,
    EventoAuditoriaXML,
)


def _evento(
    anterior: EstadoTrabajoXML, nuevo: EstadoTrabajoXML, *, fecha: datetime | None = None
) -> EventoAuditoriaXML:
    return EventoAuditoriaXML(
        trabajo_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        actor_cuenta_id=uuid.uuid4(),
        estado_anterior=anterior,
        estado_nuevo=nuevo,
        ocurrido_en=fecha or datetime.now(UTC),
    )


def test_ciclo_de_trabajo_permite_pausar_reanudar_y_completar():
    assert _evento(EstadoTrabajoXML.PENDIENTE, EstadoTrabajoXML.EJECUTANDO)
    assert _evento(EstadoTrabajoXML.EJECUTANDO, EstadoTrabajoXML.PAUSADO)
    assert _evento(EstadoTrabajoXML.PAUSADO, EstadoTrabajoXML.EJECUTANDO)
    assert _evento(EstadoTrabajoXML.EJECUTANDO, EstadoTrabajoXML.COMPLETADO)


@pytest.mark.parametrize(
    ("anterior", "nuevo"),
    [
        (EstadoTrabajoXML.PENDIENTE, EstadoTrabajoXML.COMPLETADO),
        (EstadoTrabajoXML.COMPLETADO, EstadoTrabajoXML.EJECUTANDO),
        (EstadoTrabajoXML.FALLIDO, EstadoTrabajoXML.PENDIENTE),
        (EstadoTrabajoXML.PAUSADO, EstadoTrabajoXML.COMPLETADO),
    ],
)
def test_rechaza_transiciones_ilegales(
    anterior: EstadoTrabajoXML, nuevo: EstadoTrabajoXML
):
    with pytest.raises(ValueError, match="Transición"):
        _evento(anterior, nuevo)


def test_rechaza_fecha_sin_zona_horaria():
    with pytest.raises(ValueError, match="zona horaria"):
        _evento(
            EstadoTrabajoXML.PENDIENTE,
            EstadoTrabajoXML.EJECUTANDO,
            fecha=datetime(2026, 10, 17),
        )
