"""Regresión de expedientes pendientes de autorización del receptor.

Los importes quedan como datos documentales; no se autoriza contabilización.
"""

import uuid
from dataclasses import replace

from fastapi.testclient import TestClient


def test_expediente_manual_receptor_no_autorizado_admite_adjunto(client: TestClient) -> None:
    factura = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura-pendiente.pdf", b"%PDF-1.7 factura sintetica")},
    )
    assert factura.status_code == 201, factura.text
    documento_id = factura.json()["id"]
    campos = {
        "serie": "F001",
        "correlativo": "00009988",
        "ruc_emisor": "20999999991",
        "ruc_receptor": "20999999992",
        "fecha_emision": "2026-10-19",
        "moneda": "PEN",
        "importe_total": "100.00",
    }
    confirmado = client.put(
        f"/api/v1/documentos/{documento_id}/extraccion-confirmada",
        json=campos,
    )
    assert confirmado.status_code == 200, confirmado.text
    creado = client.post(
        f"/api/v1/documentos/{documento_id}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert creado.status_code == 200, creado.text
    expediente = creado.json()["expediente"]
    assert expediente["pendiente_aprobacion"] is True
    expediente_id = expediente["id"]
    receptor_id = expediente["receptor"]["id"]

    por_serie = client.get("/api/v1/expedientes", params={"buscar": "F001-9988"})
    assert por_serie.status_code == 200, por_serie.text
    assert any(item["id"] == expediente_id for item in por_serie.json())

    por_ruc = client.get("/api/v1/expedientes", params={"receptor_ruc": "20999999992"})
    assert por_ruc.status_code == 200, por_ruc.text
    assert any(item["id"] == expediente_id for item in por_ruc.json())

    por_uuid = client.get(f"/api/v1/expedientes/{expediente_id}")
    assert por_uuid.status_code == 200, por_uuid.text
    assert por_uuid.json()["id"] == expediente_id
    assert receptor_id

    voucher = client.post(
        "/api/v1/documentos",
        data={"expediente_id": expediente_id, "tipo_documento": "VCHR"},
        files={"archivo": ("voucher-pendiente.pdf", b"%PDF-1.7 voucher sintetico")},
    )
    assert voucher.status_code == 201, voucher.text
    assert voucher.json()["expediente_id"] == expediente_id

    repetido = client.post(
        f"/api/v1/documentos/{documento_id}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert repetido.status_code == 200, repetido.text
    assert repetido.json()["expediente"]["id"] == expediente_id
    assert repetido.json()["expediente"]["pendiente_aprobacion"] is True


def test_expediente_pendiente_aislado_por_tenant(client: TestClient, auth_prueba: object) -> None:
    original = client.post(
        "/api/v1/documentos",
        files={"archivo": ("pendiente-aislado.pdf", b"%PDF-1.7 contenido sintetico")},
    )
    assert original.status_code == 201, original.text
    documento_id = original.json()["id"]
    contexto = auth_prueba.contexto
    auth_prueba.contexto = replace(contexto, tenant_id=uuid.uuid4())
    try:
        assert client.get(f"/api/v1/documentos/{documento_id}").status_code == 404
        assert client.post(
            f"/api/v1/documentos/{documento_id}/vincular",
            json={"expediente_id": str(uuid.uuid4()), "tipo_documento": "VCHR"},
        ).status_code == 404
    finally:
        auth_prueba.contexto = contexto


def test_usuario_no_puede_autorizar_empresa(client: TestClient) -> None:
    resultado = client.patch(
        f"/api/v1/empresas/{uuid.uuid4()}",
        json={"autorizada": True},
    )
    assert resultado.status_code == 403, resultado.text
