from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Miembro
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_gerencia_entrega_bruto_y_responsable_distribuye(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    resp = Miembro(
        tenant_id=tenant_id,
        codigo="RESPBRUTO",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    propio = Miembro(
        tenant_id=tenant_id,
        codigo="USBRUTO",
        nombre="Usuario propio",
        rol="USUARIO",
        activo=True,
    )
    ajeno = Miembro(
        tenant_id=tenant_id,
        codigo="USAJENO",
        nombre="Usuario ajeno",
        rol="USUARIO",
        activo=True,
    )
    cliente = Empresa(
        tenant_id=tenant_id,
        ruc="20599990001",
        razon_social="Cliente presupuesto",
        tipo_relacion="CLIENTE",
    )
    session.add_all([resp, propio, ajeno, cliente])
    session.flush()
    propio.responsable_id = resp.id
    session.commit()

    auth_prueba.como_admin()
    pedido = client.post(
        "/api/v1/pagos/pedidos",
        json={
            "cliente_id": str(cliente.id),
            "responsable_id": str(resp.id),
            "periodo_mes": date(2026, 10, 1).isoformat(),
            "moneda": "PEN",
            "monto_solicitado": "1500.00",
            "modo_distribucion": "MANUAL",
        },
    )
    assert pedido.status_code == 201, pedido.text
    pedido_id = pedido.json()["id"]
    assert pedido.json()["asignaciones"] == []
    assert pedido.json()["responsable_id"] == str(resp.id)
    indebido = client.post(
        "/api/v1/pagos/pedidos",
        json={
            "cliente_id": str(cliente.id),
            "responsable_id": str(resp.id),
            "periodo_mes": "2026-11-01",
            "moneda": "PEN",
            "monto_solicitado": "1000.00",
            "modo_distribucion": "AUTOMATICA",
        },
    )
    assert indebido.status_code == 422

    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=auth_prueba.contexto.cuenta_id,
        tenant_id=tenant_id,
        rol="RESPONSABLE",
        miembro_id=resp.id,
        gestor_id=None,
        usuario_id=None,
        codigo=resp.codigo,
        nombre=resp.nombre,
        cambio_clave_obligatorio=False,
    )
    resumen = client.get("/api/v1/responsable/resumen")
    assert resumen.status_code == 200, resumen.text
    assert len(resumen.json()["pedidos"]) == 1
    assert resumen.json()["pedidos"][0]["monto_solicitado"] == "1500.00"
    url = f"/api/v1/responsable/pedidos/{pedido_id}/distribuir"
    assert client.post(
        url, json={"usuario_id": str(ajeno.id), "monto": "100.00"}
    ).status_code == 403
    assert client.post(
        url, json={"usuario_id": str(propio.id), "monto": "1500.01"}
    ).status_code == 422
    registrado = client.post(url, json={"usuario_id": str(propio.id), "monto": "900.00"})
    assert registrado.status_code == 200, registrado.text
    resumen = client.get("/api/v1/responsable/resumen")
    assert resumen.json()["pedidos"][0]["monto_asignado"] == "900.00"
    assert resumen.json()["pedidos"][0]["pendiente_distribuir"] == "600.00"
