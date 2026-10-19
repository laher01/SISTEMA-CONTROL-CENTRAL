"""Vinculación automática prudente y alternativa manual de pendientes."""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.models import Documento


def test_creacion_manual_vincula_voucher_coincidencia_inequivoca(
    client: TestClient, engine: Engine
) -> None:
    voucher = client.post(
        "/api/v1/documentos",
        data={"tipo_documento": "VCHR"},
        files={"archivo": ("voucher.pdf", b"%PDF-1.7 transferencia sintetica")},
    )
    assert voucher.status_code == 201, voucher.text
    voucher_id = voucher.json()["id"]

    with Session(engine) as session:
        pendiente = session.get(Documento, uuid.UUID(voucher_id))
        assert pendiente is not None
        pendiente.datos_extraidos = {
            "procesamiento_documental": {
                "texto": (
                    "Operación asociada a factura F001-9124. "
                    "RUC emisor 20999999991 RUC receptor 20999999992"
                )
            }
        }
        session.commit()

    factura = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura-manual.pdf", b"%PDF-1.7 factura sintetica")},
    )
    assert factura.status_code == 201, factura.text
    id_factura = factura.json()["id"]
    confirmado = client.put(
        f"/api/v1/documentos/{id_factura}/extraccion-confirmada",
        json={
            "serie": "F001",
            "correlativo": "00009124",
            "ruc_emisor": "20999999991",
            "ruc_receptor": "20999999992",
            "fecha_emision": "2026-10-19",
            "moneda": "PEN",
            "importe_total": "150.00",
        },
    )
    assert confirmado.status_code == 200, confirmado.text
    creado = client.post(
        f"/api/v1/documentos/{id_factura}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert creado.status_code == 200, creado.text
    expediente_id = creado.json()["expediente"]["id"]

    relacionado = client.get(f"/api/v1/documentos/{voucher_id}")
    assert relacionado.status_code == 200, relacionado.text
    assert relacionado.json()["expediente_id"] == expediente_id

    repetido = client.post(
        f"/api/v1/documentos/{id_factura}/crear-expediente",
        json={"tipo_comprobante": "FACT", "requiere_guia": False},
    )
    assert repetido.status_code == 200, repetido.text
    assert repetido.json()["expediente"]["id"] == expediente_id
