"""Cobertura MISD de programación HTTP de liquidación y retirada protegida."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import date
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Expediente, PagoERP, SolicitudRetiroMISD
from app.services.bloqueo_financiero_misd import bloquear_tenant_financiero
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_programacion_pago_http_bloquea_retiro_posterior(
    engine: Engine, client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("Requiere PostgreSQL con advisory locks transaccionales")

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("liquidacion-http-misd.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Corrección de factura duplicada"},
    )
    assert creada.status_code == 201, creada.text
    solicitud_id = creada.json()["id"]
    expediente = session.get(Expediente, expediente_id)
    assert expediente is not None
    assert expediente.usuario_id is not None
    usuario_id = expediente.usuario_id
    contexto_usuario = auth_prueba.contexto
    auth_prueba.como_admin()

    fabrica = sessionmaker(engine)
    iniciada = Event()

    def programar() -> object:
        iniciada.set()
        return client.post(
            "/api/v1/responsable/pagos/programar",
            json={
                "usuario_id": str(usuario_id),
                "desde": date(2026, 9, 1).isoformat(),
                "hasta": date(2026, 9, 30).isoformat(),
                "moneda": expediente.moneda,
                "porcentaje_manual": "1.0000",
            },
        )

    with fabrica() as tenedora:
        bloquear_tenant_financiero(tenedora, contexto_usuario.tenant_id)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pendiente = pool.submit(programar)
            try:
                assert iniciada.wait(timeout=10)
                with pytest.raises(FutureTimeoutError):
                    pendiente.result(timeout=0.3)
            finally:
                tenedora.rollback()
            programada = pendiente.result(timeout=20)

    assert programada.status_code == 201, programada.text
    assert session.query(PagoERP).filter(PagoERP.usuario_id == usuario_id).count() == 1
    auth_prueba.contexto = contexto_usuario
    retirada = client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar")
    assert retirada.status_code == 409, retirada.text
    session.expire_all()
    assert session.get(Expediente, expediente_id).deleted_at is None
    assert session.get(SolicitudRetiroMISD, solicitud_id).estado != "EJECUTADA"
