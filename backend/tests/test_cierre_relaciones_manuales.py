"""Cierre técnico: asociación conservadora y alternativa manual."""

from fastapi.testclient import TestClient


def test_documento_ambiguo_permanece_pendiente_y_se_vincula_manualmente(
    client: TestClient,
) -> None:
    voucher = client.post(
        "/api/v1/documentos",
        data={"tipo_documento": "VCHR"},
        files={"archivo": ("voucher-sin-referencia.pdf", b"%PDF-1.7 voucher sin referencia")},
    )
    assert voucher.status_code == 201, voucher.text
    voucher_id = voucher.json()["id"]

    factura = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura-manual.pdf", b"%PDF-1.7 factura sintetica")},
    )
    assert factura.status_code == 201, factura.text
    documento_id = factura.json()["id"]
    confirmar = client.put(
        f"/api/v1/documentos/{documento_id}/extraccion-confirmada",
        json={
            "serie": "F001",
            "correlativo": "00009125",
            "ruc_emisor": "20999999991",
            "ruc_receptor": "20999999992",
            "fecha_emision": "2026-10-19",
            "moneda": "PEN",
            "importe_total": "150.00",
        },
    )
    assert confirmar.status_code == 200, confirmar.text
    creado = client.post(
        f"/api/v1/documentos/{documento_id}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert creado.status_code == 200, creado.text
    expediente_id = creado.json()["expediente"]["id"]

    sin_relacion = client.get(f"/api/v1/documentos/{voucher_id}")
    assert sin_relacion.status_code == 200, sin_relacion.text
    assert sin_relacion.json()["expediente_id"] is None

    vincular = client.post(
        f"/api/v1/documentos/{voucher_id}/vincular",
        json={"expediente_id": expediente_id, "tipo_documento": "VCHR"},
    )
    assert vincular.status_code == 200, vincular.text
    assert vincular.json()["expediente_id"] == expediente_id
