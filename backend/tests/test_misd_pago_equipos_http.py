"""Concurrencia HTTP de pagos Gestor/Responsable contra retiradas MISD."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import date
from decimal import Decimal
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Empresa, Expediente, Gestor, Miembro
from app.services.bloqueo_financiero_misd import bloquear_tenant_financiero
from tests.conftest import AuthPrueba
from tests.test_pagos_responsables import _preparar
from tests.xml import factura


@pytest.mark.parametrize("tipo_pago", ["gestor", "responsable"])
def test_pago_http_equipo_espera_lock_y_protege_retiro(
    engine: Engine,
    session: Session,
    client: TestClient,
    auth_prueba: AuthPrueba,
    tipo_pago: str,
) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("Se requieren advisory locks PostgreSQL")

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": (f"concurrencia-{tipo_pago}.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    solicitud = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Control concurrente de liquidación"},
    )
    assert solicitud.status_code == 201, solicitud.text
    solicitud_id = solicitud.json()["id"]
    contexto_usuario = auth_prueba.contexto
    expediente = session.get(Expediente, expediente_id)
    assert expediente is not None

    if tipo_pago == "gestor":
        gestor = Gestor(
            tenant_id=contexto_usuario.tenant_id,
            codigo="GEST-MISD-LOCK",
            nombre="Gestor concurrencia",
            usuario_id=contexto_usuario.usuario_id,
            porcentaje_comision=Decimal("3.0000"),
        )
        session.add(gestor)
        session.flush()
        expediente.gestor_id = gestor.id
        empresa = session.get(Empresa, expediente.receptor_id)
        assert empresa is not None
        empresa.autorizada = True
        session.commit()
        ruta = "/api/v1/pagos-gestores/programar"
        payload = {
            "gestor_id": str(gestor.id),
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": expediente.moneda,
        }
    else:
        responsable_id, _ = _preparar(session, auth_prueba)
        usuario = session.scalar(
            select(Miembro).where(
                Miembro.tenant_id == contexto_usuario.tenant_id,
                Miembro.codigo == "USU-01",
            )
        )
        assert usuario is not None
        expediente.usuario_id = usuario.id
        expediente.gerente_id = contexto_usuario.miembro_id
        session.commit()
        auth_prueba.como_gerente()
        ruta = "/api/v1/pagos-responsables/programar"
        payload = {
            "responsable_id": responsable_id,
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": expediente.moneda,
        }

    iniciada = Event()

    def programar() -> object:
        iniciada.set()
        return client.post(ruta, json=payload)

    with sessionmaker(engine)() as tenedora:
        bloquear_tenant_financiero(tenedora, contexto_usuario.tenant_id)
        with ThreadPoolExecutor(max_workers=1) as pool:
            futuro = pool.submit(programar)
            try:
                assert iniciada.wait(timeout=10)
                with pytest.raises(FutureTimeoutError):
                    futuro.result(timeout=0.3)
            finally:
                tenedora.rollback()
            pago = futuro.result(timeout=20)

    assert pago.status_code == 201, pago.text
    auth_prueba.contexto = contexto_usuario
    retiro = client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar")
    assert retiro.status_code == 409, retiro.text
    session.expire_all()
    assert session.get(Expediente, expediente_id).deleted_at is None
