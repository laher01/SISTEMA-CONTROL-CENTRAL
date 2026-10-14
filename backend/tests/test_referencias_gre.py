"""Casos reales de GRE remitente y referencias fiscales seguras."""

from app.services.referencias_gre import extraer_referencias_factura_gre

EJEMPLO = (
    "Datos del Destinatario :INVERSIONES Y NEGOCIACIONES MAREUF E.I.R.L. - "
    "REGISTRO ÚNICO DE CONTRIBUYENTES N° 20538821374\n"
    "Documentos Relacionados:\n"
    "Factura N° E001 175 - RUC N° 10421885627"
)


def test_referencia_gre_e001_175_y_rucs() -> None:
    referencias = extraer_referencias_factura_gre(EJEMPLO)
    assert len(referencias) == 1
    ref = referencias[0]
    assert (ref.serie, ref.correlativo) == ("E001", "175")
    assert ref.emisor_ruc == "10421885627"
    assert ref.receptor_ruc == "20538821374"


def test_no_usar_numero_propio_gre() -> None:
    assert extraer_referencias_factura_gre("GRE REMITENTE E001-175 RUC 10421885627") == ()


def test_no_inventar_ruc_de_factura() -> None:
    refs = extraer_referencias_factura_gre(
        "Datos del Destinatario RUC 20538821374\nDocumentos Relacionados: Factura N° E001-175"
    )
    assert len(refs) == 1
    assert refs[0].emisor_ruc is None


def test_referencias_multiples_no_crean_una_factura_ficticia() -> None:
    refs = extraer_referencias_factura_gre(
        "Documentos Relacionados:\n"
        "Factura N° E001 175 - RUC N° 10421885627\n"
        "Factura N° E001 176 - RUC N° 10421885627"
    )
    assert {(r.serie, r.correlativo) for r in refs} == {("E001", "175"), ("E001", "176")}


def test_no_confundir_destinatario_con_emisor_de_factura() -> None:
    refs = extraer_referencias_factura_gre(
        "Datos del Destinatario RUC 20538821374\n"
        "Documentos Relacionados: Factura N° E001 175 - RUC N° 10421885627"
    )
    assert refs[0].receptor_ruc != refs[0].emisor_ruc


def test_referencias_de_cinco_gre_sunat_reales_anonimizadas_por_formato() -> None:
    """Regresión de la disposición de texto de cinco GRE SUNAT (sin adjuntar PDF)."""
    casos = (
        ("20612638935", "20538821374", "E001", "435"),
        ("20614885085", "20615137422", "E001", "481"),
        ("20614885085", "20524011353", "E001", "468"),
        ("20614885085", "20613213008", "E001", "474"),
        ("10708800207", "20524011353", "E001", "246"),
    )
    for emisor, receptor, serie, correlativo in casos:
        texto = (
            f"EMPRESA REMITENTE RUC N°{emisor}\\n"
            "GUÍA DE REMISIÓN ELECTRÓNICA\\nREMITENTE\\n"
            f"Datos del Destinatario : EMPRESA DESTINATARIA - "
            f"REGISTRO ÚNICO DE CONTRIBUYENTES N° {receptor}\\n"
            "Documentos Relacionados:\\n"
            f"Factura N° {serie} {correlativo} - RUC N° {emisor}\\n"
            "Bienes por transportar:"
        ).replace("\\\\n", "\\n")
        refs = extraer_referencias_factura_gre(texto)
        assert len(refs) == 1, (emisor, receptor, refs)
        assert (refs[0].serie, refs[0].correlativo) == (serie, correlativo)
        assert refs[0].emisor_ruc == emisor
        assert refs[0].receptor_ruc == receptor
