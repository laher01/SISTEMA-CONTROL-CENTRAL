"""Regresión de identidad fiscal y separación de facturas y operaciones bancarias."""

import pytest

from app.services.extraccion_campos import extraer_campos
from app.services.facturas_estaciones import extraer_factura_estacion


@pytest.mark.parametrize(
    ("numero", "receptor", "ruc_cliente", "total"),
    [
        ("0016490", "INVERSIONES BORISO E.I.R.L.", "20605535098", "1750.00"),
        ("0016491", "B2C MUSA E.I.R.L.", "20614966174", "1850.00"),
        ("0016492", "INVERSIONES Y NEGOCIOS HERNANDEZ E.I.R.L.", "20478053763", "1850.00"),
        ("0016493", "FRUTTI DEL PAESE E.I.R.L.", "20611909234", "1750.00"),
        ("0016494", "CORPORACION LATINOAMERICANO EL NORTE E.I.R.L.", "20524049245", "1186.00"),
        ("0016495", "FRUTTI DEL PAESE E.I.R.L.", "20611909234", "1950.00"),
        ("0016496", "INVERSIONES BORISO E.I.R.L.", "20605535098", "1870.00"),
        ("0016497", "INVERSIONES Y NEGOCIACIONES REQUE E.I.R.L.", "20538820050", "1915.00"),
        ("0016498", "B2C MUSA E.I.R.L.", "20614966174", "1900.00"),
        ("0016499", "CORPORACION LATINOAMERICANO EL NORTE E.I.R.L.", "20524049245", "1949.00"),
    ],
)
def test_escorpio_serie_ruc_cliente_y_total(
    numero: str, receptor: str, ruc_cliente: str, total: str
) -> None:
    texto = (
        "INVERSIONES Y ASESORAMIENTO ESCORPIO SAC  R.U.C. N° 20516453835\n"
        f"FACTURA ELECTRÓNICA F109 Nº {numero}\n"
        f"SEÑOR(ES) : {receptor}     RUC : {ruc_cliente}\n"
        "2026-10-02 2026-10-02 SOL\n"
        f"IMPORTE TOTAL S/ {total}\nwww.facturacion.jadal.pe"
    )
    datos = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert datos is not None
    c = datos["campos"]
    assert c["serie"]["valor"] == "F109"
    assert c["correlativo"]["valor"] == str(int(numero))
    assert c["ruc_emisor"]["valor"] == "20516453835"
    assert c["ruc_receptor"]["valor"] == ruc_cliente
    assert c["razon_social_receptor"]["valor"] == receptor
    assert c["importe_total"]["valor"] == total


def test_jabsa_ticket_factura_y_total() -> None:
    texto = (
        "SERVICENTRO JABSA S.A\nRUC : 20374914201\n"
        "FACTURA DE VENTA ELECTRÓNICA\nF003-00004475\n"
        "Fecha Emision : 15/10/2026\n"
        "Cliente : INVERSIONES Y NEGOCIACIONES MAREUF E.I\n"
        "RUC : 20538821374  Placa :\n"
        "OP.GRAVADAS S/ 2959.32\nIGV S/ 532.68\n"
        "DESCUENTO S 0.00 TOTAL S/ 3492.00\n"
        "Representación impresa de la BOLETA DE VENTA ELECTRONICA"
    )
    campos = extraer_campos(texto, "TEXTO_PDF", 1.0)["campos"]
    assert campos["serie"]["valor"] == "F003"
    assert campos["correlativo"]["valor"] == "4475"
    assert campos["ruc_emisor"]["valor"] == "20374914201"
    assert campos["ruc_receptor"]["valor"] == "20538821374"
    assert campos["importe_total"]["valor"] == "3492.00"


def test_transferencia_bcp_nunca_es_factura() -> None:
    texto = "BCP\n¡Transferencia exitosa!\nS/ 10,160.00\nNúmero de operación 03857359"
    assert extraer_factura_estacion(texto) == {}


