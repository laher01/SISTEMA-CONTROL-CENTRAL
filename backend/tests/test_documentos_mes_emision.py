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
    clasificaciones = resumen.json()["distribucion"]
    assert sum(fila["cantidad"] for fila in clasificaciones) == resumen.json()["total_expedientes"]
    assert sum(float(fila["monto"]) for fila in clasificaciones) == float(
        resumen.json()["total_pen"]
    )

    resumen_vacio = client.get("/api/v1/documentos/resumen", params={"mes": "2026-10"})
    assert resumen_vacio.status_code == 200, resumen_vacio.text
    assert resumen_vacio.json()["total_documentos"] == 0
    assert resumen_vacio.json()["distribucion"] == []

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
            (fila.get("id") if isinstance(fila, dict) else fila) == esperado for fila in resultados
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


def test_orden_documental_respeta_paginacion_y_filtros(client: TestClient) -> None:
    documentos = []
    for numero, importe in (("2", "9.00"), ("10", "100.00")):
        respuesta = client.post(
            "/api/v1/documentos",
            files={
                "archivo": (
                    f"F001-{numero}.xml",
                    factura(numero=f"F001-{numero}", importe=importe, fecha="2026-09-21"),
                )
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        documentos.append(respuesta.json())

    for modulo in ("documentos", "expedientes", "registros"):
        ruta = f"/api/v1/{modulo}"
        filtros = (
            {"emisor": "PROVEEDOR"}
            if modulo == "registros"
            else {
                "empresa_emisora": "PROVEEDOR",
            }
        )
        for orden in ("monto", "correlativo"):
            for direccion, primero in (("asc", 0), ("desc", 1)):
                for pagina in (0, 1):
                    respuesta = client.get(
                        ruta,
                        params={
                            **filtros,
                            "orden": orden,
                            "direccion": direccion,
                            "limit": 1,
                            "offset": pagina,
                        },
                    )
                    assert respuesta.status_code == 200, respuesta.text
                    datos = respuesta.json()
                    filas = datos["filas"] if modulo == "registros" else datos
                    esperado = documentos[(primero + pagina) % 2]
                    clave = "id" if modulo == "documentos" else "expediente_id"
                    assert len(filas) == 1
                    assert (
                        filas[0].get("expediente_id" if modulo == "registros" else "id")
                        == esperado[clave]
                    )
                    if modulo == "registros":
                        assert datos["total_registros"] == 2

        for orden in (
            "gestor",
            "usuario",
            "responsable",
            "fecha_documento",
            "fecha_carga",
            "emisor",
            "receptor",
            "tipo_empresa",
        ):
            respuesta = client.get(ruta, params={**filtros, "orden": orden})
            assert respuesta.status_code == 200, respuesta.text
