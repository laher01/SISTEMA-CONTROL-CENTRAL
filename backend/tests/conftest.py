import os
import uuid
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_contexto_actual, get_hoy
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.main import app
from app.models import Base, Miembro
from app.security import ContextoAcceso
from app.services.expedientes import obtener_tenant

TEST_DATABASE_URL = os.environ.get("FC_TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")


class Reloj:
    def __init__(self) -> None:
        self.hoy = date(2026, 9, 15)


class AuthPrueba:
    def __init__(self, contexto: ContextoAcceso) -> None:
        self.contexto = contexto

    def como_admin(self) -> None:
        self.contexto = ContextoAcceso(
            cuenta_id=self.contexto.cuenta_id,
            tenant_id=self.contexto.tenant_id,
            rol="ADMINISTRADOR",
            miembro_id=self.contexto.miembro_id,
            gestor_id=None,
            usuario_id=None,
            codigo="ADMIN-TEST",
            nombre="Administrador de pruebas",
            cambio_clave_obligatorio=False,
        )

    def como_usuario(self, usuario_id: uuid.UUID, codigo: str = "USUARIO") -> None:
        self.contexto = ContextoAcceso(
            cuenta_id=self.contexto.cuenta_id,
            tenant_id=self.contexto.tenant_id,
            rol="USUARIO",
            miembro_id=usuario_id,
            gestor_id=None,
            usuario_id=usuario_id,
            codigo=codigo,
            nombre=codigo,
            cambio_clave_obligatorio=False,
        )

    def como_gestor(
        self,
        gestor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        codigo: str = "GESTOR",
    ) -> None:
        self.contexto = ContextoAcceso(
            cuenta_id=self.contexto.cuenta_id,
            tenant_id=self.contexto.tenant_id,
            rol="GESTOR",
            miembro_id=None,
            gestor_id=gestor_id,
            usuario_id=usuario_id,
            codigo=codigo,
            nombre=codigo,
            cambio_clave_obligatorio=False,
        )


@pytest.fixture
def engine() -> Iterator[Engine]:
    if TEST_DATABASE_URL.startswith("sqlite"):
        motor = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        motor = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(motor)
    Base.metadata.create_all(motor)
    yield motor
    Base.metadata.drop_all(motor)
    motor.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with sessionmaker(engine, expire_on_commit=False)() as s:
        yield s


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(storage_dir=tmp_path / "storage", tenant_default="pruebas")


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def auth_prueba(engine: Engine, settings: Settings) -> AuthPrueba:
    fabrica = sessionmaker(engine, expire_on_commit=False)
    with fabrica() as session:
        tenant = obtener_tenant(session, settings.tenant_default)
        usuario = Miembro(
            tenant_id=tenant.id,
            codigo="TESTUSR",
            nombre="Usuario de pruebas",
            rol="USUARIO",
            activo=True,
        )
        session.add(usuario)
        session.commit()
        contexto = ContextoAcceso(
            cuenta_id=uuid.uuid4(),
            tenant_id=tenant.id,
            rol="USUARIO",
            miembro_id=usuario.id,
            gestor_id=None,
            usuario_id=usuario.id,
            codigo=usuario.codigo,
            nombre=usuario.nombre,
            cambio_clave_obligatorio=False,
        )
    return AuthPrueba(contexto)


@pytest.fixture
def client(
    engine: Engine,
    settings: Settings,
    reloj: Reloj,
    auth_prueba: AuthPrueba,
) -> Iterator[TestClient]:
    fabrica = sessionmaker(engine, expire_on_commit=False)

    def sesion() -> Iterator[Session]:
        with fabrica() as s:
            yield s

    app.dependency_overrides[get_session] = sesion
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_hoy] = lambda: reloj.hoy
    app.dependency_overrides[get_contexto_actual] = lambda: auth_prueba.contexto
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    app.dependency_overrides.clear()
