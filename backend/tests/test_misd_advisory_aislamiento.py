"""Regresión PostgreSQL: aislamiento entre tenants y liberación de advisory lock."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.services.bloqueo_financiero_misd import bloquear_tenant_financiero
from tests.conftest import AuthPrueba


def _requiere_postgresql(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("La prueba requiere PostgreSQL y advisory locks reales")


def test_tenants_distintos_no_se_bloquean(
    engine: Engine, auth_prueba: AuthPrueba
) -> None:
    _requiere_postgresql(engine)
    fabrica = sessionmaker(engine)
    retenido = Event()
    liberar = Event()
    independiente = Event()
    tenant_a = auth_prueba.contexto.tenant_id
    tenant_b = uuid4()

    def primero() -> None:
        with fabrica.begin() as sesion:
            bloquear_tenant_financiero(sesion, tenant_a)
            retenido.set()
            assert liberar.wait(timeout=15)

    def segundo() -> None:
        assert retenido.wait(timeout=15)
        with fabrica.begin() as sesion:
            bloquear_tenant_financiero(sesion, tenant_b)
            independiente.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        tarea_a = pool.submit(primero)
        tarea_b = pool.submit(segundo)
        try:
            assert retenido.wait(timeout=15)
            assert independiente.wait(timeout=10)
        finally:
            liberar.set()
        tarea_a.result(timeout=20)
        tarea_b.result(timeout=20)


def test_rollback_libera_lock_financiero(
    engine: Engine, auth_prueba: AuthPrueba
) -> None:
    _requiere_postgresql(engine)
    fabrica = sessionmaker(engine)
    tenant_id = auth_prueba.contexto.tenant_id
    retenido = Event()
    liberar = Event()
    adquirido = Event()

    def primero() -> None:
        with fabrica() as sesion:
            bloquear_tenant_financiero(sesion, tenant_id)
            retenido.set()
            assert liberar.wait(timeout=15)
            sesion.rollback()

    def segundo() -> None:
        assert retenido.wait(timeout=15)
        with fabrica.begin() as sesion:
            bloquear_tenant_financiero(sesion, tenant_id)
            adquirido.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        tarea_a = pool.submit(primero)
        tarea_b = pool.submit(segundo)
        try:
            assert retenido.wait(timeout=15)
            assert not adquirido.wait(timeout=0.3)
        finally:
            liberar.set()
        tarea_a.result(timeout=20)
        tarea_b.result(timeout=20)
    assert adquirido.is_set()
