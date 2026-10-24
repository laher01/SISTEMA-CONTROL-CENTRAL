"""Aceptación OCR/PDF con datos sintéticos y DB aislada de CI.

No necesita acceso a Oracle, credenciales reales ni documentos fiscales.
Los escenarios MISD concurrentes y parser Bizlinks siguen cubiertos por
test_ocr_documentos_retirados.py y test_san_jose_bizlinks.py.
"""

import uuid
from dataclasses import replace

from fastapi.testclient import TestClient


def test_aceptacion_ingreso_manual_duplicado_y_voucher(client: TestClient) -> None:
    campos = {
        "serie": "F001",
        "correlativo": "00008761",
        "ruc_emisor": "20999999991",
        "ruc_receptor": "20999999992",
        "fecha_emision": "2026-10-23",
        "moneda": "PEN",
        "importe_total": "145.00",
    }
    factura = client.post(
        "/api/v1/documentos",
        files={"archivo": ("aceptacion-1.pdf", b"%PDF-1.7 prueba sintetica uno")},
    )
    assert factura.status_code == 201, factura.text
    documento_id = factura.json()["id"]

    confirmacion = client.put(
        f"/api/v1/documentos/{documento_id}/extraccion-confirmada", json=campos
    )
    assert confirmacion.status_code == 200, confirmacion.text

    crear = client.post(
        f"/api/v1/documentos/{documento_id}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert crear.status_code == 200, crear.text
    expediente_id = crear.json()["expediente"]["id"]
    assert expediente_id

    otra_vez = client.post(
        f"/api/v1/documentos/{documento_id}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert otra_vez.status_code == 200, otra_vez.text
    assert otra_vez.json()["creado"] is False

    duplicada = client.post(
        "/api/v1/documentos",
        files={"archivo": ("aceptacion-2.pdf", b"%PDF-1.7 prueba sintetica dos")},
    )
    assert duplicada.status_code == 201, duplicada.text
    repetida_id = duplicada.json()["id"]
    assert client.put(
        f"/api/v1/documentos/{repetida_id}/extraccion-confirmada", json=campos
    ).status_code == 200
    rechazo = client.post(
        f"/api/v1/documentos/{repetida_id}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert rechazo.status_code == 409, rechazo.text

    voucher = client.post(
        "/api/v1/documentos",
        data={"tipo_documento": "VCHR"},
        files={"archivo": ("voucher-sintetico.pdf", b"%PDF-1.7 voucher de prueba")},
    )
    assert voucher.status_code == 201, voucher.text
    voucher_id = voucher.json()["id"]
    vincular = client.post(
        f"/api/v1/documentos/{voucher_id}/vincular",
        json={"expediente_id": expediente_id, "tipo_documento": "VCHR"},
    )
    assert vincular.status_code == 200, vincular.text
    assert vincular.json()["expediente_id"] == expediente_id


def test_aceptacion_no_cruza_tenant(client: TestClient, auth_prueba: object) -> None:
    creado = client.post(
        "/api/v1/documentos",
        files={"archivo": ("tenant-privado.pdf", b"%PDF-1.7 aislamiento de prueba")},
    )
    assert creado.status_code == 201, creado.text
    documento_id = creado.json()["id"]

    contexto_original = auth_prueba.contexto
    auth_prueba.contexto = replace(contexto_original, tenant_id=uuid.uuid4())
    try:
        assert client.get(f"/api/v1/documentos/{documento_id}").status_code == 404
        assert client.put(
            f"/api/v1/documentos/{documento_id}/extraccion-confirmada",
            json={
                "serie": "F001",
                "correlativo": "00008761",
                "ruc_emisor": "20999999991",
                "ruc_receptor": "20999999992",
                "fecha_emision": "2026-10-23",
                "moneda": "PEN",
                "importe_total": "145.00",
            },
        ).status_code == 404
    finally:
        auth_prueba.contexto = contexto_original
