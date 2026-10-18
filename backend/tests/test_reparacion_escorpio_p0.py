"""Pruebas de validación fiscal para vista previa histórica SCORPIO."""

import pytest

from app.services.reparacion_escorpio import evaluar_identidad


def _pdf(numero: str, ruc_receptor: str = "20605535098") -> str:
    return (
        "INVERSIONES Y ASESORAMIENTO ESCORPIO SAC R.U.C. N° 20516453835\n"
        f"FACTURA ELECTRÓNICA F109 Nº {numero}\n"
        "SEÑOR(ES) : INVERSIONES BORISO E.I.R.L. DIRECCION : PAITA "
        f"RUC : {ruc_receptor}\n"
        "IMPORTE TOTAL S/ 1750.00\nwww.facturacion.jadal.pe"
    )


def test_acepta_identidad_verificada_y_expediente_mal_clasificado() -> None:
    estado, _ = evaluar_identidad(
        actual_serie="2026", actual_correlativo="10",
        esperado="0016490", receptor_ruc="20605535098",
        texto_pdf=_pdf("0016490"),
    )
    assert estado == "CANDIDATO"


@pytest.mark.parametrize(
    ("pdf", "esperado", "receptor"),
    [
        (_pdf("0016491"), "0016490", "20605535098"),
        (_pdf("0016490", "20614966174"), "0016490", "20605535098"),
        ("FACTURA ELECTRÓNICA F109-0016490", "0016490", "20605535098"),
    ],
)
def test_bloquea_documentos_que_no_acreditan_la_factura(
    pdf: str, esperado: str, receptor: str
) -> None:
    estado, _ = evaluar_identidad(
        actual_serie="2026", actual_correlativo="10",
        esperado=esperado, receptor_ruc=receptor, texto_pdf=pdf,
    )
    assert estado == "BLOQUEADO"


def test_no_reescribe_identidad_ya_corregida() -> None:
    estado, _ = evaluar_identidad(
        actual_serie="F109", actual_correlativo="16490",
        esperado="0016490", receptor_ruc="20605535098",
        texto_pdf=_pdf("0016490"),
    )
    assert estado == "YA_CORREGIDO"


def test_bloquea_otros_valores_anteriores() -> None:
    estado, _ = evaluar_identidad(
        actual_serie="F001", actual_correlativo="999",
        esperado="0016490", receptor_ruc="20605535098",
        texto_pdf=_pdf("0016490"),
    )
    assert estado == "BLOQUEADO"
