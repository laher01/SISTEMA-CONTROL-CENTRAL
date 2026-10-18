"""Consultas factuales NEXUS sobre ítems: sin inventar productos o acceder a otros tenants."""

from fastapi.testclient import TestClient

from app.services.nexus_items import (
    _contiene_termino,
    _diesel_en_factura_procesada,
    _grupos_coincidentes,
    consulta_items_solicitada,
)
from tests.xml import factura


def test_intencion_items() -> None:
    assert consulta_items_solicitada("DE PETROLEO CUANTOS SON") == ("producto", "petroleo")
    assert consulta_items_solicitada("DIME ALGUNO TIENE VIVERES O HIELO") == (
        "producto",
        "hielo,viveres",
    )
    assert consulta_items_solicitada("CUANTAS CONTIENEN CUADERNOS") == ("producto", "cuadernos")
    assert consulta_items_solicitada("A QUE CLIENTES LE HAN EMITIDO") == ("clientes", "")
    assert consulta_items_solicitada("hola") is None


def test_nexus_consulta_items_reales_del_xml(client: TestClient) -> None:
    subido = client.post(
        "/api/v1/documentos",
        files={
            "archivo": (
                "F001-00009001.xml",
                factura(numero="F001-00009001", importe="1500.00", fecha="2026-10-01"),
            )
        },
    )
    assert subido.status_code == 201, subido.text
    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={"mensaje": "cuántas facturas contienen cuadernos", "ruta": "/"},
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["accion"] == "CONSULTAR_ITEMS"
    assert datos["motor"] == "ESPECIALISTA_ITEMS"
    assert "motor conversacional externo" not in datos["respuesta"]


def test_consultas_escritas_con_errores_y_productos_nuevos() -> None:
    assert consulta_items_solicitada("dime cuantas facrturas de petrpoleo tenemos") == (
        "producto",
        "petroleo",
    )
    assert consulta_items_solicitada("y de llantas hay") == ("producto", "llantas")
    assert consulta_items_solicitada("y agua y sporade") == ("producto", "agua,sporade")
    assert consulta_items_solicitada("facturas de lubricantes") == ("libre", "lubricantes")


def test_busqueda_no_confunde_palabras_compuestas() -> None:
    assert consulta_items_solicitada("¿Cuántas facturas de aguardiente?") == (
        "libre",
        "aguardiente",
    )
    assert _contiene_termino("aguardiente mineral", "agua") is False
    assert _contiene_termino("agua mineral", "agua") is True
    assert _contiene_termino("aceite para neumáticos", "neumatico") is False
    assert _contiene_termino("neumaticos", "neumatico") is True
    assert consulta_items_solicitada("¿Y agua y Sporade?") == ("producto", "agua,sporade")


def test_desglose_de_productos_sin_contar_subcadenas() -> None:
    catalogo = {"agua": ("agua",), "sporade": ("sporade",)}
    grupos = ["agua", "sporade"]
    assert _grupos_coincidentes("AGUA SPORADE", grupos, catalogo) == grupos
    assert _grupos_coincidentes("AGUARDIENTE", grupos, catalogo) == []
    assert _grupos_coincidentes("SPORADE", grupos, catalogo) == ["sporade"]


def test_consulta_libre_elimina_muletillas_sin_perder_producto() -> None:
    assert consulta_items_solicitada("¿Y de tornillos hay?") == ("libre", "tornillos")
    assert consulta_items_solicitada("¿Facturas de lubricantes tenemos?") == (
        "libre",
        "lubricantes",
    )
    assert consulta_items_solicitada("¿Facturas de sal industrial?") == (
        "libre",
        "sal industrial",
    )


def test_diesel_en_pdf_procesado_requiere_linea_y_tipo_factura() -> None:
    texto = (
        "FACTURA ELECTRÓNICA F109 Nº 0016494 CANTIDAD CODIGO U.M DESCRIPCION "
        "49.499 09 GLL DIESEL B5 S50 20.31 23.96 1005.08"
    )
    assert _diesel_en_factura_procesada({"procesamiento_documental": {"texto": texto}})
    assert not _diesel_en_factura_procesada(
        {"procesamiento_documental": {"texto": "FACTURA combustibles DIESEL B5 S50"}}
    )
    assert not _diesel_en_factura_procesada(
        {"procesamiento_documental": {"texto": "GLL DIESEL B5 S50"}}
    )
    assert not _diesel_en_factura_procesada({})
