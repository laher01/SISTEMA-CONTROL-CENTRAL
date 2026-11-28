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
