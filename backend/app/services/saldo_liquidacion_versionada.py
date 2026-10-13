"""Cálculo aislado de saldos sobre una liquidación histórica inmutable.

No escribe en base de datos, no confirma ni ejecuta transferencias.
El almacenamiento deberá imponer unicidad transaccional de referencia e idempotencia.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")


def _dinero(valor: Decimal) -> Decimal:
    if not valor.is_finite() or valor < 0:
        raise ValueError("Importe inválido")
    if valor.quantize(CENTIMO) != valor:
        raise ValueError("Importe debe expresarse en céntimos")
    return valor


@dataclass(frozen=True)
class LiquidacionVersionada:
    id: str
    version_regla: str
    moneda: str
    bruto_aprobado: Decimal

    def __post_init__(self) -> None:
        if not self.id or not self.version_regla or self.moneda not in ("PEN", "USD"):
            raise ValueError("Identidad, versión o moneda inválida")
        _dinero(self.bruto_aprobado)


@dataclass(frozen=True)
class MovimientoLiquidacion:
    referencia: str
    importe: Decimal
    moneda: str

    def __post_init__(self) -> None:
        if not self.referencia or not self.referencia.strip():
            raise ValueError("Referencia obligatoria")
        if self.moneda not in ("PEN", "USD") or self.importe <= 0:
            raise ValueError("Movimiento inválido")
        _dinero(self.importe)


def calcular_saldo(
    liquidacion: LiquidacionVersionada,
    movimientos: tuple[MovimientoLiquidacion, ...],
) -> Decimal:
    """Rechaza referencias duplicadas, exceso sobre bruto y monedas distintas.

    Nunca recalcula la comisión con una tasa vigente nueva.
    """
    referencias: set[str] = set()
    pagado = Decimal("0")
    for movimiento in movimientos:
        clave = movimiento.referencia.strip()
        if clave in referencias:
            raise ValueError("Movimiento duplicado")
        referencias.add(clave)
        if movimiento.moneda != liquidacion.moneda:
            raise ValueError("Moneda distinta de la liquidación")
        pagado += movimiento.importe
        if pagado > liquidacion.bruto_aprobado:
            raise ValueError("Movimiento supera saldo")
    return (liquidacion.bruto_aprobado - pagado).quantize(CENTIMO, rounding=ROUND_HALF_UP)
