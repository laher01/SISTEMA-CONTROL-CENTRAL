from datetime import date
from decimal import Decimal

from app.core.config import Settings
from app.services.expedientes import fecha_limite, requiere_bancarizacion


def test_fecha_limite_mes_siguiente() -> None:
    assert fecha_limite(date(2026, 9, 30), 7) == date(2026, 10, 7)
    assert fecha_limite(date(2026, 12, 1), 7) == date(2027, 1, 7)


def test_umbral_bancarizacion() -> None:
    settings = Settings()
    assert requiere_bancarizacion("PEN", Decimal("2000.00"), settings)
    assert not requiere_bancarizacion("PEN", Decimal("1999.99"), settings)
    assert requiere_bancarizacion("USD", Decimal("500.00"), settings)
    assert not requiere_bancarizacion("USD", Decimal("499.99"), settings)
