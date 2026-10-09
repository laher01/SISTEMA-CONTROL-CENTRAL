"""Regresiones de comisiones por receptor y pago exclusivo a Responsable."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Miembro
from tests.conftest import AuthPrueba


def _preparar(session: Session, auth_prueba: AuthPrueba) -> tuple[str, str]:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-01",
        nombre="Responsable prueba",
        rol="RESPONSABLE",
        activo=True,
    )
    usuario = Miembro(
        tenant_id=tenant_id,
        codigo="USU-01",
        nombre="Usuario prueba",
        rol="USUARIO",
        activo=True,
    )
    cliente = Empresa(
        tenant_id=tenant_id,
        ruc="20538821374",
        razon_social="CLIENTE PRUEBA",
        tipo_relacion="CLIENTE",
        agente_retencion=False,
    )
    session.add_all([responsable, usuario, cliente])
    session.flush()
    usuario.responsable_id = responsable.id
    factura = Expediente(
        tenant_id=tenant_id,
        emisor_id=cliente.id,
        receptor_id=cliente.id,
        tipo_comprobante="FACT",
        serie="F001",
        correlativo="00001",
        fecha_emision=date(2026, 9, 15),
        moneda="PEN",
        importe_total=Decimal("1000.00"),
        usuario_id=usuario.id,
    )
    session.add(factura)
    session.commit()
    return str(responsable.id), str(cliente.id)


def test_comisiones_gerencia_por_cliente_y_autorizacion(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
) -> None:
    responsable_id, cliente_id = _preparar(session, auth_prueba)
    auth_prueba.como_gerente()
    url = "/api/v1/pagos-responsables"
    params = {"desde": "2026-09-01", "hasta": "2026-09-30", "moneda": "PEN"}
    resumen = client.get(url + "/resumen", params=params)
    assert resumen.status_code == 200, resumen.text
    datos = resumen.json()
    assert datos["total_produccion"] == "1000.00"
    assert datos["total_comisiones"] == "35.00"
    assert datos["filas"][0]["cliente_id"] == cliente_id
    assert datos["filas"][0]["exceso"] == "1000.00"

    cambio = client.put(
        url + "/comision",
        json={
            "responsable_id": responsable_id,
            "cliente_id": cliente_id,
            "porcentaje": "4.0",
            "motivo": "Condición especial de Gerencia",
        },
    )
    assert cambio.status_code == 200, cambio.text
    modificado = client.get(url + "/resumen", params=params).json()
    assert modificado["total_comisiones"] == "40.00"

    historial = client.get(f"{url}/comision/{responsable_id}/{cliente_id}/historial")
    assert historial.status_code == 200, historial.text
    assert historial.json()[0]["datos"]["actor"] == "GERENTE-TEST"

    programado = client.post(
        url + "/programar",
        json={
            "responsable_id": responsable_id,
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": "PEN",
        },
    )
    assert programado.status_code == 201, programado.text
    pago_id = programado.json()["id"]

    repetido = client.post(
        url + "/programar",
        json={
            "responsable_id": responsable_id,
            "desde": "2026-09-15",
            "hasta": "2026-10-15",
            "moneda": "PEN",
        },
    )
    assert repetido.status_code == 409

    confirmar = client.post(
        f"{url}/{pago_id}/confirmar",
        json={"fecha_pago": "2026-10-09", "referencia_pago": "BANCO-01234"},
    )
    assert confirmar.status_code == 200, confirmar.text
    assert confirmar.json()["estado"] == "PAGADO"

    auth_prueba.como_admin()
    prohibido = client.post(
        f"{url}/{pago_id}/confirmar",
        json={"fecha_pago": "2026-10-09", "referencia_pago": "BANCO-99999"},
    )
    assert prohibido.status_code == 403
