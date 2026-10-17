"""Regresiones de formatos nuevos sin adjuntar datos ni imágenes privadas."""

from app.services.extraccion_campos import extraer_campos


def test_escorpio_numero_separado_nro_y_rucs() -> None:
    texto = (
        "INVERSIONES Y ASESORAMIENTO ESCORPIO SAC\n"
        "R.U.C. N° 20516453835\n"
        "FACTURA ELECTRÓNICA\n"
        "F109 Nº 0016490\n"
        "SEÑOR(ES)\n: INVERSIONES BORISO E.I.R.L.\n"
        "RUC\n: 20605535098\n"
        "FECHA DE EMISIÓN\n2026-10-02\n"
        "OP GRAVADAS S/ 1,483.05\nI.G.V. 18% S/ 266.95\n"
        "IMPORTE TOTAL S/ 1,750.00\n"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["serie"]["valor"] == "F109"
    assert campos["correlativo"]["valor"] == "16490"
    assert campos["ruc_emisor"]["valor"] == "20516453835"
    assert campos["ruc_receptor"]["valor"] == "20605535098"
    assert campos["importe_total"]["valor"] == "1750.00"


def test_bcp_operacion_larga_conserva_cero_y_no_inventa_serie() -> None:
    texto = (
        "BCP\n¡Transferencia exitosa!\n"
        "S/ 10,160.00\n"
        "Domingo, 20 Septiembre 2026 - 06:23 p.m.\n"
        "Enviado a Vivar Melendrez Jimena Joan J.\n"
        "Número de operación\n03857359\n"
    )
    resultado = extraer_campos(texto, "OCR", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["banco"]["valor"] == "BCP"
    assert campos["numero_operacion"]["valor"] == "03857359"
    assert campos["importe_total"]["valor"] == "10160.00"
    assert campos["fecha_emision"]["valor"] == "2026-09-20"
    assert "serie" not in campos
    assert "ruc_emisor" not in campos
    assert "ruc_receptor" not in campos


def test_bcp_sin_identificador_no_crea_operacion() -> None:
    resultado = extraer_campos(
        "BCP\nTransferencia exitosa\nS/ 350.00\n",
        "OCR",
        1.0,
    )
    assert resultado is not None
    assert "numero_operacion" not in resultado["campos"]


def test_factura_con_mencion_de_transferencia_bcp_conserva_serie() -> None:
    texto = (
        "FACTURA ELECTRÓNICA\nF001-00000123\n"
        "RUC EMISOR: 20616012739\nRUC RECEPTOR: 20538821374\n"
        "FORMA DE PAGO: TRANSFERENCIA BCP\nIMPORTE TOTAL S/ 120.00"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["campos"]["serie"]["valor"] == "F001"
    assert resultado["campos"]["correlativo"]["valor"] == "123"


def test_bcp_con_concepto_pago_factura_no_inventa_serie() -> None:
    texto = (
        "BCP\nTransferencia exitosa\nS/ 10,160.00\n"
        "Domingo, 20 Septiembre 2026 - 06:23 p.m.\n"
        "Concepto: pago factura de proveedor\n"
        "Número de operación\n03857359\n"
    )
    resultado = extraer_campos(texto, "OCR", 1.0)
    assert resultado is not None
    assert resultado["campos"]["numero_operacion"]["valor"] == "03857359"
    assert "serie" not in resultado["campos"]
    assert "correlativo" not in resultado["campos"]


def test_bcp_con_factura_electronica_en_concepto_no_inventa_serie() -> None:
    texto = (
        "BCP\nTransferencia exitosa\nS/ 120.00\n"
        "Domingo, 20 Septiembre 2026 - 06:23 p.m.\n"
        "Concepto: pago de factura electrónica del proveedor\n"
        "Número de operación\n03857359\n"
    )
    resultado = extraer_campos(texto, "OCR", 1.0)
    assert resultado is not None
    assert resultado["campos"]["numero_operacion"]["valor"] == "03857359"
    assert "serie" not in resultado["campos"]
    assert "correlativo" not in resultado["campos"]


def test_jabsa_ticket_extrae_rucs_y_total_con_etiquetas() -> None:
    texto = (
        "SERVICENTRO JABSA S.A\nRUC : 20374914201\n"
        "FACTURA DE VENTA ELECTRONICA\nF003-00004475\n"
        "Cliente : INVERSIONES Y NEGOCIACIONES MAREUF E.I\n"
        "RUC : 20538821374 Placa :\n"
        "OP.GRAVADAS S/ 2959.32\nIGV S/ 532.68\n"
        "TOTAL S/ 3492.00\n"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["serie"]["valor"] == "F003"
    assert campos["ruc_emisor"]["valor"] == "20374914201"
    assert campos["ruc_receptor"]["valor"] == "20538821374"
    assert campos["importe_total"]["valor"] == "3492.00"
