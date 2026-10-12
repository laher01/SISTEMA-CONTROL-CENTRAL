"""Regresiones: visibilidad configurable y trazabilidad de fechas de Secretaría."""

from dataclasses import replace
from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba
from tests.xml import factura


def test_menu_secretaria_se_configura_y_se_aplica_en_api(
    client: TestClient, auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()
    configuracion = client.get("/api/v1/configuracion/permisos/secretaria")
    assert configuracion.status_code == 200, configuracion.text
    assert configuracion.json() == {
        "registros": True,
        "control_documental": True,
        "documentos": True,
        "expedientes": True,
    }

    for permiso in (
        "SECRETARIA_MENU_REGISTROS",
        "SECRETARIA_MENU_CONTROL_DOCUMENTAL",
        "SECRETARIA_MENU_DOCUMENTOS",
    ):
        actualizacion = client.put(
            "/api/v1/configuracion/permisos",
            json={"rol": "SECRETARIA", "permiso": permiso, "habilitado": False},
        )
        assert actualizacion.status_code == 200, actualizacion.text

    auth_prueba.contexto = replace(auth_prueba.contexto, rol="SECRETARIA")
    estado = client.get("/api/v1/configuracion/permisos/secretaria")
    assert estado.status_code == 200, estado.text
    assert estado.json() == {
        "registros": False,
        "control_documental": False,
        "documentos": False,
        "expedientes": True,
    }
    assert client.get("/api/v1/registros").status_code == 403
    assert client.get("/api/v1/documentos").status_code == 403
    assert client.get("/api/v1/documentos/resumen").status_code == 403
    assert client.get("/api/v1/dashboard/secretaria-expedientes").status_code == 403
    assert client.get("/api/v1/expedientes").status_code == 200
    # La jerarquía sigue siendo necesaria en Expedientes aunque Registros esté oculto.
    assert client.get("/api/v1/registros/opciones").status_code == 200


def test_documento_busca_correlativo_y_expone_fecha_carga(
    client: TestClient, auth_prueba: AuthPrueba,
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("fecha_correlativo.xml", factura(numero="F001-00000989"))},
    )
    assert subida.status_code == 201, subida.text
    documento = subida.json()
    assert documento["created_at"]
    auth_prueba.como_admin()
    serie = documento["serie"]
    numero = documento["correlativo"]
    assert serie and numero
    query = {"serie_correlativo": f"{serie}-{numero}"}
    lista = client.get("/api/v1/documentos", params=query)
    assert lista.status_code == 200, lista.text
    assert any(fila["id"] == documento["id"] for fila in lista.json())
    resumen = client.get("/api/v1/documentos/resumen", params=query)
    assert resumen.status_code == 200, resumen.text
    assert resumen.json()["total_documentos"] >= 1
    ninguna = client.get(
        "/api/v1/documentos", params={"serie_correlativo": "ZZZ-99999999"}
    )
    assert ninguna.status_code == 200, ninguna.text
    assert ninguna.json() == []
    if documento["fecha_emision"]:
        por_fecha = client.get(
            "/api/v1/documentos",
            params={**query, "fecha_emision": documento["fecha_emision"]},
        )
        assert por_fecha.status_code == 200, por_fecha.text
        assert any(fila["id"] == documento["id"] for fila in por_fecha.json())

    if documento["expediente_id"]:
        exp = client.get("/api/v1/expedientes")
        assert exp.status_code == 200, exp.text
        fila = next(
            fila for fila in exp.json() if fila["id"] == documento["expediente_id"]
        )
        assert fila["fecha_carga"] == documento["created_at"]
        registros = client.get("/api/v1/registros")
        assert registros.status_code == 200, registros.text
        registro = next(
            fila
            for fila in registros.json()["filas"]
            if fila["expediente_id"] == documento["expediente_id"]
        )
        assert registro["fecha_carga"] == documento["created_at"]
        tablero = client.get(
            "/api/v1/dashboard/secretaria-expedientes",
            params={"desde": date(2025, 1, 1), "hasta": date(2027, 12, 31)},
        )
        assert tablero.status_code == 200, tablero.text
        control = next(
            fila
            for fila in tablero.json()["filas"]
            if fila["id"] == documento["expediente_id"]
        )
        assert control["fecha_carga"] == documento["created_at"]
