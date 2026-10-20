"""Creación manual de expediente cuando OCR no proporciona campos."""

import uuid
from dataclasses import replace

from fastapi.testclient import TestClient


def test_confirmacion_manual_sin_ocr_y_colision_fiscal(client: TestClient) -> None:
    campos = {
        "serie": "F001",
        "correlativo": "00000001",
        "ruc_emisor": "20999999991",
        "ruc_receptor": "20999999992",
        "fecha_emision": "2026-09-29",
        "moneda": "PEN",
        "importe_total": "28800.00",
    }
    solicitud = {"tipo_comprobante": "FACT", "requiere_guia": False}

    primero = client.post(
        "/api/v1/documentos",
        files={"archivo": ("sin-lectura-1.pdf", b"%PDF-1.7 sin lectura 1")},
    )
    assert primero.status_code == 201, primero.text
    documento_id = primero.json()["id"]
    confirmar = client.put(f"/api/v1/documentos/{documento_id}/extraccion-confirmada", json=campos)
    assert confirmar.status_code == 200, confirmar.text
    creado = client.post(f"/api/v1/documentos/{documento_id}/crear-expediente", json=solicitud)
    assert creado.status_code == 200, creado.text
    assert creado.json()["creado"] is True
    expediente_id = creado.json()["expediente"]["id"]
    assert expediente_id

    # Repetición exacta desde el mismo documento: idempotencia.
    otra_vez = client.post(f"/api/v1/documentos/{documento_id}/crear-expediente", json=solicitud)
    assert otra_vez.status_code == 200, otra_vez.text
    assert otra_vez.json()["creado"] is False
    assert otra_vez.json()["expediente"]["id"] == expediente_id

    # Segundo archivo distinto con identidad fiscal repetida: no duplicar.
    segundo = client.post(
        "/api/v1/documentos",
        files={"archivo": ("sin-lectura-2.pdf", b"%PDF-1.7 sin lectura 2")},
    )
    assert segundo.status_code == 201, segundo.text
    segundo_id = segundo.json()["id"]
    assert (
        client.put(
            f"/api/v1/documentos/{segundo_id}/extraccion-confirmada", json=campos
        ).status_code
        == 200
    )
    conflicto = client.post(f"/api/v1/documentos/{segundo_id}/crear-expediente", json=solicitud)
    assert conflicto.status_code == 409, conflicto.text
    assert conflicto.json()["detail"]["duplicado"] is True
    assert conflicto.json()["detail"]["expediente_id"] == expediente_id


def test_creacion_manual_no_cruza_tenant(client: TestClient, auth_prueba: object) -> None:
    registro = client.post(
        "/api/v1/documentos",
        files={"archivo": ("aislamiento.pdf", b"%PDF-1.7 aislamiento fiscal")},
    )
    assert registro.status_code == 201, registro.text
    documento_id = registro.json()["id"]
    contexto_original = auth_prueba.contexto
    auth_prueba.contexto = replace(contexto_original, tenant_id=uuid.uuid4())
    try:
        campos = {
            "serie": "F001",
            "correlativo": "00000002",
            "ruc_emisor": "20999999991",
            "ruc_receptor": "20999999992",
            "fecha_emision": "2026-10-07",
            "moneda": "PEN",
            "importe_total": "9400.00",
        }
        confirmar = client.put(
            f"/api/v1/documentos/{documento_id}/extraccion-confirmada", json=campos
        )
        assert confirmar.status_code == 404
        crear = client.post(
            f"/api/v1/documentos/{documento_id}/crear-expediente",
            json={"tipo_comprobante": "FACT", "requiere_guia": False},
        )
        assert crear.status_code == 404
    finally:
        auth_prueba.contexto = contexto_original
