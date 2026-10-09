import io
import subprocess

import pytest
from pypdf import PdfWriter

from app.enums import TipoDocumento
from app.services import procesamiento_documental as pd
from app.services.extraccion_campos import extraer_campos


def pdf_vacio(paginas: int = 1) -> bytes:
    salida = io.BytesIO()
    escritor = PdfWriter()
    for _ in range(paginas):
        escritor.add_blank_page(width=100, height=100)
    escritor.write(salida)
    return salida.getvalue()


def test_pdf_sin_capa_texto_solicita_ocr_si_no_hay_motor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _: None)
    resultado = pd.procesar(pdf_vacio(), 10_000)
    assert resultado.metodo == "TEXTO_PDF"
    assert resultado.paginas == 1
    assert resultado.texto == ""
    assert resultado.requiere_ocr is True


def test_pdf_escaneado_se_procesa_por_pagina(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setattr(pd, "_idioma_disponible", lambda _: "spa")
    resultados = iter([("FACTURA ELECTRONICA F001-123", 0.91), ("TOTAL 2500.00", 0.81)])
    monkeypatch.setattr(pd, "_ejecutar_tesseract", lambda *_: next(resultados))
    resultado = pd.procesar(pdf_vacio(2), 10_000)
    assert resultado.metodo == "OCR_PDF"
    assert resultado.motor == "pdfium+tesseract"
    assert resultado.paginas == 2
    assert resultado.confianza == pytest.approx(0.86)
    assert "--- Página 1 ---" in resultado.texto
    assert "--- Página 2 ---" in resultado.texto
    assert resultado.sugerencia is not None
    assert resultado.sugerencia.tipo == TipoDocumento.FACT


def test_pdf_invalido_se_rechaza() -> None:
    with pytest.raises(pd.DocumentoNoProcesable, match="dañado"):
        pd.procesar(b"%PDF-esto no es un pdf", 10_000)


def test_sugerencia_es_evidencia_y_no_clasificacion_automatica() -> None:
    sugerencia = pd.sugerir_tipo("FACTURA ELECTRÓNICA F001-123")
    assert sugerencia is not None
    assert sugerencia.tipo == TipoDocumento.FACT
    assert sugerencia.confianza == pytest.approx(0.8)
    assert sugerencia.a_dict()["requiere_confirmacion"] is True


def test_ocr_imagen_registra_confianza(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _: "/usr/bin/tesseract")

    def ejecutar(comando: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if "--list-langs" in comando:
            return subprocess.CompletedProcess(
                comando, 0, "List of available languages:\nspa\neng\n", ""
            )
        tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t90\tCONSTANCIA\n"
            "5\t1\t1\t1\t1\t2\t11\t0\t10\t10\t80\tDE\n"
            "5\t1\t1\t1\t1\t3\t22\t0\t10\t10\t70\tPAGO\n"
        )
        return subprocess.CompletedProcess(comando, 0, tsv, "")

    monkeypatch.setattr(pd.subprocess, "run", ejecutar)
    resultado = pd.procesar(b"\x89PNG\r\n\x1a\ncontenido", 10_000)
    assert resultado.texto == "CONSTANCIA DE PAGO"
    assert resultado.confianza == pytest.approx(0.8)
    assert resultado.idioma == "spa+eng"
    assert resultado.sugerencia is not None
    assert resultado.sugerencia.tipo == TipoDocumento.VCHR


def test_extrae_campos_de_factura_con_trazabilidad() -> None:
    texto = """FACTURA ELECTRÓNICA F001-00000123
    RUC EMISOR: 20500000002 CLIENTE RUC: 20100000001
    Fecha de emisión: 17/09/2026 Moneda: SOLES TOTAL S/ 2,500.40"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["serie"]["valor"] == "F001"
    assert campos["correlativo"]["valor"] == "123"
    assert campos["ruc_emisor"]["valor"] == "20500000002"
    assert campos["ruc_receptor"]["valor"] == "20100000001"
    assert campos["fecha_emision"]["valor"] == "2026-09-17"
    assert campos["moneda"]["valor"] == "PEN"
    assert campos["importe_total"]["valor"] == "2500.40"
    assert campos["importe_total"]["fuente"] == "TEXTO_PDF"
    assert campos["importe_total"]["requiere_confirmacion"] is True


def test_extrae_voucher_ocr_sin_confundir_miles_y_decimales() -> None:
    texto = "OPERACIÓN EXITOSA Nro. operación: AB-908771 TOTAL PAGADO US$ 1.234,56"
    resultado = extraer_campos(texto, "OCR_IMAGEN", 0.8)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["numero_operacion"]["valor"] == "AB-908771"
    assert campos["moneda"]["valor"] == "USD"
    assert campos["importe_total"]["valor"] == "1234.56"
    assert campos["numero_operacion"]["fuente"] == "OCR"
    assert campos["numero_operacion"]["confianza"] < 0.9


def test_fecha_imposible_no_se_publica() -> None:
    resultado = extraer_campos("FECHA DE EMISIÓN: 31/02/2026", "OCR_PDF", 0.9)
    assert resultado is None


def test_extrae_razones_sociales_de_factura() -> None:
    texto = """FACTURA ELECTRÓNICA F001-00000123
    PROVEEDOR: PESQUERA DEL PACIFICO S.A.C. RUC: 20500000002
    CLIENTE: NEXOMAR NEGOCIOS E.I.R.L. RUC: 20100000001
    Fecha de emisión: 17/09/2026 Moneda: SOLES TOTAL S/ 2,500.40"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["razon_social_emisor"]["valor"] == "PESQUERA DEL PACIFICO S.A.C."
    assert campos["razon_social_receptor"]["valor"] == "NEXOMAR NEGOCIOS E.I.R.L."


def test_extrae_partes_y_campos_de_recibo_por_honorarios() -> None:
    texto = """RECIBO POR HONORARIOS ELECTRÓNICO
    JUAN PEREZ LOPEZ
    RUC: 10456789012
    E001-00000038
    RECIBÍ DE: NEXOMAR NEGOCIOS E.I.R.L.
    IDENTIFICADO CON RUC NÚMERO: 20100000001
    FECHA DE EMISIÓN: 02/10/2026
    TOTAL POR HONORARIOS: S/ 350.00"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["serie"]["valor"] == "E001"
    assert campos["correlativo"]["valor"] == "38"
    assert campos["ruc_emisor"]["valor"] == "10456789012"
    assert campos["ruc_receptor"]["valor"] == "20100000001"
    assert campos["razon_social_emisor"]["valor"] == "JUAN PEREZ LOPEZ"
    assert campos["razon_social_receptor"]["valor"] == "NEXOMAR NEGOCIOS E.I.R.L."
    assert campos["fecha_emision"]["valor"] == "2026-10-02"
    assert campos["moneda"]["valor"] == "PEN"
    assert campos["importe_total"]["valor"] == "350.00"


def test_extrae_razon_social_junto_al_ruc_sin_etiqueta_proveedor() -> None:
    texto = """PESQUERA YATARUMI S.A.C.
    RUC: 20492560601
    FACTURA ELECTRÓNICA E001-00003321
    CLIENTE: COMERCIAL DEL MAR S.A.C.
    RUC RECEPTOR: 20600612876
    FECHA DE EMISIÓN: 02/10/2026
    TOTAL: S/ 1,250.00"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_receptor"]["valor"] == "20600612876"
    assert campos["razon_social_receptor"]["valor"] == "COMERCIAL DEL MAR S.A.C."


