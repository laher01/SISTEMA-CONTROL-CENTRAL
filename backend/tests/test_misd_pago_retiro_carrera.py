"""Regresión HTTP: una liquidación confirmada impide ejecutar retirada MISD."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from decimal import Decimal
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Expediente, PagoERP, SolicitudRetiroMISD
from app.services.bloqueo_financiero_misd import bloquear_tenant_financiero
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_pago_concurrente_impide_retirada_misd(
    engine: Engine, client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("Requiere PostgreSQL con dos conexiones")

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("pago-concurrente-misd.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Retirada documental concurrente"},
    )
    assert creada.status_code == 201, creada.text
    solicitud_id = creada.json()["id"]
    expediente = session.get(Expediente, expediente_id)
    assert expediente is not None
    assert expediente.usuario_id is not None

    iniciada = Event()
    fabrica = sessionmaker(engine)

    def retirar() -> object:
        iniciada.set()
        return client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar")

    with fabrica() as liquidacion:
        bloquear_tenant_financiero(liquidacion, auth_prueba.contexto.tenant_id)
        liquidacion.add(
            PagoERP(
                tenant_id=expediente.tenant_id,
                usuario_id=expediente.usuario_id,
                creado_por_cuenta_id=auth_prueba.contexto.cuenta_id,
                periodo_desde=expediente.fecha_emision,
                periodo_hasta=expediente.fecha_emision,
                moneda=expediente.moneda,
                produccion_total=Decimal("100.00"),
                porcentaje=Decimal("1.0000"),
                bruto=Decimal("1.00"),
                saldo=Decimal("1.00"),
                estado="PROGRAMADO",
            )
        )
        liquidacion.flush()
        with ThreadPoolExecutor(max_workers=1) as pool:
            respuesta_futura = pool.submit(retirar)
            try:
                assert iniciada.wait(timeout=10)
                with pytest.raises(FutureTimeoutError):
                    respuesta_futura.result(timeout=0.3)
            finally:
                liquidacion.commit()
            respuesta = respuesta_futura.result(timeout=20)

    assert respuesta.status_code == 409, respuesta.text
    session.expire_all()
    assert session.get(Expediente, expediente_id).deleted_at is None
    assert session.get(SolicitudRetiroMISD, solicitud_id).estado != "EJECUTADA"
