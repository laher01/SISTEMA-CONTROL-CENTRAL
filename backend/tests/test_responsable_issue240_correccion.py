"""Cobertura del filtro financiero de autorización de receptora — Issue #240."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Miembro
from tests.conftest import AuthPrueba


def test_liquidacion_mixta_excluye_solo_importes_no_elegibles(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    """El expediente elegible se conserva y el pendiente no aumenta el pago."""
    auth_prueba.como_admin()
    tenant_id = auth_prueba.contexto.tenant_id
    usuario = session.query(Miembro).filter_by(tenant_id=tenant_id, codigo="TESTUSR").one()
    usuario.porcentaje_con_agente = Decimal("2.00")
    usuario.porcentaje_sin_agente = Decimal("2.00")
    emisor = Empresa(tenant_id=tenant_id, ruc="20123456789", razon_social="Emisor mixto")
    autorizado = Empresa(
        tenant_id=tenant_id, ruc="20987654321", razon_social="Autorizada", autorizada=True
    )
    pendiente = Empresa(
        tenant_id=tenant_id, ruc="20876543210", razon_social="No autorizada", autorizada=False
    )
    session.add_all([emisor, autorizado, pendiente])
    session.flush()
    for receptor, correlativo, importe, flag in (
        (autorizado, "000001", "1000.00", False),
        (pendiente, "000002", "2000.00", True),
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
                pendiente_aprobacion=flag,
            )
        )
    session.commit()
    datos = {
        "usuario_id": str(usuario.id),
        "desde": "2026-09-01",
        "hasta": "2026-09-30",
        "moneda": "PEN",
    }
    cotizacion = client.post("/api/v1/responsable/pagos/cotizar", json=datos)
    assert cotizacion.status_code == 200, cotizacion.text
    programacion = client.post("/api/v1/responsable/pagos/programar", json=datos)
    assert programacion.status_code == 201, programacion.text
    liquidaciones = client.get(
        "/api/v1/responsable/pagos/liquidaciones",
        params={"usuario_id": str(usuario.id)},
    )
    assert liquidaciones.status_code == 200, liquidaciones.text
    pago = liquidaciones.json()[0]
    assert Decimal(cotizacion.json()["produccion"]) == Decimal("1000.00")
    assert Decimal(cotizacion.json()["bruto"]) == Decimal("20.00")
    assert Decimal(pago["produccion_total"]) == Decimal("1000.00")
    assert Decimal(pago["bruto"]) == Decimal("20.00")
