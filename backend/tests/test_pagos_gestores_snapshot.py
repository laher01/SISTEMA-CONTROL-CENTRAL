"""Regresión: una comisión actualizada no altera liquidaciones ya programadas."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Gestor, PagoGestor
from tests.conftest import AuthPrueba


def test_liquidacion_gestor_conserva_snapshot_de_porcentaje_y_saldo(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tid = auth_prueba.contexto.tenant_id
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None

    emisor = Empresa(tenant_id=tid, ruc="20911111111", razon_social="Emisor")
    receptor = Empresa(tenant_id=tid, ruc="20922222222", razon_social="Receptor")
    gestor = Gestor(
        tenant_id=tid,
        codigo="GES-SNAPSHOT",
        nombre="Gestor histórico",
        usuario_id=usuario_id,
        porcentaje_comision=Decimal("2.0000"),
    )
    session.add_all([emisor, receptor, gestor])
    session.flush()
    session.add(
        Expediente(
            tenant_id=tid,
            receptor_id=receptor.id,
            emisor_id=emisor.id,
            tipo_comprobante="01",
            serie="F002",
            correlativo="00000001",
            fecha_emision=date(2026, 10, 5),
            moneda="PEN",
            importe_total=Decimal("1000.00"),
            usuario_id=usuario_id,
            gestor_id=gestor.id,
        )
    )
    session.commit()

    datos = {
        "gestor_id": str(gestor.id),
        "desde": "2026-10-01",
        "hasta": "2026-10-31",
        "moneda": "PEN",
    }
    programacion = client.post("/api/v1/pagos-gestores/programar", json=datos)
    assert programacion.status_code == 201, programacion.text
    pago_id = programacion.json()["id"]
    assert Decimal(programacion.json()["saldo"]) == Decimal("20.00")

    gestor.porcentaje_comision = Decimal("7.0000")
    session.commit()

    cotizacion_nueva = client.post("/api/v1/pagos-gestores/cotizar", json=datos)
    assert cotizacion_nueva.status_code == 200
    assert Decimal(cotizacion_nueva.json()["porcentaje"]) == Decimal("7.0000")
    assert Decimal(cotizacion_nueva.json()["bruto"]) == Decimal("70.00")

    pago_historico = session.get(PagoGestor, uuid.UUID(pago_id))
    assert pago_historico is not None
    assert Decimal(pago_historico.bruto) == Decimal("20.00")
    listado = client.get("/api/v1/pagos-gestores")
    assert listado.status_code == 200, listado.text
    original = next(p for p in listado.json() if p["id"] == pago_id)
    assert Decimal(original["porcentaje"]) == Decimal("2.0000")
    assert Decimal(original["saldo"]) == Decimal("20.00")
    assert original["estado"] == "PROGRAMADO"
    assert client.post("/api/v1/pagos-gestores/programar", json=datos).status_code == 409
