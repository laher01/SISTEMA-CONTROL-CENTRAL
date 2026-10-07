from fastapi.testclient import TestClient

from tests.xml import EMISOR, factura


def _subir(client: TestClient, numero: str, importe: str = "1500.00") -> dict[str, object]:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": (numero + ".xml", factura(numero=numero, importe=importe))},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_nexus_revisa_expediente_actual(client: TestClient) -> None:
    documento = _subir(client, "F001-00000901", "1500.00")
    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "¿Qué falta en este expediente?",
            "ruta": f"/expedientes/{documento['expediente_id']}",
            "expediente_id": documento["expediente_id"],
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["accion"] == "REVISAR_EXPEDIENTE"
    assert datos["datos"]["faltantes"] == []
    assert "debajo de S/ 2,000" in datos["respuesta"]


def test_nexus_calcula_compras_del_mes(client: TestClient) -> None:
    _subir(client, "F001-00000902", "100.00")
    _subir(client, "F001-00000903", "200.00")

    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "¿Cuánto llevo comprado este mes?",
            "ruta": "/registros",
            "expediente_id": None,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["accion"] == "TOTAL_COMPRAS_MES"
    assert datos["datos"]["totales"]["PEN"]["registros"] == 2
    assert datos["datos"]["totales"]["PEN"]["total"] == "300.00"


def test_nexus_consulta_ruc_local_sin_inventar_internet(client: TestClient) -> None:
    _subir(client, "F001-00000904", "500.00")

    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": f"Verifica el RUC {EMISOR}",
            "ruta": "/registros",
            "expediente_id": None,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["accion"] == "VERIFICAR_RUC"
    assert datos["datos"]["razon_local"] == "PROVEEDOR SAC"
    assert datos["internet_usado"] is False
    assert datos["requiere_configuracion_externa"] is True


def test_nexus_estado_informa_integraciones_pendientes(client: TestClient) -> None:
    respuesta = client.get("/api/v1/nexus/estado")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "asistente_activo": True,
        "consulta_ruc_externa": False,
        "busqueda_internet": False,
        "fuente_oficial_preferida": "SUNAT",
    }
