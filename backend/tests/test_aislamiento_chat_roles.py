"""Prohibiciones de acceso cruzado a mensajes y expedientes por rol."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CuentaAcceso, Miembro, Tenant
from tests.conftest import AuthPrueba


@pytest.mark.parametrize(
    "rol",
    ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO", "GESTOR"],
)
def test_chat_no_permita_contactos_entre_tenants(
    client: TestClient, session: Session, auth_prueba: AuthPrueba, rol: str
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    otro = Tenant(nombre="Tenant externo aislado", codigo="EXT-SEG-01", estado="ACTIVO")
    session.add(otro)
    session.flush()
    miembro = Miembro(
        tenant_id=otro.id,
        codigo="EXTERNO01",
        nombre="Contacto externo",
        rol="USUARIO",
        activo=True,
    )
    session.add(miembro)
    session.flush()
    cuenta = CuentaAcceso(
        tenant_id=otro.id,
        miembro_id=miembro.id,
        login="EXTERNO01",
        password_hash="hash-prueba",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta)
    session.commit()
    listado = client.get("/api/v1/chat/contactos")
    if rol == "SUPERADMIN":
        assert listado.status_code == 403, listado.text
        return
    assert listado.status_code == 200, listado.text
    assert str(cuenta.id) not in {x["cuenta_id"] for x in listado.json()}
    enviado = client.post(
        "/api/v1/chat/mensajes",
        data={"destinatario_cuenta_id": str(cuenta.id), "texto": "Bloqueado"},
    )
    assert enviado.status_code == 404, enviado.text
    lectura = client.get("/api/v1/chat/mensajes", params={"con": str(cuenta.id)})
    assert lectura.status_code == 404, lectura.text


@pytest.mark.parametrize(
    "rol",
    ["GERENTE", "RESPONSABLE", "USUARIO", "GESTOR"],
)
def test_sin_identidad_admin_no_puede_recalcular_expedientes(
    client: TestClient, auth_prueba: AuthPrueba, rol: str
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    respuesta = client.post("/api/v1/expedientes/recalcular")
    assert respuesta.status_code in (403, 422), respuesta.text
