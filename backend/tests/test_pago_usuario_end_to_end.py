"""Coincidencia entre cotizar y programar: facturas, saldos antiguos y adelantos."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AdelantoERP, Empresa, Expediente, Miembro, SaldoCompraERP
from tests.conftest import AuthPrueba


def test_cotizacion_y_programacion_coinciden_con_saldo_historico(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    tenant_id = auth_prueba.contexto.tenant_id
    usuario = session.query(Miembro).filter_by(tenant_id=tenant_id, codigo="TESTUSR").one()
    usuario.porcentaje_con_agente = Decimal("2.35")
    usuario.porcentaje_sin_agente = Decimal("2.85")
    receptor_agente = Empresa(
        tenant_id=tenant_id, ruc="20111111111", razon_social="Empresa agente", agente_retencion=True
    )
    receptor_libre = Empresa(
        tenant_id=tenant_id, ruc="20222222222", razon_social="Empresa sin agente", agente_retencion=False
    )
    emisor = Empresa(tenant_id=tenant_id, ruc="20333333333", razon_social="Proveedor")
    session.add_all([receptor_agente, receptor_libre, emisor])
    session.flush()
    for receptor, importe, correlativo in (
        (receptor_agente, "20000.00", "000001"),
        (receptor_libre, "15000.00", "000002"),
    ):
        session.add(
            Expediente(
                tenant_id=tenant_id,
                receptor_id=receptor.id,
                emisor_id=emisor.id,
                usuario_id=usuario.id,
                tipo_comprobante="01",
                serie="F001",
                correlativo=correlativo,
                fecha_emision=date(2026, 9, 10),
                moneda="PEN",
                importe_total=Decimal(importe),
            )
        )
    saldo = SaldoCompraERP(
        tenant_id=tenant_id,
        usuario_id=usuario.id,
        periodo_mes=date(2026, 8, 1),
        moneda="PEN",
        monto=Decimal("1000.00"),
        detalle="Saldo de producción agosto",
        creado_por_cuenta_id=auth_prueba.contexto.cuenta_id,
    )
    adelanto = AdelantoERP(
        tenant_id=tenant_id,
        usuario_id=usuario.id,
        fecha=date(2026, 9, 7),
        moneda="PEN",
        monto=Decimal("150.00"),
        descripcion="Adelanto de prueba",
    )
    session.add_all([saldo, adelanto])
    session.commit()

    datos = {
        "usuario_id": str(usuario.id),
        "desde": "2026-09-01",
        "hasta": "2026-09-30",
        "moneda": "PEN",
        "saldo_ids": [str(saldo.id)],
        "porcentajes_saldos": {str(saldo.id): "2.00"},
        "adelanto_ids": [str(adelanto.id)],
    }
    cotizacion = client.post("/api/v1/responsable/pagos/cotizar", json=datos)
    assert cotizacion.status_code == 200, cotizacion.text
    resultado = cotizacion.json()
    assert Decimal(resultado["produccion"]) == Decimal("35000.00")
    assert Decimal(resultado["saldos_agregados"]) == Decimal("1000.00")
    assert Decimal(resultado["bruto"]) == Decimal("917.50")
    assert Decimal(resultado["adelantos"]) == Decimal("150.00")
    assert Decimal(resultado["neto"]) == Decimal("767.50")

    programacion = client.post("/api/v1/responsable/pagos/programar", json=datos)
    assert programacion.status_code == 201, programacion.text
    liquidaciones = client.get(
        "/api/v1/responsable/pagos/liquidaciones",
        params={"usuario_id": str(usuario.id)},
    )
    assert liquidaciones.status_code == 200, liquidaciones.text
    pago = liquidaciones.json()[0]
    assert Decimal(pago["bruto"]) == Decimal(resultado["bruto"])
    assert Decimal(pago["adelantos"]) == Decimal(resultado["adelantos"])
    assert Decimal(pago["saldo"]) == Decimal(resultado["neto"])

    duplicado = client.post("/api/v1/responsable/pagos/programar", json=datos)
    assert duplicado.status_code == 409


def test_saldo_sin_porcentaje_historico_rechazado(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    tenant_id = auth_prueba.contexto.tenant_id
    usuario = session.query(Miembro).filter_by(tenant_id=tenant_id, codigo="TESTUSR").one()
    saldo = SaldoCompraERP(
        tenant_id=tenant_id,
        usuario_id=usuario.id,
        periodo_mes=date(2026, 8, 1),
        moneda="PEN",
        monto=Decimal("1000.00"),
        detalle="Saldo historico",
        creado_por_cuenta_id=auth_prueba.contexto.cuenta_id,
    )
    session.add(saldo)
    session.commit()
    respuesta = client.post(
        "/api/v1/responsable/pagos/cotizar",
        json={
            "usuario_id": str(usuario.id),
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": "PEN",
            "saldo_ids": [str(saldo.id)],
        },
    )
    assert respuesta.status_code == 422
