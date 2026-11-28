from dataclasses import replace
from io import BytesIO
from unittest.mock import patch

import httpx
import pytest
from openpyxl import Workbook  # type: ignore[import-untyped]

from app.services import consultas_empresas as ce


def test_ssco_busca_ruc_del_sujeto_y_no_del_representante():
    libro = Workbook()
    hoja = libro.active
    assert hoja is not None
    hoja.title = "Hoja1"
    hoja.append(
        [
            "RUC",
            "Razón social",
            "Domicilio",
            "Resolución",
            "Emisión",
            "Firme",
            "RUC representante",
            "Representante",
            "Publicación",
        ]
    )
    hoja.append(
        [
            "20000000001",
            "Proveedor",
            "—",
            "001",
            "2026-01-01",
            "2026-01-02",
            "20000000002",
            "Representante",
            "2026-01-31",
        ]
    )
    archivo = BytesIO()
    libro.save(archivo)
    libro.close()
    assert set(ce.leer_padron(archivo.getvalue())) == {"20000000001"}


def test_coactiva_suma_y_cuenta_registros():
    peticion = httpx.Request("POST", ce.FUENTE_COACTIVA)
    with patch.object(
        ce.httpx,
        "post",
        return_value=httpx.Response(
            200,
            request=peticion,
            json={"success": True, "data": [{"monto": "0.10"}, {"monto": "0.20"}]},
        ),
    ):
        assert ce.consultar_coactiva("20000000001", "prueba") == {
            "estado": "Con deuda",
            "monto": "0.30",
            "registros": 2,
        }


def test_coactiva_rechaza_resultados_fallidos():
    with (
        patch.object(
            ce.httpx,
            "post",
            return_value=httpx.Response(
                200,
                request=httpx.Request("POST", ce.FUENTE_COACTIVA),
                json={"success": False},
            ),
        ),
        pytest.raises(ValueError),
    ):
        ce.consultar_coactiva("20000000001", "prueba")


def test_coactiva_404_documentado_y_503_son_distintos():
    peticion = httpx.Request("POST", ce.FUENTE_COACTIVA)
    with patch.object(
        ce.httpx,
        "post",
        side_effect=[
            httpx.Response(
                404, request=peticion, json={"success": False, "code": "document_not_found"}
            ),
            httpx.Response(
                503, request=peticion, json={"success": False, "code": "upstream_unavailable"}
            ),
        ],
    ):
        assert ce.consultar_coactiva("20000000001", "prueba")["registros"] == 0
        with pytest.raises(httpx.HTTPStatusError):
            ce.consultar_coactiva("20000000001", "prueba")


def test_ficha_sunat_separa_condicion_del_domicilio():
    ruc = "20000000001"
    with patch.object(ce.httpx, "post") as post:
        post.return_value = httpx.Response(
            200,
            request=httpx.Request("POST", f"{ce.BASE_APIPERU}/ruc-sunat"),
            json={"success": True, "data": {"ruc": ruc, "estado": "ACTIVO", "condicion": "HABIDO"}},
        )
        assert ce.consultar_ficha(ruc, "prueba", "sunat")["condicion"] == "HABIDO"
        assert post.call_args.args[0].endswith("/ruc-sunat")


def test_responsable_puede_consultar_empresas(client, auth_prueba):
    auth_prueba.contexto = replace(auth_prueba.contexto, rol="RESPONSABLE")
    with patch.object(ce, "consultar_ssco", return_value={"estado": "No figura"}):
        respuesta = client.get("/api/v1/empresas/consultas/ssco/20000000001")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "No figura"


def test_solo_admin_puede_rotar_token_y_la_api_no_lo_devuelve(client, auth_prueba, settings):
    from cryptography.fernet import Fernet

    ruta = "/api/v1/empresas/consultas/configuracion"
    settings.consultas_empresas_encryption_key = Fernet.generate_key().decode()
    datos = {"api_token": "token-de-prueba-1", "endpoints": ce.ENDPOINTS}
    assert client.get(ruta).status_code == 403
    assert client.patch(ruta, json=datos).status_code == 403
    auth_prueba.como_admin()
    respuesta = client.patch(ruta, json=datos)
    assert respuesta.status_code == 200
    assert respuesta.json()["token_configurado"]
    assert datos["api_token"] not in respuesta.text
    assert datos["api_token"] not in client.get(ruta).text
    datos["api_token"] = "token-de-prueba-2"
    assert client.patch(ruta, json=datos).status_code == 200
    with patch.object(ce, "consultar_coactiva", return_value={"estado": "Sin deuda"}) as coactiva:
        assert client.get("/api/v1/empresas/consultas/coactiva/20000000001").status_code == 200
        coactiva.assert_called_once_with("20000000001", datos["api_token"], ce.FUENTE_COACTIVA)


def test_configuracion_rechaza_destino_ajeno(client, auth_prueba):
    auth_prueba.como_admin()
    respuesta = client.patch(
        "/api/v1/empresas/consultas/configuracion",
        json={
            "endpoints": {**ce.ENDPOINTS, "coactiva": "https://otro.example/"},
        },
    )
    assert respuesta.status_code == 422


def test_ficha_ruc_legacy_consulta_por_get_y_muestra_domicilio():
    ruc = "20131312955"
    url = ce.FICHA_RUC_LEGACY
    respuesta = httpx.Response(
        200,
        request=httpx.Request("GET", f"{url}{ruc}"),
        json={"success": True, "data": {"ruc": ruc, "direccion": "Av. Garcilaso"}},
    )
    with patch.object(ce.httpx, "get", return_value=respuesta) as consulta:
        ficha = ce.consultar_ficha(ruc, "prueba", "sunat", url)
    assert consulta.call_args.args == (f"{url}{ruc}",)
    assert ficha["direccion_completa"] == "Av. Garcilaso"
    assert ficha["fuente"] == "Ficha básica de APIPERU"


def test_configuracion_acepta_formato_dotenv_de_la_pc(client, auth_prueba, settings):
    from cryptography.fernet import Fernet

    auth_prueba.como_admin()
    settings.consultas_empresas_encryption_key = Fernet.generate_key().decode()
    endpoint = "https://apiperu.dev/api/ruc_deuda_coactiva/"
    ruta = "/api/v1/empresas/consultas"
    respuesta = client.patch(
        f"{ruta}/configuracion",
        json={
            "api_token": " 'token-de-prueba' ",
            "endpoints": {**ce.ENDPOINTS, "coactiva": f" '{endpoint}' "},
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["endpoints"]["coactiva"] == endpoint
    with patch.object(ce, "consultar_coactiva", return_value={"estado": "Con deuda"}) as consulta:
        assert client.get(f"{ruta}/coactiva/20601865484").status_code == 200
    consulta.assert_called_once_with("20601865484", "token-de-prueba", endpoint)
