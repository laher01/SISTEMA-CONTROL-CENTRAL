from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Tenant
from app.services.distribucion_jonatan import TasasJonatan, calcular_distribucion_jonatan
from tests.conftest import AuthPrueba


def test_pago_sobre_pedido_manual_sin_alex() -> None:
    r = calcular_distribucion_jonatan(
        total_emitido=Decimal("1114897.76"),
        base_autorizada=Decimal("378000.00"),
    )
    assert r.bruto == Decimal("11340.00")
    assert r.gente_lima == Decimal("8505.00")
    assert r.javier == Decimal("472.50")
    assert r.jonatan == Decimal("1181.25")
    assert r.neto == Decimal("10158.75")
    assert r.excluido_alex == Decimal("1181.25")
    assert r.gente_lima + r.javier + r.jonatan == r.neto
    assert r.modo_base == "MANUAL"


def test_pago_total_emitido_exige_confirmacion() -> None:
    with pytest.raises(ValueError):
        calcular_distribucion_jonatan(total_emitido=Decimal("1114897.76"))
    with pytest.raises(ValueError):
        calcular_distribucion_jonatan(
            total_emitido=Decimal("1114897.76"), base_autorizada=Decimal("0")
        )
    r = calcular_distribucion_jonatan(total_emitido=Decimal("1114897.76"), usar_total_emitido=True)
    assert r.bruto == Decimal("33446.93")
    assert r.gente_lima == Decimal("25085.20")
    assert r.javier == Decimal("1393.62")
    assert r.jonatan == Decimal("3484.06")
    assert r.neto == Decimal("29962.88")
    assert r.excluido_alex == Decimal("3484.05")
    assert r.gente_lima + r.javier + r.jonatan == r.neto


def test_tasas_personalizadas_y_validaciones() -> None:
    with pytest.raises(ValueError):
        calcular_distribucion_jonatan(total_emitido=Decimal("100"), base_autorizada=Decimal("120"))
    with pytest.raises(ValueError):
        calcular_distribucion_jonatan(
            total_emitido=Decimal("100"),
            base_autorizada=Decimal("100"),
            tasas=TasasJonatan(jonatan=Decimal("0.500")),
        )


def test_endpoint_simulacion_autorizada(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    solicitud = {
        "total_emitido": "1114897.76",
        "base_autorizada": "380000.00",
    }
    assert client.post("/api/v1/pagos/simular-jonatan", json=solicitud).status_code == 403
    auth_prueba.como_admin()
    assert client.post("/api/v1/pagos/simular-jonatan", json=solicitud).status_code == 403

    tenant = session.get(Tenant, auth_prueba.contexto.tenant_id)
    assert tenant is not None
    tenant.codigo = "LAH-001-AD"
    session.commit()

    respuesta = client.post("/api/v1/pagos/simular-jonatan", json=solicitud)
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert Decimal(str(datos["neto_pagable"])) == Decimal("10212.50")
    assert Decimal(str(datos["gente_lima"])) == Decimal("8550.00")
    assert Decimal(str(datos["javier"])) == Decimal("475.00")
    assert Decimal(str(datos["jonatan"])) == Decimal("1187.50")
