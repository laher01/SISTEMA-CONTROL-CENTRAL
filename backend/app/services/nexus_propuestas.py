"""Propuestas declarativas de NEXUS: aprobación explícita antes de uso.

Este módulo no guarda propuestas ni ejecuta pagos. La persistencia y autorización
deben resolverse en el servicio de aplicación, bajo tenant y Responsable.
"""

from dataclasses import dataclass
from enum import StrEnum


class EstadoFormula(StrEnum):
    BORRADOR = "BORRADOR"
    APROBADA = "APROBADA"
    REVOCADA = "REVOCADA"


@dataclass(frozen=True)
class PropuestaFormula:
    plantilla: str
    version: int
    estado: EstadoFormula
    usuario_codigo: str
    responsable_codigo: str

    def validar(self) -> None:
        if self.version < 1:
            raise ValueError("La versión debe ser positiva")
        if not self.responsable_codigo.strip():
            raise ValueError("Falta identificar al Responsable")
        if self.plantilla == "DISTRIBUCION_JONA01_V1":
            if self.usuario_codigo.upper() != "JONA01":
                raise ValueError("Distribución especial restringida a JONA01")
        elif self.plantilla != "PAGO_ESTANDAR_V1":
            raise ValueError("Plantilla desconocida")

    def habilitada_para_liquidar(self) -> bool:
        self.validar()
        return self.estado == EstadoFormula.APROBADA


def transicion_formula(actual: EstadoFormula, siguiente: EstadoFormula) -> EstadoFormula:
    """Transiciones permitidas, sin reactivar fórmulas revocadas."""
    if (actual, siguiente) not in {
        (EstadoFormula.BORRADOR, EstadoFormula.APROBADA),
        (EstadoFormula.BORRADOR, EstadoFormula.REVOCADA),
        (EstadoFormula.APROBADA, EstadoFormula.REVOCADA),
    }:
        raise ValueError("Transición de fórmula no permitida")
    return siguiente
