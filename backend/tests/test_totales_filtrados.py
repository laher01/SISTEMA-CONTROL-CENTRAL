from decimal import Decimal

from fastapi.testclient import TestClient

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
