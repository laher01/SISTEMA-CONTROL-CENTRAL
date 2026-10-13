"""El mes documental se calcula por emisión y modifica lista y resumen."""

from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba
from tests.xml import factura


def test_documentos_filtra_mes_emision_y_no_mes_de_carga(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={
            "archivo": (
                "factura_mes_2026.xml",
                factura(numero="F001-00001991", fecha="2026-09-21"),
            )
        },
    )
    assert subida.status_code == 201, subida.text
    documento_id = subida.json()["id"]
    auth_prueba.como_admin()

    septiembre = client.get("/api/v1/documentos", params={"mes": "2026-09"})
    assert septiembre.status_code == 200, septiembre.text
    assert any(item["id"] == documento_id for item in septiembre.json())

    octubre = client.get("/api/v1/documentos", params={"mes": "2026-10"})
    assert octubre.status_code == 200, octubre.text
    assert not any(item["id"] == documento_id for item in octubre.json())

    resumen = client.get("/api/v1/documentos/resumen", params={"mes": "2026-09"})
    assert resumen.status_code == 200, resumen.text
    assert resumen.json()["total_documentos"] >= 1

    resumen_vacio = client.get("/api/v1/documentos/resumen", params={"mes": "2026-10"})
    assert resumen_vacio.status_code == 200, resumen_vacio.text
    assert resumen_vacio.json()["total_documentos"] == 0

    invalido = client.get("/api/v1/documentos", params={"mes": "2026-13"})
    assert invalido.status_code == 422
