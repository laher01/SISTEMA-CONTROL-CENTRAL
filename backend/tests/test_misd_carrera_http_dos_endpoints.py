"""Dos endpoints HTTP reales compiten por el lock financiero del mismo tenant."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from decimal import Decimal
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Empresa, Expediente, Gestor, PagoGestor
from app.services.bloqueo_financiero_misd import bloquear_tenant_financiero
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_pago_gestor_y_retiro_misd_http_simultaneos(
    engine: Engine, session: Session, client: TestClient, auth_prueba: AuthPrueba
) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("Prueba de carrera requiere PostgreSQL")

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("doble-carrera-gestor.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    solicitud = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Revisión simultánea de liquidación"},
    )
    assert solicitud.status_code == 201, solicitud.text
    expediente = session.get(Expediente, expediente_id)
    assert expediente is not None
    gestor = Gestor(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="GEST-CARRERA-HTTP",
        nombre="Gestor carrera real",
        usuario_id=auth_prueba.contexto.usuario_id,
        porcentaje_comision=Decimal("3.0000"),
    )
    session.add(gestor)
    session.flush()
    expediente.gestor_id = gestor.id
    empresa = session.get(Empresa, expediente.receptor_id)
    assert empresa is not None
    empresa.autorizada = True
    session.commit()
    tenant_id = auth_prueba.contexto.tenant_id

    pago_iniciado = Event()
    retiro_iniciado = Event()

    def pagar() -> object:
        pago_iniciado.set()
        return client.post(
            "/api/v1/pagos-gestores/programar",
            json={
                "gestor_id": str(gestor.id),
                "desde": "2026-09-01",
                "hasta": "2026-09-30",
                "moneda": expediente.moneda,
            },
        )

    def retirar() -> object:
        retiro_iniciado.set()
        return client.post(f"/api/v1/misd/solicitudes/{solicitud.json()['id']}/ejecutar")

    with sessionmaker(engine)() as tenedora:
        bloquear_tenant_financiero(tenedora, tenant_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            fp = pool.submit(pagar)
            fr = pool.submit(retirar)
            try:
                assert pago_iniciado.wait(timeout=10)
                assert retiro_iniciado.wait(timeout=10)
                with pytest.raises(FutureTimeoutError):
                    fp.result(timeout=0.3)
                with pytest.raises(FutureTimeoutError):
                    fr.result(timeout=0.3)
            finally:
                tenedora.rollback()
            pago = fp.result(timeout=25)
            retiro = fr.result(timeout=25)

    assert pago.status_code == 201, pago.text
    session.expire_all()
    expediente_final = session.get(Expediente, expediente_id)
    assert expediente_final is not None
    liquidacion = session.scalar(select(PagoGestor).where(PagoGestor.gestor_id == gestor.id))
    assert liquidacion is not None
    if retiro.status_code == 409:
        assert expediente_final.deleted_at is None
        assert Decimal(liquidacion.produccion_total) > 0
    else:
        assert retiro.status_code == 200, retiro.text
        assert expediente_final.deleted_at is not None
        assert Decimal(liquidacion.produccion_total) == 0
