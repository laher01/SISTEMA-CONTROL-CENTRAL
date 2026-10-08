from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba
from tests.xml import factura


def test_filtros_a_b_registros_documentos_expedientes(
    client: TestClient, auth_prueba: AuthPrueba
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

    auth_prueba.como_admin()
    for ruc, categoria in [("20500000002", "A"), ("20600000003", "B")]:
        respuesta = client.patch(
            f"/api/v1/empresas/{emisores[ruc]}",
            json={"clasificacion_proveedor": categoria},
        )
        assert respuesta.status_code == 200, respuesta.text

    for categoria, esperado in [("A", 2), ("B", 1)]:
        registros = client.get("/api/v1/registros", params={"tipo_empresa": categoria})
        assert registros.status_code == 200, registros.text
        assert registros.json()["total_registros"] == esperado
        assert all(f["tipo_empresa"] == categoria for f in registros.json()["filas"])

        for ruta in ["/api/v1/documentos", "/api/v1/expedientes"]:
            respuesta = client.get(ruta, params={"tipo_empresa": categoria})
            assert respuesta.status_code == 200, respuesta.text
            assert len(respuesta.json()) == esperado

    for ruta in ["/api/v1/registros", "/api/v1/documentos", "/api/v1/expedientes"]:
        assert client.get(ruta, params={"tipo_empresa": "C"}).status_code == 422
