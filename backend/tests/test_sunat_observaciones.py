from types import SimpleNamespace

import pytest

from app.services import sunat_observaciones


def test_resumen_observado(monkeypatch: pytest.MonkeyPatch) -> None:
    textos = [
        "ANEXO 01.2 - DETALLE DE COMPROBANTES\n"
        "202511 6 20000000001 PROVEEDOR 1 Factura F001 1 01/11/2025 100.00 18.00 118.00",
        "202512 6 20000000001 PROVEEDOR 7 Nota F001 2 01/12/2025 -10.00 -1.80 -11.80\n"
        "202512 6 20000000002 FILA INCOMPLETA",
        "ANEXO 01.3\n202512 6 20000000001 OTRO 100.00 18.00 118.00",
    ]
    lector = SimpleNamespace(
        is_encrypted=False,
        pages=[SimpleNamespace(extract_text=lambda t=t: t) for t in textos],
    )
    monkeypatch.setattr(sunat_observaciones, "PdfReader", lambda _: lector)
    resultado = sunat_observaciones.resumir_observaciones_sunat(b"%PDF-")
    assert resultado["filas_leidas"] == 2
    assert resultado["filas_no_leidas"] == 1
    assert resultado["proveedores"] == 1
    assert resultado["igv_observado"] == "16.20"
    assert resultado["lectura_requiere_revision"] is True


def test_rechaza_archivo_no_pdf() -> None:
    with pytest.raises(ValueError, match="PDF inválido"):
        sunat_observaciones.resumir_observaciones_sunat(b"texto")
