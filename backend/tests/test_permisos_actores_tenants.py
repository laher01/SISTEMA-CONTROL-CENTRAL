"""Permisos defensivos y aislamiento para actores operativos."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CuentaAcceso, Miembro, Tenant
from tests.conftest import AuthPrueba


def _contacto(session: Session, tenant_id, codigo: str, rol: str) -> str:
    miembro = Miembro(
        tenant_id=tenant_id, codigo=codigo, nombre=codigo, rol=rol, activo=True
    )
    session.add(miembro)
    session.flush()
    cuenta = CuentaAcceso(
        tenant_id=tenant_id,
        miembro_id=miembro.id,
        login=codigo,
        password_hash="hash-prueba",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta)
    session.commit()
    return str(cuenta.id)


@pytest.mark.parametrize(
    "rol",
    ["ADMINISTRADOR", "GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO", "GESTOR"],
)
def test_ningun_actor_cliente_puede_listar_tenants_globales(
    client: TestClient, auth_prueba: AuthPrueba, rol: str
) -> None:
    auth_prueba.contexto.rol = rol
    respuesta = client.get("/api/v1/configuracion/administraciones")
    assert respuesta.status_code == 403


def test_usuario_no_contacta_persona_de_otro_tenant(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    ajeno = Tenant(nombre="Empresa ajena", codigo="OTRA-001", estado="ACTIVO")
    session.add(ajeno)
    session.flush()
    cuenta_id = _contacto(session, ajeno.id, "OTRO-USUARIO", "USUARIO")

    listado = client.get("/api/v1/chat/contactos")
    assert listado.status_code == 200, listado.text
    assert cuenta_id not in {c["cuenta_id"] for c in listado.json()}
    enviado = client.post(
        "/api/v1/chat/mensajes",
        data={"destinatario_cuenta_id": cuenta_id, "texto": "No debe salir"},
    )
    assert enviado.status_code == 404


def test_admin_tenant_no_puede_crear_superadmin(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    respuesta = client.post(
        "/api/v1/miembros",
        json={"codigo": "SUPERDOS", "nombre": "Super Global", "rol": "SUPERADMIN"},
    )
    assert respuesta.status_code == 403