def test_texto_pypdf_escorpio_fragmentado() -> None:
    texto = (
        "INVERSIONES Y ASESORAMIENTO ESCORPIO\nSAC\n"
        "Página Web: www.facturacion.jadal.pe\n"
        "R.U.C. N° 20516453835\nFACTURA ELECTRÓNICA\nF109  Nº 0016490\n"
        "SEÑOR(ES)\n: INVERSIONES BORISO E.I.R.L.\n"
        "DIRECCIÖN\n: LIMA\nRUC\n: 20605535098\n"
        "FECHA DE EMISIÓN\n2026-10-02\n"
        "IMPORTE TOTAL\nS/\n1,750.00"
    )
    campos = extraer_campos(texto, "TEXTO_PDF", 1.0)["campos"]
    assert campos["serie"]["valor"] == "F109"
    assert campos["correlativo"]["valor"] == "16490"
    assert campos["ruc_receptor"]["valor"] == "20605535098"
    assert campos["razon_social_receptor"]["valor"] == "INVERSIONES BORISO E.I.R.L."
    assert campos["importe_total"]["valor"] == "1750.00"


def test_texto_pypdf_jabsa_desordenado() -> None:
    texto = (
        "F003-00004475\nFACTURA DE VENTA ELECTRÓNICA\n"
        ": 15/10/2026Fecha Emision\nSERVICENTRO JABSA S.A\n"
        "RUC : 20374914201\n"
        "S/TOTAL\n532.68S/IGV\nOP.GRAVADAS S/ 2959.32\n3492.00\n"
        "Cliente\nRUC\n:\n:\n:\nCAJERO 2 PUCUSANA\n"
        "INVERSIONES Y NEGOCIACIONES MAREUF E.I\n20538821374\n"
    )
    campos = extraer_campos(texto, "TEXTO_PDF", 1.0)["campos"]
    assert campos["ruc_emisor"]["valor"] == "20374914201"
    assert campos["ruc_receptor"]["valor"] == "20538821374"
    assert campos["fecha_emision"]["valor"] == "2026-10-15"
    assert campos["importe_total"]["valor"] == "3492.00"


def test_ticket_con_factura_y_boleta_contradictorias_requiere_revision() -> None:
    texto = (
        "SERVICENTRO JABSA S.A\nRUC : 20374914201\n"
        "FACTURA DE VENTA ELECTRÓNICA\nF003-00004475\n"
        "Fecha Emision : 15/10/2026\n"
        "Cliente : INVERSIONES Y NEGOCIACIONES MAREUF E.I\n"
        "RUC : 20538821374 Placa :\n"
        "OP.GRAVADAS S/ 2959.32\nIGV S/ 532.68\nTOTAL S/ 3492.00\n"
        "Representación impresa de la BOLETA DE VENTA ELECTRONICA"
    )
    datos = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert datos is not None
    assert datos["requiere_revision"] is True
    assert "TIPO_COMPROBANTE_CONFLICTIVO" in datos["alertas"]


def test_ticket_sin_contradiccion_no_genera_alerta() -> None:
    texto = (
        "SERVICENTRO JABSA S.A\nRUC : 20374914201\n"
        "FACTURA DE VENTA ELECTRÓNICA\nF003-00004475\n"
        "Fecha Emision : 15/10/2026\nTOTAL S/ 3492.00"
    )
    datos = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert datos is not None
    assert "TIPO_COMPROBANTE_CONFLICTIVO" not in datos.get("alertas", [])


def test_ticket_con_tipo_contradictorio_no_se_auto_vincula() -> None:
    from types import SimpleNamespace

    from app.services.automatizacion_documental import aplicar_automaticamente

    documento = SimpleNamespace(datos_extraidos={}, expediente_id=None)
    procesamiento = {
        "extraccion_estructurada": {
            "alertas": ["TIPO_COMPROBANTE_CONFLICTIVO"],
        }
    }
    resultado = aplicar_automaticamente(None, None, None, documento, procesamiento)
    assert resultado.estado == "REVISION_REQUERIDA"
    assert documento.datos_extraidos["automatizacion_documental"]["estado"] == (
        "REVISION_REQUERIDA"
    )
