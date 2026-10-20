"""Regresión HTTP MISD: solicitar y resolver respetan el advisory lock financiero."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import replace
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import CuentaAcceso, Miembro
from app.services.bloqueo_financiero_misd import bloquear_tenant_financiero
from tests.conftest import AuthPrueba
from tests.xml import factura


@pytest.mark.parametrize("operacion", ["solicitar", "resolver"])
def test_misd_http_espera_lock_financiero(
    engine: Engine,
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
    operacion: str,
) -> None:
    """La petición HTTP espera la liberación del bloqueo de otra conexión."""
    if engine.dialect.name != "postgresql":
        pytest.skip("Requiere conexiones PostgreSQL independientes")

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": (f"bloqueo-{operacion}.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]

    if operacion == "solicitar":
        ruta = "/api/v1/misd/solicitudes"
        datos = {"expediente_id": expediente_id, "motivo": "Retirada bajo concurrencia"}
        esperado = 201
    else:
        creada = client.post(
            "/api/v1/misd/solicitudes",
            json={"expediente_id": expediente_id, "motivo": "Revisión concurrente"},
        )
        assert creada.status_code == 201, creada.text
        admin = Miembro(
            tenant_id=auth_prueba.contexto.tenant_id,
            codigo="ADMIN-CONCURRENCIA",
            nombre="Administración de concurrencia",
            rol="ADMINISTRADOR",
            activo=True,
        )
        session.add(admin)
        session.flush()
        cuenta = CuentaAcceso(
            tenant_id=auth_prueba.contexto.tenant_id,
            login="admin-concurrencia",
            password_hash="hash-pruebas",
            miembro_id=admin.id,
            activo=True,
            cambio_clave_obligatorio=False,
        )
        session.add(cuenta)
        session.commit()
        auth_prueba.contexto = replace(
            auth_prueba.contexto,
            cuenta_id=cuenta.id,
            miembro_id=admin.id,
            rol="ADMINISTRADOR",
            usuario_id=None,
            gestor_id=None,
        )
        ruta = f"/api/v1/misd/solicitudes/{creada.json()['id']}/resolver"
        datos = {"aprobar": True, "motivo": "Aprobada después de esperar bloqueo"}
        esperado = 200

    fabrica = sessionmaker(engine)
    iniciada = Event()

    def realizar_peticion() -> object:
        iniciada.set()
        return client.post(ruta, json=datos)

    with fabrica() as tenedora:
        bloquear_tenant_financiero(tenedora, auth_prueba.contexto.tenant_id)
        with ThreadPoolExecutor(max_workers=1) as pool:
            resultado = pool.submit(realizar_peticion)
            try:
                assert iniciada.wait(timeout=10)
                with pytest.raises(FutureTimeoutError):
                    resultado.result(timeout=0.3)
            finally:
                tenedora.rollback()
            respuesta = resultado.result(timeout=20)

    assert respuesta.status_code == esperado, respuesta.text
