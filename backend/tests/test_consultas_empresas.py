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
