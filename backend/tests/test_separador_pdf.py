import io

import pytest
from pypdf import PdfWriter

from app.services.procesamiento_documental import DocumentoNoProcesable
from app.services.separador_pdf import analizar_paquete, extraer_fragmento


def _paquete(paginas: list[str]) -> bytes:
    from pypdf.generic import (
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
    )

    salida = PdfWriter()
    for contenido in paginas:
        hoja = salida.add_blank_page(width=595, height=842)
        fuente = DictionaryObject(
            {
                NameObject("/F1"): DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                    }
                ),
            }
        )
        hoja[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fuente})
        lineas = contenido.splitlines()
        operadores = ["BT /F1 10 Tf 20 780 Td"]
        for linea in lineas:
            operadores.append(f"({linea}) Tj 0 -20 Td")
        operadores.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(operadores).encode("ascii"))
        hoja[NameObject("/Contents")] = salida._add_object(stream)
    memoria_final = io.BytesIO()
    salida.write(memoria_final)
    return memoria_final.getvalue()


def test_paquete_facturas_multiemisor_y_continuacion() -> None:
    pdf = _paquete(
        [
            "FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9050",
            "Anexo o segunda pagina de la factura precedente",
            "FACTURA ELECTRONICA\nRUC: 20615266796\nE001-2272",
            "FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9051",
        ]
    )
    partes = analizar_paquete(pdf)
    assert [(p.inicio, p.fin, p.serie, p.correlativo) for p in partes] == [
        (0, 2, "E001", "9050"),
        (2, 3, "E001", "2272"),
        (3, 4, "E001", "9051"),
    ]
    from pypdf import PdfReader

    assert len(PdfReader(io.BytesIO(extraer_fragmento(pdf, partes[0]))).pages) == 2


def test_paquete_incierto_no_se_divide() -> None:
    pdf = _paquete(["Anexo sin cabecera", "FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9050"])
    with pytest.raises(DocumentoNoProcesable):
        analizar_paquete(pdf)


def test_paquete_una_sola_factura_no_se_fragmenta() -> None:
    pdf = _paquete(["FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9050", "Segunda pagina"])
    with pytest.raises(DocumentoNoProcesable):
        analizar_paquete(pdf)


def test_paquete_cotizaciones_numeracion_comercial() -> None:
    pdf = _paquete(
        [
            "COTIZACION No. 00275-2026\nCLIENTE RUC 20538821374",
            "Anexo con condiciones comerciales y detalle de productos",
            "COTIZACION No. 074\nRUC 20615898598\nCLIENTE RUC 20538821374",
            "COTIZACION No. 076\nRUC 20615898598\nCLIENTE RUC 20538821374",
        ]
    )
    partes = analizar_paquete(pdf)
    assert [(p.inicio, p.fin, p.tipo, p.serie, p.correlativo) for p in partes] == [
        (0, 2, "COT", "COT", "00275-2026"),
        (2, 3, "COT", "COT", "074"),
        (3, 4, "COT", "COT", "076"),
    ]


def test_cotizacion_sin_numero_no_se_inventa() -> None:
    pdf = _paquete(
        [
            "COTIZACION\nCLIENTE RUC 20538821374",
            "COTIZACION No. 074\nRUC 20615898598",
        ]
    )
    with pytest.raises(DocumentoNoProcesable):
        analizar_paquete(pdf)


def test_normalizacion_numero_con_espacios() -> None:
    from app.services.separador_pdf import _cabecera

    cabecera = _cabecera("COTIZACION No. 00275 - 2026")
    assert cabecera is not None
    assert cabecera[2] == "00275-2026"


def test_importacion_selectiva_y_reimportacion_con_padre(client, session) -> None:
    from sqlalchemy import select

    from app.models import Documento, RelacionDocumento

    pdf = _paquete(
        [
            "COTIZACION No. 00198\\nPROVEEDOR A",
            "COTIZACION No. 00199\\nPROVEEDOR A",
        ]
    )

    def enviar(confirmar: bool, indices: str | None = None):
        datos = {"confirmar": str(confirmar).lower()}
        if indices is not None:
            datos["indices_documentos"] = indices
        return client.post(
            "/api/v1/documentos/paquete",
            data=datos,
            files={"archivo": ("cotizaciones.pdf", pdf, "application/pdf")},
        )

    vista = enviar(False)
    assert vista.status_code == 200
    assert vista.json()["total"] == 2
    primero = enviar(True, "0")
    assert primero.status_code == 200, primero.text
    assert primero.json()["total"] == 1
    segundo = enviar(True, "1")
    assert segundo.status_code == 200, segundo.text
    assert segundo.json()["total"] == 1
    repetido = enviar(True, "0")
    assert repetido.status_code == 200
    assert repetido.json()["duplicados"] == 1

    documentos = list(session.scalars(select(Documento)))
    padres = [d for d in documentos if d.tipo_documento == "OTRO"]
    hijos = [d for d in documentos if d.tipo_documento == "COT"]
    assert len(padres) == 1
    assert len(hijos) == 2
    relaciones = list(session.scalars(select(RelacionDocumento)))
    assert len(relaciones) == 2
    assert {r.destino_id for r in relaciones} == {d.id for d in hijos}
    assert {r.origen_id for r in relaciones} == {padres[0].id}


def test_reimportacion_semantica_pdf_distinto(client, session) -> None:
    from sqlalchemy import select

    from app.models import Documento

    original = _paquete(
        [
            "COTIZACION No. 0074\\nPROVEEDOR RUC 20615898598\\nCLIENTE RUC 20538821374",
            "COTIZACION No. 0075\\nPROVEEDOR RUC 20615898598\\nCLIENTE RUC 20538821374",
        ]
    )
    equivalente = _paquete(
        [
            "COTIZACION No. 0074\\nPROVEEDOR RUC 20615898598\\nCLIENTE RUC 20538821374\\nCOPIA",
            "COTIZACION No. 0076\\nPROVEEDOR RUC 20615898598\\nCLIENTE RUC 20538821374",
        ]
    )

    def importar(pdf: bytes):
        return client.post(
            "/api/v1/documentos/paquete",
            data={"confirmar": "true"},
            files={"archivo": ("paquete.pdf", pdf, "application/pdf")},
        )

    primero = importar(original)
    assert primero.status_code == 200, primero.text
    assert primero.json()["revision"] == 2
    segundo = importar(equivalente)
    assert segundo.status_code == 200, segundo.text
    assert segundo.json()["duplicados"] == 1
    assert segundo.json()["revision"] == 1
    cotizaciones = list(
        session.scalars(select(Documento).where(Documento.tipo_documento == "COT"))
    )
    assert len(cotizaciones) == 3
    assert len({d.huella_comercial for d in cotizaciones}) == 3
