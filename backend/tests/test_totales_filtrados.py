from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Expediente

from tests.conftest import AuthPrueba
from tests.xml import factura


def test_totales_globales_sin_duplicar_por_documentos(client: TestClient) -> None:
    ids = []
    for numero, importe in [("F001-00000601", "100.00"), ("F001-00000602", "200.00")]:
        response = client.post(
            "/api/v1/documentos",
            files={"archivo": (numero + ".xml", factura(numero=numero, importe=importe))},
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["expediente_id"])
    documentos = client.get("/api/v1/documentos/resumen")
    assert documentos.status_code == 200, documentos.text
    resumen = documentos.json()
    assert resumen["total_documentos"] == 2
    assert resumen["total_expedientes"] == 2
    assert Decimal(resumen["total_pen"]) == Decimal("300.00")

    expedientes = client.get("/api/v1/expedientes/resumen")
    assert expedientes.status_code == 200, expedientes.text
    assert expedientes.json()["total_expedientes"] == 2
    assert Decimal(expedientes.json()["total_pen"]) == Decimal("300.00")

    filtrado = client.get("/api/v1/expedientes/resumen", params={"emisor_ruc": "00000000000"})
    assert filtrado.status_code == 200, filtrado.text
    assert filtrado.json()["total_expedientes"] == 0


def test_eliminar_documento_actualiza_resumen_sin_eliminar_otras_facturas(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    ids = []
    for numero in ("F001-00000701", "F001-00000702"):
        respuesta = client.post(
            "/api/v1/documentos",
            files={"archivo": (numero + ".xml", factura(numero=numero, importe="100.00"))},
        )
        assert respuesta.status_code == 201, respuesta.text
        ids.append(respuesta.json()["id"])

    anterior = client.get("/api/v1/documentos/resumen")
    assert anterior.status_code == 200, anterior.text
    assert anterior.json()["total_documentos"] == 2

    auth_prueba.como_admin()
    eliminacion = client.delete(f"/api/v1/documentos/{ids[0]}")
    assert eliminacion.status_code == 204, eliminacion.text
    assert client.get(f"/api/v1/documentos/{ids[0]}").status_code == 404
    assert client.get(f"/api/v1/documentos/{ids[1]}").status_code == 200

    posterior = client.get("/api/v1/documentos/resumen")
    assert posterior.status_code == 200, posterior.text
    assert posterior.json()["total_documentos"] == 1


def test_dashboard_no_suma_expediente_con_cliente_pendiente(
    client: TestClient, session: Session
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("cliente-pendiente.xml", factura(numero="F001-00000998", importe="750.00"))},
    )
    assert respuesta.status_code == 201, respuesta.text
    expediente = session.get(Expediente, respuesta.json()["expediente_id"])
    assert expediente is not None
    expediente.pendiente_aprobacion = True
    session.commit()

    panel = client.get("/api/v1/dashboard/resumen")
    assert panel.status_code == 200, panel.text
    resumen = panel.json()
    assert resumen["pendientes_aprobacion"] >= 1
    assert all(
        Decimal(fila["bancarizable"]) + Decimal(fila["no_bancarizable"]) == 0
        for fila in resumen["montos"]
    )
