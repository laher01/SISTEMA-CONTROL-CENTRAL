from fastapi.testclient import TestClient

from tests.xml import factura


def test_dashboard_filtra_clasificacion_proveedor(
    client: TestClient,
) -> None:
    for numero, emisor in [
        ("F001-00000123", "20500000002"),
        ("F001-00000124", "20500000002"),
        ("F002-00000125", "20600000003"),
    ]:
        respuesta = client.post(
            "/api/v1/documentos",
            files={"archivo": (numero + ".xml", factura(numero=numero, emisor=emisor))},
        )
        assert respuesta.status_code == 201, respuesta.text

    empresas = client.get("/api/v1/empresas")
    assert empresas.status_code == 200
    emisores = {e["ruc"]: e["id"] for e in empresas.json()}

    for ruc, categoria in [("20500000002", "A"), ("20600000003", "B")]:
        respuesta = client.patch(
            f"/api/v1/empresas/{emisores[ruc]}",
            json={"clasificacion_proveedor": categoria},
        )
        assert respuesta.status_code == 200, respuesta.text

    for categoria, esperado in [("A", 2), ("B", 1)]:
        respuesta = client.get(
            "/api/v1/dashboard/desglose",
            params={"tipo_empresa": categoria, "agrupar_por": "emisor"},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert sum(f["expedientes"] for f in respuesta.json()["filas"]) == esperado

    todos = client.get("/api/v1/dashboard/desglose")
    assert sum(f["expedientes"] for f in todos.json()["filas"]) == 3
    assert client.get("/api/v1/dashboard/desglose", params={"tipo_empresa": "C"}).status_code == 422
