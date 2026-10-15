"""Regresiones: Dashboard comparte alcance para tarjetas, tabla y opciones."""

import uuid

from fastapi.testclient import TestClient

from app.security import ContextoAcceso
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_dashboard_mes_resumen_desglose_y_opciones(client: TestClient) -> None:
    for numero in ("F001-00000901", "F001-00000902"):
        respuesta = client.post(
            "/api/v1/documentos",
            files={"archivo": (numero + ".xml", factura(numero=numero))},
        )
        assert respuesta.status_code == 201, respuesta.text

    resumen = client.get("/api/v1/dashboard/resumen")
    assert resumen.status_code == 200, resumen.text
    assert resumen.json()["expedientes_total"] == 2

    desglose = client.get("/api/v1/dashboard/desglose")
    assert desglose.status_code == 200
    assert sum(f["expedientes"] for f in desglose.json()["filas"]) == 2

    for grupo in ("responsable", "usuario", "gestor", "emisor", "receptor", "tipo_empresa", "dia", "mes", "anio"):
        agrupado = client.get("/api/v1/dashboard/desglose", params={"agrupar_por": grupo})
        assert agrupado.status_code == 200, agrupado.text
        assert sum(fila["expedientes"] for fila in agrupado.json()["filas"]) == 2

    opciones = client.get("/api/v1/dashboard/opciones")
    assert opciones.status_code == 200
    assert len(opciones.json()["emisores"]) == 1
    assert len(opciones.json()["receptores"]) == 1
    emisor_id = opciones.json()["emisores"][0]["id"]
    receptor_id = opciones.json()["receptores"][0]["id"]

    para_emisor = client.get("/api/v1/dashboard/resumen", params={"emisor_id": emisor_id})
    assert para_emisor.status_code == 200
    assert para_emisor.json()["expedientes_total"] == 2

    para_receptor = client.get("/api/v1/dashboard/desglose", params={"receptor_id": receptor_id})
    assert para_receptor.status_code == 200
    assert sum(f["expedientes"] for f in para_receptor.json()["filas"]) == 2

    sin_registros = client.get("/api/v1/dashboard/resumen", params={"mes": "2020-01"})
    assert sin_registros.status_code == 200
    assert sin_registros.json()["expedientes_total"] == 0
    assert sum(sin_registros.json()["documentos_pendientes"].values()) == 0
    for importe in sin_registros.json()["montos"]:
        assert float(importe["bancarizable"]) == 0
        assert float(importe["no_bancarizable"]) == 0

    opciones_vacias = client.get("/api/v1/dashboard/opciones", params={"mes": "2020-01"})
    assert opciones_vacias.status_code == 200
    assert opciones_vacias.json()["emisores"] == []
    assert opciones_vacias.json()["receptores"] == []

    assert client.get("/api/v1/dashboard/resumen", params={"mes": "2026-99"}).status_code == 422


def test_responsable_sin_cartera_no_ve_registros_ajenos(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura.xml", factura(numero="F001-00000915"))},
    )
    assert subida.status_code == 201, subida.text
    anterior = auth_prueba.contexto
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=anterior.cuenta_id,
        tenant_id=anterior.tenant_id,
        rol="RESPONSABLE",
        miembro_id=uuid.uuid4(),
        gestor_id=None,
        usuario_id=None,
        codigo="RESP-PRUEBA",
        nombre="Responsable de prueba",
        cambio_clave_obligatorio=False,
    )
    for endpoint in ("resumen", "desglose", "opciones"):
        respuesta = client.get(f"/api/v1/dashboard/{endpoint}")
        assert respuesta.status_code == 200, respuesta.text
        if endpoint == "resumen":
            assert respuesta.json()["expedientes_total"] == 0
        elif endpoint == "desglose":
            assert respuesta.json()["filas"] == []
        else:
            assert respuesta.json()["emisores"] == []
            assert respuesta.json()["receptores"] == []