def test_no_confunde_direccion_con_razon_social_del_emisor() -> None:
    texto = """FACTURA ELECTRÓNICA F001-00000123
    PESQUERA CORRECTA S.A.C.
    DIRECCIÓN: AV. INDUSTRIAL 123 PAITA
    RUC EMISOR: 20500000002
    CLIENTE: NEXOMAR NEGOCIOS E.I.R.L. RUC RECEPTOR: 20100000001
    FECHA DE EMISIÓN: 17/09/2026
    TOTAL: S/ 500.00"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_emisor"]["valor"] == "20500000002"
    assert "razon_social_emisor" not in campos
    assert campos["razon_social_receptor"]["valor"] == "NEXOMAR NEGOCIOS E.I.R.L."


def test_razon_social_receptor_debe_estar_vinculada_al_mismo_ruc() -> None:
    texto = """FACTURA ELECTRÓNICA F001-00000123
    PROVEEDOR: PESQUERA DEL PACIFICO S.A.C. RUC EMISOR: 20500000002
    CLIENTE: EMPRESA AJENA S.A.C. RUC: 20999999999
    INFORMACIÓN ADICIONAL
    RUC RECEPTOR: 20100000001
    FECHA DE EMISIÓN: 17/09/2026
    TOTAL: S/ 500.00"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_receptor"]["valor"] == "20100000001"
    assert "razon_social_receptor" not in campos


