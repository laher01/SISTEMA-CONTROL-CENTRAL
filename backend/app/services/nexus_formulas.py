"""NEXUS: fórmulas de pago declarativas, verificables y sin ejecución de código libre."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

CENTIMO = Decimal("0.01")
CIEN = Decimal("100")


@dataclass(frozen=True)
class TramoProduccion:
    base: Decimal
    porcentaje: Decimal

    def validar(self) -> None:
        if not self.base.is_finite() or self.base < 0:
            raise ValueError("La producción debe ser finita y no negativa")
        if not self.porcentaje.is_finite() or not 0 <= self.porcentaje <= CIEN:
            raise ValueError("El porcentaje debe estar entre 0 y 100")


@dataclass(frozen=True)
class PagoEstandar:
    sin_retencion: Decimal
    con_retencion: Decimal
    total: Decimal


def calcular_pago_estandar(
    *,
    produccion_sin_retencion: Decimal,
    porcentaje_sin_retencion: Decimal,
    produccion_con_retencion: Decimal,
    porcentaje_con_retencion: Decimal,
) -> PagoEstandar:
    """Calcula la comisión normal usando las tasas registradas del usuario."""
    sin = TramoProduccion(produccion_sin_retencion, porcentaje_sin_retencion)
    con = TramoProduccion(produccion_con_retencion, porcentaje_con_retencion)
    sin.validar()
    con.validar()
    sin_pago = (sin.base * sin.porcentaje / CIEN).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    con_pago = (con.base * con.porcentaje / CIEN).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    return PagoEstandar(
        sin_retencion=sin_pago,
        con_retencion=con_pago,
        total=sin_pago + con_pago,
    )


def validar_destinatario_especial(
    *,
    codigo_usuario: str,
    codigo_esperado: Literal["JONA01"] = "JONA01",
) -> None:
    """Segunda barrera; la autorización de tenant y usuario_id va en la API."""
    if codigo_usuario.strip().upper() != codigo_esperado:
        raise ValueError("Fórmula especial exclusiva de JONA01")


def validar_propuesta_nexus(
    *,
    expresion: str,
    variables: set[str],
    variables_permitidas: set[str],
) -> None:
    """No admite expresiones de programación; únicamente plantillas registradas."""
    if expresion not in {"PAGO_ESTANDAR_V1", "DISTRIBUCION_JONA01_V1"}:
        raise ValueError("Plantilla de fórmula no permitida")
    if not variables.issubset(variables_permitidas):
        raise ValueError("Variables no autorizadas")

