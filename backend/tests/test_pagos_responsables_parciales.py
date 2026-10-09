"""Pruebas de adelantos, saldo y comprobantes de Gerencia."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Miembro
from tests.conftest import AuthPrueba


def test_adelanto_y_pago_total_con_comprobante(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
) -> None:
    tenant = auth_prueba.contexto.tenant_id
    responsable = Miembro(tenant_id=tenant, codigo="RESP01", nombre="Resp", rol="RESPONSABLE")
    usuario = Miembro(tenant_id=tenant, codigo="USU01", nombre="Usuario", rol="USUARIO")
    cliente = Empresa(
        tenant_id=tenant, ruc="20538821374", razon_social="CLIENTE TEST", tipo_relacion="CLIENTE"
    )
    session.add_all([responsable, usuario, cliente])
    session.flush()
    usuario.responsable_id = responsable.id
    session.add(
        Expediente(
            tenant_id=tenant,
            emisor_id=cliente.id,
            receptor_id=cliente.id,
            tipo_comprobante="FACT",
            serie="F001",
            correlativo="300",
            fecha_emision=date(2026, 9, 15),
            moneda="PEN",
            importe_total=Decimal("1000.00"),
            usuario_id=usuario.id,
        gerente_id=auth_prueba.contexto.miembro_id,
        )
    )
    session.commit()
    auth_prueba.como_gerente()
    url = "/api/v1/pagos-responsables"
    programado = client.post(
        url + "/programar",
        json={
            "responsable_id": str(responsable.id),
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": "PEN",
        },
    )
    assert programado.status_code == 201, programado.text
    pago_id = programado.json()["id"]

    def abonar(accion: str, referencia: str, monto: str | None = None):
        datos = {"accion": accion, "referencia": referencia, "fecha": "2026-10-09"}
        if monto is not None:
            datos["monto"] = monto
        return client.post(
            f"{url}/{pago_id}/abonar",
            data=datos,
            files={"comprobante": ("voucher.pdf", b"%PDF-1.7 prueba", "application/pdf")},
        )

    parcial = abonar("ADELANTO", "REF-0001", "10.00")
    assert parcial.status_code == 200, parcial.text
    assert parcial.json()["saldo"] == "25.00"
    assert parcial.json()["estado"] == "PARCIAL"
    assert abonar("ADELANTO", "REF-0001", "1.00").status_code == 409
    assert abonar("ADELANTO", "REF-0002", "99.00").status_code == 422

    reprogramado = client.post(
        f"{url}/{pago_id}/reprogramar",
        json={"fecha": "2026-11-15", "motivo": "Se pagará en noviembre"},
    )
    assert reprogramado.status_code == 200, reprogramado.text

    final = abonar("TOTAL", "REF-0002")
    assert final.status_code == 200, final.text
    assert final.json()["estado"] == "PAGADO"
    assert final.json()["saldo"] == "0.00"
    assert abonar("ADELANTO", "REF-0003", "1.00").status_code == 409
    movimientos = client.get(f"{url}/{pago_id}/movimientos")
    assert movimientos.status_code == 200
    assert len(movimientos.json()) == 2
    comprobante = client.get(
        f"{url}/{pago_id}/movimientos/{movimientos.json()[0]['id']}/comprobante"
    )
    assert comprobante.status_code == 200
    assert comprobante.content.startswith(b"%PDF-")
