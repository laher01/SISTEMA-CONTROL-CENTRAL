"""Issue #311: ninguna sesión existente sobrevive a suspender su tenant."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_contexto_actual
from app.core.config import Settings
from app.main import app
from app.models import CuentaAcceso, Miembro, Tenant
from app.security import contexto_desde_token, crear_sesion


class SesionFalsa:
    def __init__(self, estado: str | None, cruzado: bool = False) -> None:
        tenant_id = uuid4()
        self.tenant = SimpleNamespace(id=tenant_id, estado=estado) if estado is not None else None
        self.cuenta = SimpleNamespace(
            id=uuid4(),
            tenant_id=tenant_id,
            activo=True,
            deleted_at=None,
            gestor_id=None,
            miembro_id=uuid4(),
            cambio_clave_obligatorio=False,
        )
        self.miembro = SimpleNamespace(
            id=self.cuenta.miembro_id,
            rol="ADMINISTRADOR",
            activo=True,
            deleted_at=None,
            codigo="ADMIN01",
            nombre="Administración de prueba",
        )
        self.sesion = SimpleNamespace(
            tenant_id=uuid4() if cruzado else tenant_id,
            cuenta_id=self.cuenta.id,
            expira_at=datetime.now(UTC) + timedelta(hours=1),
            revocada_at=None,
            ultima_actividad=None,
        )
        self.flushes = 0

    def scalar(self, _consulta: object) -> object:
        return self.sesion

    def get(self, modelo: object, _identificador: object) -> object:
        if modelo is CuentaAcceso:
            return self.cuenta
        if modelo is Tenant:
            return self.tenant
        if modelo is Miembro:
            return self.miembro
        raise AssertionError("Modelo inesperado")

    def flush(self) -> None:
        self.flushes += 1


@pytest.mark.parametrize(
    ("estado", "cruzado"),
    [
        ("SUSPENDIDO", False),
        ("INACTIVO", False),
        (None, False),
        ("ACTIVO", True),
    ],
)
def test_sesion_ajena_o_de_tenant_inactivo_se_revoca(estado: str | None, cruzado: bool) -> None:
    session = SesionFalsa(estado, cruzado)
    assert contexto_desde_token(session, "token-ficticio") is None
    assert session.sesion.revocada_at is not None
    assert session.flushes == 1


def test_sesion_de_tenant_activo_conserva_acceso() -> None:
    session = SesionFalsa("ACTIVO")
    contexto = contexto_desde_token(session, "token-ficticio")
    assert contexto is not None
    assert contexto.tenant_id == session.tenant.id
    assert contexto.rol == "ADMINISTRADOR"
    assert session.sesion.revocada_at is None
    assert session.flushes == 0


def test_http_suspension_reactivacion_y_sesion_nueva(
    client: TestClient,
    session: Session,
    settings: Settings,
) -> None:
    """Prueba HTTP real sin el bypass de autenticación de la fixture estándar."""
    tenant = Tenant(nombre="Organización prueba 311", estado="ACTIVO")
    session.add(tenant)
    session.flush()
    miembro = Miembro(
        tenant_id=tenant.id,
        codigo="ADMIN01",
        nombre="Propietario de prueba",
        rol="ADMINISTRADOR",
        activo=True,
    )
    session.add(miembro)
    session.flush()
    cuenta = CuentaAcceso(
        tenant_id=tenant.id,
        login="ADMIN01",
        password_hash="hash-de-prueba",
        miembro_id=miembro.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta)
    session.flush()
    _, token_anterior = crear_sesion(session, cuenta, "ADMINISTRADOR")
    session.commit()
    app.dependency_overrides.pop(get_contexto_actual, None)
    client.cookies.set(settings.session_cookie_name, token_anterior)

    assert client.get("/api/v1/auth/me").status_code == 200

    tenant.estado = "SUSPENDIDO"
    session.commit()
    assert client.get("/api/v1/auth/me").status_code == 401

    tenant.estado = "ACTIVO"
    session.commit()
    assert client.get("/api/v1/auth/me").status_code == 401

    _, token_nuevo = crear_sesion(session, cuenta, "ADMINISTRADOR")
    session.commit()
    client.cookies.set(settings.session_cookie_name, token_nuevo)
    assert client.get("/api/v1/auth/me").status_code == 200
