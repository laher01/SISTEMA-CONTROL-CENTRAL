"""Contrato de recepción de importes fiscales sin alterar reglas del parser."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.schemas import ExtraccionConfirmar


def test_schema_separa_importes_sin_recalcular() -> None:
    datos = ExtraccionConfirmar.model_validate(
        {
            "subtotal": "108872.87",
            "igv": "19597.13",
            "descuentos": "0.00",
            "importe_total": "128470.00",
            "importe_a_pagar": "128470.00",
        }
    )
    assert datos.subtotal == Decimal("108872.87")
    assert datos.importe_total == Decimal("128470.00")
    assert datos.importe_a_pagar == Decimal("128470.00")


def test_confirmacion_persiste_importes_diferenciados_y_crea_expediente_con_total(
    client: TestClient,
) -> None:
    carga = client.post(
        "/api/v1/documentos",
        files={"archivo": ("fiscal-sintetica.pdf", b"%PDF-1.7 datos de prueba")},
    )
    assert carga.status_code == 201, carga.text
    documento_id = carga.json()["id"]
    campos = {
        "serie": "F001",
        "correlativo": "00000042",
        "ruc_emisor": "20999999991",
        "ruc_receptor": "20999999992",
        "fecha_emision": "2026-10-26",
        "moneda": "PEN",
        "subtotal": "100.00",
        "igv": "18.00",
        "descuentos": "2.00",
        "importe_total": "118.00",
        "importe_a_pagar": "116.00",
    }
    confirmacion = client.put(
        f"/api/v1/documentos/{documento_id}/extraccion-confirmada",
        json=campos,
    )
    assert confirmacion.status_code == 200, confirmacion.text
    guardados = confirmacion.json()["datos_extraidos"]["extraccion_confirmada"]["campos"]
    for nombre in ("subtotal", "igv", "descuentos", "importe_total", "importe_a_pagar"):
        assert Decimal(str(guardados[nombre])) == Decimal(campos[nombre])
    creado = client.post(
        f"/api/v1/documentos/{documento_id}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert creado.status_code == 200, creado.text
    assert Decimal(str(creado.json()["expediente"]["importe_total"])) == Decimal("118.00")
    consulta = client.get(f"/api/v1/documentos/{documento_id}")
    assert consulta.status_code == 200, consulta.text
    almacenados = consulta.json()["datos_extraidos"]["extraccion_confirmada"]["campos"]
    assert Decimal(str(almacenados["subtotal"])) == Decimal("100.00")
    assert Decimal(str(almacenados["importe_total"])) == Decimal("118.00")
