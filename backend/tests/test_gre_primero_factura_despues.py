"""Conciliación de un expediente provisional desde GRE remitente."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes import documentos as documentos_routes
from app.services.procesamiento_documental import ResultadoProcesamiento, sugerir_tipo
from tests.test_api import pdf_vacio, subir
from tests.xml import EMISOR, RECEPTOR, factura


def test_guia_pdf_primero_factura_xml_despues_sin_ocr_repetido(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    texto = (
        "GUÍA DE REMISIÓN REMITENTE\n"
        f"Datos del Destinatario: RUC N° {RECEPTOR}\n"
        "Documentos Relacionados:\n"
        f"Factura N° F001 175 - RUC N° {EMISOR}"
    )
    ejecuciones = [0]

    def procesar_pdf(*_args: object) -> ResultadoProcesamiento:
        ejecuciones[0] += 1
        return ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
        )

    monkeypatch.setattr(documentos_routes, "procesar", procesar_pdf)
    guia_doc = subir(client, "guia-primero.pdf", pdf_vacio())
    assert guia_doc["tipo_documento"] == "GRR"
    assert guia_doc["expediente_id"] is None

    listado = client.get("/api/v1/documentos/provisionales-gre")
    assert listado.status_code == 200, listado.text
    assert len(listado.json()) == 1
    assert listado.json()[0]["factura"] == "F001-175"
    assert listado.json()[0]["estado"] == "PENDIENTE_FACTURA"
    assert listado.json()[0]["monto_contabilizable"] == "0.00"
    assert listado.json()[0]["cliente_autorizado"] is False

    factura_doc = subir(client, "factura-despues.xml", factura(numero="F001-00000175"))
    assert factura_doc["expediente_id"] is not None
    guia_final = client.get(f"/api/v1/documentos/{guia_doc['id']}")
    assert guia_final.status_code == 200, guia_final.text
    assert guia_final.json()["expediente_id"] == factura_doc["expediente_id"]
    assert guia_final.json()["tipo_documento"] == "GRR"
    assert guia_final.json()["estado"] == "RELACIONADO"
    assert ejecuciones[0] == 1
    assert client.get("/api/v1/documentos/provisionales-gre").json() == []


def test_referencia_no_coincidente_no_relaciona_otra_factura(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    texto = (
        "GUÍA DE REMISIÓN REMITENTE\n"
        f"Datos del Destinatario: RUC N° {RECEPTOR}\n"
        "Documentos Relacionados:\n"
        "Factura N° F001 175 - RUC N° 10421885627"
    )
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
        ),
    )
    guia_doc = subir(client, "gre.pdf", pdf_vacio())
    factura_doc = subir(client, "factura.xml", factura(numero="F001-00000175"))
    assert factura_doc["expediente_id"] is not None
    assert client.get(f"/api/v1/documentos/{guia_doc['id']}").json()["expediente_id"] is None


def test_gre_sunat_con_referencia_impresa_ambigua_no_inventa_factura(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ejemplo visual: la GRE menciona 'Factura N° 0002 8',
    # que no permite identificar con seguridad serie y correlativo.
    texto = (
        "GUÍA DE REMISIÓN ELECTRÓNICA REMITENTE\n"
        "MARY GREIS E.I.R.L. RUC 20550466385\n"
        "GRE E001-00000910\n"
        "Datos del Destinatario: INVERSIONES Y NEGOCIACIONES MAREUF E.I.R.L. "
        "REGISTRO ÚNICO DE CONTRIBUYENTES N° 20538821374\n"
        "Documentos Relacionados:\n"
        "Factura N° 0002 8 - RUC N° 20550466385"
    )
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
            lambda *_: ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
            ),
    )
    guia = subir(client, "gre-sunat.pdf", pdf_vacio())
    assert guia["tipo_documento"] == "GRR"
    assert guia["expediente_id"] is None
    assert guia["estado"] != "RELACIONADO"
    respuesta = client.get(f"/api/v1/documentos/{guia['id']}")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.status_code == 200, respuesta.text
    assert (
        respuesta.json()["datos_extraidos"]["gre_factura_pendiente"]["importe_contabilizable"]
        == "0.00"
    )
    resumen = client.get("/api/v1/expedientes/resumen")
    resumen = client.get("/api/v1/expedientes/resumen")
    assert resumen.status_code == 200
    assert resumen.json()["total_expedientes"] == 0
