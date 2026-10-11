"""El consolidado de flujos no es una conciliación bancaria ni un saldo por cobrar."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AbonoClienteERP, Empresa, Expediente
from tests.conftest import AuthPrueba


def test_flujos_por_periodo_y_acceso(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    empresa = Empresa(
        tenant_id=auth_prueba.contexto.tenant_id,
        ruc="20997773331",
        razon_social="Cliente de prueba",
        tipo_relacion="CLIENTE",
    )
    session.add(empresa)
    session.flush()
    session.add(
        Expediente(
            tenant_id=auth_prueba.contexto.tenant_id,
            emisor_id=empresa.id,
            receptor_id=empresa.id,
            tipo_comprobante="FACT",
            serie="F001",
            correlativo="4001",
            fecha_emision=date(2026, 10, 4),
            moneda="PEN",
            importe_total=Decimal("120.00"),
        )
    )
    session.add(
        AbonoClienteERP(
            tenant_id=auth_prueba.contexto.tenant_id,
            cliente_id=empresa.id,
            fecha=date(2026, 10, 8),
            moneda="PEN",
            monto=Decimal("70.00"),
        )
    )
    session.commit()
    url = "/api/v1/pagos/consolidado-flujos"
    params = {"desde": "2026-10-01", "hasta": "2026-10-31", "moneda": "PEN"}
    auth_prueba.como_gerente()
    assert client.get(url, params=params).status_code == 403
    auth_prueba.como_admin()
    respuesta = client.get(url, params=params)
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert Decimal(datos["produccion_periodo"]) == Decimal("120.00")
    assert Decimal(datos["abonos_registrados_periodo"]) == Decimal("70.00")
    assert "no equivale al saldo" in datos["advertencia"]
    assert client.get(url, params={**params, "moneda": "USD"}).json()["produccion_periodo"] == "0"
    assert client.get(url, params={**params, "desde": "2026-11-01"}).status_code == 422
    assert client.get(url, params={**params, "desde": "2025-01-01"}).status_code == 422
    assert client.get(url, params={**params, "moneda": "EUR"}).status_code == 422
    fuera_de_periodo = client.get(
        url,
        params={**params, "desde": "2026-09-01", "hasta": "2026-09-30"},
    )
    assert fuera_de_periodo.status_code == 200
    assert Decimal(fuera_de_periodo.json()["produccion_periodo"]) == 0
    assert Decimal(fuera_de_periodo.json()["abonos_registrados_periodo"]) == 0