def test_parser_sunat_extrae_razones_sociales_multilinea() -> None:
    texto = """MEGAIMPORT R & A E.I.R.L.
AV. BELAUNDE OESTE 500 SEC. 201
COMAS - LIMA - LIMA
FACTURA ELECTRONICA
RUC: 20615898598
E001-39
Fecha de Emisión : 20/08/2026
Señor(es) :
INVERSIONES Y NEGOCIACIONES
MAREUF E.I.R.L.
RUC : 20538821374
Dirección del Cliente :
CAL. PUQUINA NRO 110
Tipo de Moneda : SOLES
Importe Total : S/ 1,224.84
Esta es una representación impresa de la factura electrónica, generada en el Sistema de SUNAT."""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["formato_documental"] == "SUNAT_FACTURA"
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_emisor"]["valor"] == "20615898598"
    assert campos["ruc_receptor"]["valor"] == "20538821374"
    assert campos["razon_social_emisor"]["valor"] == "MEGAIMPORT R & A E.I.R.L."
    assert campos["razon_social_receptor"]["valor"] == "INVERSIONES Y NEGOCIACIONES MAREUF E.I.R.L."


def test_parser_facturalaya_extrae_emisor_y_receptor() -> None:
    texto = """"MULTINEGOCIOS JIRETH"
R.U.C.: 20602413498
NEXOMAR NEGOCIOS EIRL - 20602413498
FACTURA ELECTRÓNICA
F002 - 000122
Fecha de Emisión: 10-07-2026 09:33:33 PM
Razón Social: B2C MUSA E.I.R.L.
R.U.C. 20614966174
Dirección: MZA. W LOTE. 05
Forma de pago: EFECTIVO
Total: S/ 305.20
Emitido por: facturalaya.com"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["formato_documental"] == "OSE_FACTURALAYA"
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["razon_social_emisor"]["valor"] == "NEXOMAR NEGOCIOS EIRL"
    assert campos["razon_social_receptor"]["valor"] == "B2C MUSA E.I.R.L."
    assert campos["ruc_emisor"]["valor"] == "20602413498"
    assert campos["ruc_receptor"]["valor"] == "20614966174"


def test_parser_factuhost_extrae_razon_multilinea() -> None:
    texto = """Para consultar el comprobante ingresar a https://sigma.factuhost.com.pe/buscar
Representacion impresa de la Factura Electrónica
SIGMA PROYECTOS Y ABASTECIEMIENTO
E.I.R.L.
RUC 20615275400
FACTURA ELECTRÓNICA
F001-00004099
FECHA DE EMISIÓN : 2026-06-30 / 23:30:59
CLIENTE : B2C MUSA E.I.R.L.
RUC : 20614966174
DIRECCIÓN : MZ. W LT. 05
MONEDA : Soles
TOTAL A PAGAR: S/ 1,751.44"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["formato_documental"] == "OSE_FACTUHOST"
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["razon_social_emisor"]["valor"] == "SIGMA PROYECTOS Y ABASTECIEMIENTO E.I.R.L."
    assert campos["razon_social_receptor"]["valor"] == "B2C MUSA E.I.R.L."
    assert campos["ruc_emisor"]["valor"] == "20615275400"
    assert campos["ruc_receptor"]["valor"] == "20614966174"


