"""Los importes documentales pendientes no forman parte de totales autorizados."""

from fastapi.testclient import TestClient


def test_importe_pendiente_no_aparece_en_totales(client: TestClient) -> None:
    documento = client.post(
        "/api/v1/documentos",
        files={"archivo": ("comprobante.pdf", b"%PDF-1.7 documento sintetico")},
    )
    assert documento.status_code == 201, documento.text
    documento_id = documento.json()["id"]
    campos = {
        "serie": "F001",
        "correlativo": "00009123",
        "ruc_emisor": "20999999991",
        "ruc_receptor": "20999999992",
        "fecha_emision": "2026-10-19",
        "moneda": "PEN",
        "importe_total": "125.00",
    }
    confirmado = client.put(f"/api/v1/documentos/{documento_id}/extraccion-confirmada", json=campos)
    assert confirmado.status_code == 200, confirmado.text
    creado = client.post(
        f"/api/v1/documentos/{documento_id}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert creado.status_code == 200, creado.text
    assert creado.json()["expediente"]["pendiente_aprobacion"] is True

    expedientes = client.get("/api/v1/expedientes/resumen")
    assert expedientes.status_code == 200, expedientes.text
    assert str(expedientes.json()["total_pen_autorizado"]) in ("0", "0.00")

    documentos = client.get("/api/v1/documentos/resumen")
    assert documentos.status_code == 200, documentos.text
    assert str(documentos.json()["total_pen_autorizado"]) in ("0", "0.00")

    empresas = client.get("/api/v1/expedientes/resumen-empresas")
    assert empresas.status_code == 200, empresas.text
