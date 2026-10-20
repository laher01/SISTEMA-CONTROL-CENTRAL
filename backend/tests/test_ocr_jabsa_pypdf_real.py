"""Regresión fiscal derivada del texto real extraído con pypdf del PDF JABSA.

No se incorpora el PDF privado al repositorio. El texto es un recorte
representativo, conservando el orden original que causó la incidencia.
"""

from app.services.extraccion_campos import extraer_campos


def test_jabsa_texto_pypdf_real_identidad_fecha_montos_y_alerta() -> None:
    texto = (
        "F003-00004475\nFACTURA DE VENTA ELECTRÓNICA\n"
        ": 15/10/2026Fecha Emision\nSERVICENTRO JABSA S.A\n"
        "RUC : 20374914201\n"
        "S/TOTAL\n532.68S/IGV\nOP.GRAVADAS S/ 2959.32\n3492.00\n"
        "Representación impresa de la BOLETA DE VENTA\n"
        "ELECTRONICA puede ser consultada en\n"
        "Cliente\nRUC\n:\n:\n:\nCAJERO 2 PUCUSANA\n"
        "INVERSIONES Y NEGOCIACIONES MAREUF E.I\n20538821374\n"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    esperados = {
        "serie": "F003",
        "correlativo": "00004475",
        "fecha_emision": "2026-10-15",
        "ruc_emisor": "20374914201",
        "ruc_receptor": "20538821374",
        "importe_total": "3492.00",
        "moneda": "PEN",
    }
    for nombre, valor in esperados.items():
        assert campos[nombre]["valor"] == valor
        assert campos[nombre]["evidencia"]
    assert resultado["requiere_revision"] is True
    assert "TIPO_COMPROBANTE_CONFLICTIVO" in resultado["alertas"]


def test_jabsa_fecha_invertida_separada_por_espacios() -> None:
    texto = "SERVICENTRO JABSA S.A FACTURA F003-00004475\n15/10/2026   Fecha Emision\n"
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["campos"]["fecha_emision"]["valor"] == "2026-10-15"


def test_formato_ajeno_no_se_interpreta_como_jabsa() -> None:
    texto = "OTRA EMPRESA FACTURA F001-00000123\nFecha Emision : 16/10/2026\n"
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["campos"]["fecha_emision"]["valor"] == "2026-10-16"