def test_parser_efact_extrae_partes() -> None:
    texto = """RUC: 20602413498
Nro. F001-00000230
NEXOMAR NEGOCIOS E.I.R.L.
MZA. G2 LOTE. 13 P.J. CIUDAD BLANCA
FACTURA ELECTRÓNICA
Cliente:
CORPORACION LATINOAMERICANO EL NORTE E.I.R.L.
RUC:
20524049245
Dirección:
MZA. A LOTE. 17
31-jul-2026
Moneda: SOLES
TOTAL S/ 702.84
Representación impresa de la factura electrónica, consulte en www.efact.pe"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["formato_documental"] == "OSE_EFACT"
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_emisor"]["valor"] == "20602413498"
    assert campos["ruc_receptor"]["valor"] == "20524049245"
    assert campos["razon_social_emisor"]["valor"] == "NEXOMAR NEGOCIOS E.I.R.L."
    assert (
        campos["razon_social_receptor"]["valor"] == "CORPORACION LATINOAMERICANO EL NORTE E.I.R.L."
    )


def test_rhe_sunat_real_extrae_persona_natural_emisora_misma_linea() -> None:
    texto = """19/8/26, 13:56 Emisión del Recibo por Honorarios Electrónico

AYALA AREVALO ELVIS EDUARDO R.U.C. 10753246920
MZA. H LOTE. 9 A.H. JUAN VALER SANDOVAL PIURA - PAITA - PAITA
RECIBO POR HONORARIOS ELECTRÓNICO
Nro: E001-33
Recibí de FRUTTI DEL PAESE E.I.R.L.
Identificado con RUC Número 20611909234
Fecha de emisión 17 de Agosto del 2026
Total por Honorarios : 1,500.00
Retención (8 %) IR : (0.00)
Total Neto Recibido : 1,500.00 SOLES"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_emisor"]["valor"] == "10753246920"
    assert campos["razon_social_emisor"]["valor"] == "AYALA AREVALO ELVIS EDUARDO"
    assert campos["ruc_receptor"]["valor"] == "20611909234"
    assert campos["razon_social_receptor"]["valor"] == "FRUTTI DEL PAESE E.I.R.L."
    assert campos["fecha_emision"]["valor"] == "2026-08-17"
    assert campos["importe_total"]["valor"] == "1500.00"


def test_rhe_sunat_real_extrae_persona_natural_con_pdf_reordenado() -> None:
    texto = """DEL ARTÍCULO 33 DE LA LEY DEL IMPUESTO A LA RENTA
Recibí de:
Identificado con
Observación
Inciso
La suma de:
Total por honorarios:
Retención (
R.U.C.
RECIBO POR HONORARIOS ELECTRONICO
Nro:
10404432953
E001- 24
AREVALO HERRERA LUIS ALEXANDER
MZA. G2 LOTE. 13 CIUDAD BLANCA PIURA - PAITA - PAITA
TELÉFONO: -
número
Por concepto de
de del
Total Neto Recibido:
INVERSIONES Y NEGOCIACIONES YATDIZ IMPORT
RUC 20523209176
UN MIL CIENTO CINCUENTA Y 00/100 SOLES
SERVICIO DE CONTROL DE DESCARGA DE HIELO Y LOGISTICA
A
31 Julio 2026
1,150.00
(0.00)
1,150.00
SOLES
8 %) IR:
Fecha de emisión"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_emisor"]["valor"] == "10404432953"
    assert campos["razon_social_emisor"]["valor"] == "AREVALO HERRERA LUIS ALEXANDER"
    assert campos["ruc_receptor"]["valor"] == "20523209176"


def test_rhe_no_acepta_nro_como_razon_social_emisor() -> None:
    texto = """RECIBO POR HONORARIOS ELECTRÓNICO
