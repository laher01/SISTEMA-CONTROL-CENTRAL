from fastapi.testclient import TestClient

from app.core.config import Settings
from app.services import nexus as nexus_service
from tests.xml import EMISOR, factura


def _subir(client: TestClient, numero: str, importe: str = "1500.00") -> dict[str, object]:
    respuesta = client.post(
        "/api/v1/documentos",
        files={
            "archivo": (
                numero + ".xml",
                factura(numero=numero, importe=importe, fecha="2026-10-01"),
            )
        },
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
    datos = respuesta.json()
    assert datos["asistente_activo"] is True
    assert datos["consulta_ruc_externa"] is False
    assert datos["busqueda_internet"] is False
    assert datos["motor_conversacional"] is False
    assert datos["knowledge_base"] is True
    assert datos["fuente_oficial_preferida"] == "SUNAT"


def test_nexus_responde_con_contexto_de_pantalla_y_knowledge_base(
    client: TestClient,
) -> None:
    _subir(client, "F001-00000905", "750.00")
    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "¿Qué está pasando en esta pantalla y qué debería revisar?",
            "ruta": "/empresas?vista=proveedores",
            "expediente_id": None,
            "historial": [],
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["accion"] == "CONTEXTO_NEXUS"
    assert datos["seccion"] == "EMPRESAS"
    assert datos["motor"] == "CONTEXTUAL"
    assert datos["llm_usado"] is False
    assert any(fuente["tipo"] == "KNOWLEDGE_BASE" for fuente in datos["fuentes"])
    assert "EMPRESAS" in datos["respuesta"]


def test_nexus_motor_conversacional_recibe_contexto_historial_y_conocimiento(
    client: TestClient,
    settings: Settings,
    monkeypatch,
) -> None:
    settings.nexus_llm_url = "https://llm.example.test/chat"
    settings.nexus_llm_model = "nexus-test"
    capturado: dict[str, object] = {}

    def falso_http(
        url: str,
        *,
        method: str,
        token: str | None,
        timeout: int,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        capturado["url"] = url
        capturado["payload"] = payload or {}
        return {"choices": [{"message": {"content": "Respuesta contextual de prueba."}}]}

    monkeypatch.setattr(nexus_service, "_http_json", falso_http)

    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "¿Y qué significa eso para este mes?",
            "ruta": "/pagos",
            "expediente_id": None,
            "historial": [
                {"autor": "usuario", "texto": "Explícame los pedidos de Gerencia"},
                {"autor": "nexus", "texto": "Los pedidos controlan lo solicitado y ejecutado."},
            ],
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["respuesta"] == "Respuesta contextual de prueba."
    assert datos["llm_usado"] is True
    assert datos["motor"] == "LLM_CONTEXTUAL"
    assert datos["seccion"] == "PAGOS"

    payload = capturado["payload"]
    assert isinstance(payload, dict)
    mensajes = payload["messages"]
    assert isinstance(mensajes, list)
    textos = [item["content"] for item in mensajes if isinstance(item, dict)]
    assert any("CONTEXTO AUTORIZADO" in texto for texto in textos)
    assert any("BASE DE CONOCIMIENTO" in texto for texto in textos)
    assert any("Explícame los pedidos de Gerencia" in texto for texto in textos)
