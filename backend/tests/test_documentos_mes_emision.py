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


def test_empresa_proveedora_y_cliente_se_filtran_independientemente(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura_empresas.xml", factura(numero="F001-00001992"))},
    )
    assert subida.status_code == 201, subida.text
    documento_id = subida.json()["id"]
    expediente_id = subida.json()["expediente_id"]
    auth_prueba.como_admin()

    parametros = {"empresa_emisora": "proveedor", "empresa_receptora": "cliente"}
    rutas = (
        "/api/v1/documentos",
        "/api/v1/expedientes",
        "/api/v1/expedientes/ids",
    )
    for ruta in rutas:
        respuesta = client.get(ruta, params=parametros)
        assert respuesta.status_code == 200, (ruta, respuesta.text)
        resultados = respuesta.json()
        esperado = documento_id if ruta.endswith("/documentos") else expediente_id
        assert any(
            (fila.get("id") if isinstance(fila, dict) else fila) == esperado
            for fila in resultados
        )

    para_control = {"desde": "2026-01-01", "hasta": "2026-12-31", **parametros}
    control = client.get("/api/v1/dashboard/secretaria-expedientes", params=para_control)
    assert control.status_code == 200, control.text
    assert any(fila["id"] == expediente_id for fila in control.json()["filas"])

    for campo in ("empresa_emisora", "empresa_receptora"):
        incorrecto = {**parametros, campo: "EMPRESA INEXISTENTE ZZ123"}
        documentos = client.get("/api/v1/documentos/resumen", params=incorrecto)
        assert documentos.status_code == 200, documentos.text
        assert documentos.json()["total_documentos"] == 0
        expedientes = client.get("/api/v1/expedientes/resumen", params=incorrecto)
        assert expedientes.status_code == 200, expedientes.text
        assert expedientes.json()["total_expedientes"] == 0
