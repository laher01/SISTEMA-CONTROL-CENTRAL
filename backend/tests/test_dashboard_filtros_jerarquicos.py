"""Regresiones: Dashboard comparte alcance para tarjetas, tabla y opciones."""
from fastapi.testclient import TestClient

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

    opciones = client.get("/api/v1/dashboard/opciones")
    assert opciones.status_code == 200
    assert len(opciones.json()["emisores"]) == 1
    assert len(opciones.json()["receptores"]) == 1
    emisor_id = opciones.json()["emisores"][0]["id"]
    receptor_id = opciones.json()["receptores"][0]["id"]

    para_emisor = client.get("/api/v1/dashboard/resumen", params={"emisor_id": emisor_id})
    assert para_emisor.status_code == 200
    assert para_emisor.json()["expedientes_total"] == 2

    para_receptor = client.get(
        "/api/v1/dashboard/desglose", params={"receptor_id": receptor_id}
    )
    assert para_receptor.status_code == 200
    assert sum(f["expedientes"] for f in para_receptor.json()["filas"]) == 2

    sin_registros = client.get("/api/v1/dashboard/resumen", params={"mes": "2020-01"})
    assert sin_registros.status_code == 200
    assert sin_registros.json()["expedientes_total"] == 0
    for importe in sin_registros.json()["montos"]:
        assert float(importe["bancarizable"]) == 0
        assert float(importe["no_bancarizable"]) == 0

    opciones_vacias = client.get("/api/v1/dashboard/opciones", params={"mes": "2020-01"})
    assert opciones_vacias.status_code == 200
    assert opciones_vacias.json()["emisores"] == []
    assert opciones_vacias.json()["receptores"] == []

    assert client.get("/api/v1/dashboard/resumen", params={"mes": "2026-99"}).status_code == 422
