"""Issue #311: ninguna sesión existente sobrevive a suspender su tenant."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models import CuentaAcceso, Miembro, Tenant
from app.security import contexto_desde_token


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
def test_sesion_ajena_o_de_tenant_inactivo_se_revoca(
    estado: str | None, cruzado: bool
) -> None:
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
