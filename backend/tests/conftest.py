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
from app.models import Base, CuentaAcceso, Documento, Expediente, Gestor, Miembro
from app.security import ContextoAcceso
from app.services.expedientes import obtener_tenant

TEST_DATABASE_URL = os.environ.get("FC_TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")


def completar_facturas_de_prueba(session: Session) -> None:
    """Adjunta un documento sintético a expedientes sembrados como facturas.

    Varias pruebas históricas construían solo la cabecera de la factura. La
    aplicación ahora exige un documento activo para contabilizarla, así que
    estas pruebas deben representar el expediente completo.
    """
    session.flush()
    expedientes = session.query(Expediente).filter(Expediente.deleted_at.is_(None)).all()
    for expediente in expedientes:
        if any(documento.deleted_at is None for documento in expediente.documentos):
            continue
        if expediente.documentos:
            continue
        session.add(
            Documento(
                tenant_id=expediente.tenant_id,
                expediente_id=expediente.id,
                tipo_documento="FACT",
                estado="RELACIONADO",
                sha256=uuid.uuid4().hex * 2,
                nombre_original=f"{expediente.serie}-{expediente.correlativo}.pdf",
                mime_type="application/pdf",
                tamano_bytes=1,
                ruta_storage=f"test/{uuid.uuid4().hex}.pdf",
                formato_origen="PRUEBA",
            )
        )
    session.flush()
    # El cliente de prueba consulta con una sesión distinta (como la API real).
    # Publicar los fixtures antes de verificar la respuesta en PostgreSQL.
    session.commit()


class Reloj:
    def __init__(self) -> None:
        self.hoy = date(2026, 9, 15)


class AuthPrueba:
    def __init__(
        self, contexto: ContextoAcceso, gestor_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> None:
        self.contexto = contexto
        self.gestor_id = gestor_id
        self.usuario_id = usuario_id

    def como_superadmin(self) -> None:
        self.contexto = ContextoAcceso(
            cuenta_id=self.contexto.cuenta_id,
            tenant_id=self.contexto.tenant_id,
            rol="SUPERADMIN",
            miembro_id=self.contexto.miembro_id,
            gestor_id=None,
            usuario_id=None,
            codigo="ADMIN01",
            nombre="Superadministrador de pruebas",
            cambio_clave_obligatorio=False,
        )

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

    def como_gerente(self) -> None:
        self.contexto = ContextoAcceso(
            cuenta_id=self.contexto.cuenta_id,
            tenant_id=self.contexto.tenant_id,
            rol="GERENTE",
            miembro_id=self.contexto.miembro_id,
            gestor_id=None,
            usuario_id=None,
            codigo="GERENTE-TEST",
            nombre="Gerente de pruebas",
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
        session.flush()
        gestor = Gestor(
            tenant_id=tenant.id,
            codigo="TESTGST",
            nombre="Gestor de pruebas",
            usuario_id=usuario.id,
        )
        session.add(gestor)
        session.flush()
        cuenta = CuentaAcceso(
            tenant_id=tenant.id,
            login="TESTUSR",
            password_hash="test-hash",
            miembro_id=usuario.id,
            gestor_id=None,
            activo=True,
            cambio_clave_obligatorio=False,
        )
        session.add(cuenta)
        session.commit()
        contexto = ContextoAcceso(
            cuenta_id=cuenta.id,
            tenant_id=tenant.id,
            rol="USUARIO",
            miembro_id=usuario.id,
            gestor_id=None,
            usuario_id=usuario.id,
            codigo=usuario.codigo,
            nombre=usuario.nombre,
            cambio_clave_obligatorio=False,
        )
    return AuthPrueba(contexto, gestor.id, usuario.id)


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
    app.state.auth_prueba = auth_prueba
    app.state.auto_gestor_upload_for_tests = True
    with TestClient(app, base_url="https://testserver") as c:
        post_original = c.post

        def post_con_gestor_de_prueba(url: str, *args: object, **kwargs: object):
            rutas_carga = {
                "/api/v1/documentos",
                "/api/v1/documentos/paquete",
                "/api/v1/documentos/lote-imagenes",
            }
            contexto_original = auth_prueba.contexto
            if (
                app.state.auto_gestor_upload_for_tests
                and url in rutas_carga
                and contexto_original.rol in {"USUARIO", "ADMINISTRADOR"}
            ):
                auth_prueba.como_gestor(auth_prueba.gestor_id, auth_prueba.usuario_id)
            try:
                return post_original(url, *args, **kwargs)
            finally:
                auth_prueba.contexto = contexto_original

        c.post = post_con_gestor_de_prueba  # type: ignore[method-assign]
        yield c
    app.dependency_overrides.clear()
