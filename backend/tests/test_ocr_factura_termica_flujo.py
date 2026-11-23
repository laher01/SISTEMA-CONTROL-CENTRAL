"""Flujo aislado: ticket sintético -> OCR -> revisión -> confirmación -> expediente.

El mismo endpoint multipart recibe archivos de web y Android; no usa sus credenciales,
el PDF comercial ni conexiones a producción.
"""

import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.services import procesamiento_documental as pd


def _pdf_termico_sintetico() -> bytes:
    salida = io.BytesIO()
    escritor = PdfWriter()
    escritor.add_blank_page(width=140, height=380)
    escritor.write(salida)
    return salida.getvalue()


def test_ticket_termico_multiplataforma_confirma_identidad_antes_de_crear_expediente(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setattr(pd, "_idioma_disponible", lambda _: "spa")

    def lectura(
        _motor: str, _archivo: object, _idioma: str, _limite: int, psm: int | None = None
    ) -> tuple[str, float]:
        if psm == 6:
            return "F F O L - 000136", 0.48
        return (
            "COMERCIO DE PRUEBA\nRUC: 20999999991\nFACTURA ELECTRONICA\n"
            "F F O L - OOOI36\nEmisión: 21/01/2026\n"
            "Documento: 20999999992\nOp. Gravadas: S/ 52.54\n"
            "I.G.V 18%: S/ 9.46\nTotal: S/ 62.00",
            0.88,
        )

    monkeypatch.setattr(pd, "_ejecutar_tesseract", lectura)

    # Contrato compartido: web (FormData) y Android (multipart), mismo campo "archivo".
    subida = client.post(
        "/api/v1/documentos",
        files={
            "archivo": (
                "factura-termica-sintetica.pdf",
                _pdf_termico_sintetico(),
                "application/pdf",
            )
        },
    )
    assert subida.status_code == 201, subida.text
    documento_id = subida.json()["id"]

    procesado = client.post(f"/api/v1/documentos/{documento_id}/procesar")
    assert procesado.status_code == 200, procesado.text
    datos = procesado.json()["datos_extraidos"]
    proceso = datos["procesamiento_documental"]
    assert proceso["metodo"] == "OCR_PDF"
    assert proceso["ocr_revision"]["requiere_confirmacion"] is True
    assert "F F O L" in proceso["ocr_revision"]["texto"]
    assert proceso["extraccion_estructurada"]["campos"]["importe_total"]["valor"] == "62.00"
    assert "serie" not in proceso["extraccion_estructurada"]["campos"]
    assert "extraccion_confirmada" not in datos
    assert procesado.json()["expediente_id"] is None

    solicitud = {"tipo_comprobante": "FACT", "requiere_guia": False}
    bloqueado = client.post(f"/api/v1/documentos/{documento_id}/crear-expediente", json=solicitud)
    assert bloqueado.status_code == 409, bloqueado.text
    assert "Debe confirmar la extracción" in bloqueado.json()["detail"]

    confirmacion = client.put(
        f"/api/v1/documentos/{documento_id}/extraccion-confirmada",
        json={
            "serie": "FF01",
            "correlativo": "000136",
            "ruc_emisor": "20999999991",
            "ruc_receptor": "20999999992",
            "fecha_emision": "2026-01-21",
            "moneda": "PEN",
            "subtotal": "52.54",
            "igv": "9.46",
            "importe_total": "62.00",
        },
    )
    assert confirmacion.status_code == 200, confirmacion.text
    campos_confirmados = confirmacion.json()["datos_extraidos"]["extraccion_confirmada"]["campos"]
    assert campos_confirmados["serie"] == "FF01"

    creado = client.post(f"/api/v1/documentos/{documento_id}/crear-expediente", json=solicitud)
    assert creado.status_code == 200, creado.text
    assert creado.json()["expediente"]["serie"] == "FF01"
    assert str(creado.json()["expediente"]["importe_total"]) == "62.00"

    # Evita duplicar identidad fiscal y monto si se repite la operación.
    repetido = client.post(f"/api/v1/documentos/{documento_id}/crear-expediente", json=solicitud)
    assert repetido.status_code == 200, repetido.text
    assert repetido.json()["creado"] is False
    assert repetido.json()["expediente"]["id"] == creado.json()["expediente"]["id"]
