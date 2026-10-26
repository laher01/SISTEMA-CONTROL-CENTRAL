"""Exclusión transaccional compartida entre MISD y pagos en PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.services.bloqueo_financiero_misd import bloquear_tenant_financiero
from app.services.bloqueo_produccion import bloquear_tenant_para_produccion
from tests.conftest import AuthPrueba


@pytest.mark.parametrize("primero_financiero", [True, False])
def test_lock_tenant_serializa_transacciones_postgresql(
    engine: Engine,
    auth_prueba: AuthPrueba,
    primero_financiero: bool,
) -> None:
    """Ambos nombres de contrato compiten por exactamente el mismo lock."""
    if engine.dialect.name != "postgresql":
        pytest.skip("Se requieren advisory locks transaccionales PostgreSQL")

    tenant_id: UUID = auth_prueba.contexto.tenant_id
    primera_bloqueada = Event()
    liberar_primera = Event()
    segunda_adquirida = Event()
    fabrica = sessionmaker(engine)
    primera_funcion = (
        bloquear_tenant_financiero if primero_financiero else bloquear_tenant_para_produccion
    )
    segunda_funcion = (
        bloquear_tenant_para_produccion if primero_financiero else bloquear_tenant_financiero
    )

    def primera() -> None:
        with fabrica.begin() as sesion:
            primera_funcion(sesion, tenant_id)
            primera_bloqueada.set()
            assert liberar_primera.wait(timeout=15)

    def segunda() -> None:
        assert primera_bloqueada.wait(timeout=15)
        with fabrica.begin() as sesion:
            segunda_funcion(sesion, tenant_id)
            segunda_adquirida.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futuro_a = pool.submit(primera)
        futuro_b = pool.submit(segunda)
        try:
            assert primera_bloqueada.wait(timeout=15)
            assert not segunda_adquirida.wait(timeout=0.3)
        finally:
            liberar_primera.set()
        futuro_a.result(timeout=20)
        futuro_b.result(timeout=20)
    assert segunda_adquirida.is_set()
