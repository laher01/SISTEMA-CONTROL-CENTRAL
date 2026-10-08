"""Regla especial de distribución Jonatan/Javier, sin Alex.

Esta calculadora prepara una *simulación*: no autoriza ni ejecuta pagos.
La selección de TOTAL_EMITIDO requiere confirmación explícita en el flujo de pagos.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")
CIEN = Decimal("100")


@dataclass(frozen=True)
class TasasJonatan:
    gente_lima: Decimal = Decimal("2.250")
    javier: Decimal = Decimal("0.125")
    jonatan: Decimal = Decimal("0.3125")

    def validar(self) -> None:
        tasas = (self.gente_lima, self.javier, self.jonatan)
        if any(t < 0 or t > CIEN for t in tasas):
            raise ValueError("Los porcentajes deben estar entre 0 y 100")
        if sum(tasas, Decimal("0")) != Decimal("2.6875"):
            raise ValueError("La suma de porcentajes debe ser 2.6875 %")


@dataclass(frozen=True)
class ResultadoJonatan:
    base: Decimal
    bruto: Decimal
    neto: Decimal
    excluido_alex: Decimal
    gente_lima: Decimal
    javier: Decimal
    jonatan: Decimal
    modo_base: str


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTIMO, rounding=ROUND_HALF_UP)


def calcular_distribucion_jonatan(
    *,
    total_emitido: Decimal,
    base_autorizada: Decimal | None = None,
    usar_total_emitido: bool = False,
    tasas: TasasJonatan | None = None,
) -> ResultadoJonatan:
    """Distribuir el 3 % con conciliación exacta en céntimos.

    Requiere seleccionar explícitamente una base manual positiva o confirmar
    la modalidad de total emitido. Un cero accidental nunca habilita pagar todo.
    """
    tasas = tasas or TasasJonatan()
    tasas.validar()
    if not total_emitido.is_finite() or total_emitido < 0:
        raise ValueError("Total emitido inválido")
    if usar_total_emitido:
        if base_autorizada is not None:
            raise ValueError("No combinar base manual con total emitido")
        base = total_emitido
        modo = "TOTAL_EMITIDO_CONFIRMADO"
    else:
        if base_autorizada is None or not base_autorizada.is_finite() or base_autorizada <= 0:
            raise ValueError("Se requiere una base manual positiva")
        if base_autorizada > total_emitido:
            raise ValueError("Base autorizada superior al total emitido")
        base = base_autorizada
        modo = "MANUAL"
    bruto = _redondear(base * Decimal("3") / CIEN)
    gente = _redondear(base * tasas.gente_lima / CIEN)
    javier = _redondear(base * tasas.javier / CIEN)
    neto = _redondear(base * Decimal("2.6875") / CIEN)
    jonatan = neto - gente - javier
    excluido_alex = bruto - neto
    return ResultadoJonatan(
        base=_redondear(base),
        bruto=bruto,
        neto=neto,
        excluido_alex=excluido_alex,
        gente_lima=gente,
        javier=javier,
        jonatan=jonatan,
        modo_base=modo,
    )
