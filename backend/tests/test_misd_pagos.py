"""Regresión MISD: los pagos generados congelan su producción de origen."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Expediente, PagoERP
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_pago_generado_bloquea_documento_y_expediente_incluso_para_admin(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("congelada.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = respuesta.json()
    expediente = session.get(Expediente, documento["expediente_id"])
    assert expediente is not None
    assert expediente.usuario_id is not None
    pago = PagoERP(
        tenant_id=expediente.tenant_id,
        usuario_id=expediente.usuario_id,
        periodo_desde=date(2026, 1, 1),
        periodo_hasta=date(2026, 12, 31),
        moneda=expediente.moneda,
        produccion_total=Decimal("100.00"),
        porcentaje=Decimal("10"),
        bruto=Decimal("10.00"),
        saldo=Decimal("10.00"),
        estado="PROGRAMADO",
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()

    ruta_documento = f"/api/v1/documentos/{documento['id']}"
    ruta_expediente = f"/api/v1/expedientes/{expediente.id}"
    documento_bloqueado = client.delete(ruta_documento)
    expediente_bloqueado = client.delete(ruta_expediente)
    assert documento_bloqueado.status_code == 409, documento_bloqueado.text
    assert expediente_bloqueado.status_code == 409, expediente_bloqueado.text
    assert "Liquidación" in documento_bloqueado.text
    assert client.get(ruta_documento).status_code == 200
    assert client.get(ruta_expediente).status_code == 200

    session.delete(pago)
    session.commit()
    assert client.delete(ruta_expediente).status_code == 204