R.U.C. 10753246920
Nro: E001-35
AYALA AREVALO ELVIS EDUARDO
Recibí de MAIK FISHING SOCIEDAD ANONIMA CERRADA
Identificado con RUC Número 20609762030
Fecha de emisión 19 de Agosto del 2026
Total por Honorarios : 1,500.00"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_emisor"]["valor"] == "10753246920"
    assert campos["razon_social_emisor"]["valor"] == "AYALA AREVALO ELVIS EDUARDO"


@pytest.mark.parametrize(
    ("numero", "receptor", "ruc_receptor", "dia"),
    [
        ("37", "MAIK FISHING SOCIEDAD ANONIMA CERRADA", "20609762030", "23"),
        ("38", "INVERSIONES YATAMURI E.I.R.L.", "20492560601", "24"),
        ("39", "FRUTTI DEL PAESE E.I.R.L.", "20611909234", "23"),
    ],
)
def test_rhe_sunat_columnas_desordenadas_tres_recibos(
    numero: str, receptor: str, ruc_receptor: str, dia: str
) -> None:
    # Simula texto que pypdf extrae por orden interno de bloques PDF:
    # fecha/total separados de sus respectivas etiquetas.
    texto = f"""RECIBO POR HONORARIOS ELECTRONICO
R.U.C. 10753246920
Nro:
E001- {numero}
AYALA AREVALO ELVIS EDUARDO
Recibí de: {receptor}
Identificado con RUC número {ruc_receptor}
La suma de: UN MIL QUINIENTOS Y 00/100 SOLES
Por concepto de EL SERVICIO DE ASESORIA Y DOCUMENTACION-PAITA
Inciso A DEL ARTICULO 33 DE LA LEY DEL IMPUESTO A LA RENTA
{dia} de Setiembre del 2026
1,500.00
(0.00)
1,500.00
SOLES
Total por honorarios:
Retención (8 %) IR:
Total Neto Recibido:
Fecha de emisión"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["serie"]["valor"] == "E001"
    assert campos["correlativo"]["valor"] == numero
    assert campos["ruc_emisor"]["valor"] == "10753246920"
    assert campos["ruc_receptor"]["valor"] == ruc_receptor
    assert campos["fecha_emision"]["valor"] == f"2026-09-{dia}"
    assert campos["importe_total"]["valor"] == "1500.00"
    assert campos["moneda"]["valor"] == "PEN"


@pytest.mark.parametrize(
    ("numero", "receptor", "ruc_receptor", "dia"),
    [
        ("37", "MAIK FISHING SOCIEDAD ANONIMA CERRADA", "20609762030", "23"),
        ("38", "INVERSIONES YATAMURI E.I.R.L.", "20492560601", "24"),
        ("39", "FRUTTI DEL PAESE E.I.R.L.", "20611909234", "23"),
    ],
)
def test_rhe_pypdf_originales_sunat_serie_invertida(
    numero: str, receptor: str, ruc_receptor: str, dia: str
) -> None:
    # Orden y separación observados al ejecutar PdfReader.extract_text()
    # sobre los tres PDF originales SUNAT (no su disposición visual).
    texto = f"""DEL ARTÍCULO 33 DE LA LEY DEL IMPUESTO A LA RENTA
Recibí de:
Identificado con
Observación
Inciso
La suma de:
Total por honorarios:
Retención (
R.U.C.
RECIBO POR HONORARIOS ELECTRONICO
Nro:
10753246920
-E001 {numero}
AYALA AREVALO ELVIS EDUARDO
MZA. H LOTE. 9 A.H. JUAN VALER SANDOVAL PIURA - PAITA - PAITA
-TELÉFONO:
número
Por concepto de
de del
Total Neto Recibido:
{receptor}
RUC {ruc_receptor}
 UN MIL QUINIENTOS Y 00/100 SOLES
EL SERVICIO DE ASESORIA Y DOCUMENTACION-PAITA
-
A
{dia} Setiembre 2026
1,500.00
(0.00)
1,500.00
SOLES
%) IR:8
Fecha de emisión"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["serie"]["valor"] == "E001"
    assert campos["correlativo"]["valor"] == numero
    assert campos["ruc_emisor"]["valor"] == "10753246920"
    assert campos["ruc_receptor"]["valor"] == ruc_receptor
    assert campos["fecha_emision"]["valor"] == f"2026-09-{dia}"
    assert campos["importe_total"]["valor"] == "1500.00"
    assert campos["moneda"]["valor"] == "PEN"


@pytest.mark.parametrize(
    ("emisor_nombre", "emisor_ruc", "numero", "receptor_nombre", "receptor_ruc", "total"),
    [
        ("COMERCIAL RAWIRA E.I.R.L.", "20615177424", "4015", "CORPORACION LATINOAMERICANO EL NORTE E.I.R.L.", "20524049245", "1994.00"),
        ("COMERCIAL RAWIRA E.I.R.L.", "20615177424", "3964", "FRUTTI DEL PAESE E.I.R.L.", "20611909234", "1499.20"),
        ("COMERCIAL RAWIRA E.I.R.L.", "20615177424", "3999", "B2C MUSA E.I.R.L.", "20614966174", "1994.00"),
        ("COMERCIAL RAWIRA E.I.R.L.", "20615177424", "3981", "CAVIA PORCELLUS URBINA E.I.R.L.", "20613213008", "1958.00"),
        ("COMERCIAL RAWIRA E.I.R.L.", "20615177424", "3927", "INVERSIONES Y NEGOCIACIONES MAREUF E.I.R.L.", "20538821374", "1944.00"),
        ("RAYYAN ZAYD E.I.R.L.", "20615191249", "3568", "INVERSIONES Y NEGOCIACIONES MAREUF E.I.R.L.", "20538821374", "1985.00"),
    ],
)
def test_facturas_separadas_real_sunat_jose_no_es_ose(
    emisor_nombre: str, emisor_ruc: str, numero: str,
    receptor_nombre: str, receptor_ruc: str, total: str,
) -> None:
    # Misma distribución y campos del texto pypdf de facturas originales
    # extraídas del paquete; no usar el nombre de archivo como fuente fiscal.
    texto = (
        f" {emisor_nombre}\nAV. JOSE CARLOS MARIATEGUI 2346\n"
        f"EL AGUSTINO - LIMA - LIMA\nFACTURA ELECTRONICA\n"
        f"RUC: {emisor_ruc}\nE001-{numero}\n"
        "Fecha de Emisión : 22/08/2026\n"
        f"Señor(es) : {receptor_nombre}\nRUC : {receptor_ruc}\n"
        "Tipo de Moneda : SOLES\nForma de pago: Contado\n"
        f"Importe Total : S/ {total[: -3]}.{total[-2:]}\n"
        "Esta es una representación impresa de la factura electrónica, "
        "generada en el Sistema de SUNAT."
    )
    from app.services.extraccion_campos import detectar_formato_documental

    assert detectar_formato_documental(texto) == "SUNAT_FACTURA"
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["ruc_emisor"]["valor"] == emisor_ruc
    assert campos["ruc_receptor"]["valor"] == receptor_ruc
    assert campos["razon_social_emisor"]["valor"] == emisor_nombre
    assert campos["razon_social_receptor"]["valor"] == receptor_nombre
    assert campos["serie"]["valor"] == "E001"
    assert campos["correlativo"]["valor"] == numero
    assert campos["importe_total"]["valor"] == total


def test_detector_ose_no_confunde_nombres_comunes() -> None:
    from app.services.extraccion_campos import detectar_formato_documental

    assert detectar_formato_documental("FACTURA ELECTRONICA\nJOSE PEREZ\nE001-1") != "OSE"
    assert detectar_formato_documental("PROVEEDOR OSE\nFACTURA ELECTRONICA") == "OSE"
