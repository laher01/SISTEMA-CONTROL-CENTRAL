"""La Secretaría solo administra Responsables creados por su propia cuenta."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Miembro
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_secretaria_no_modifica_responsables_ajenos(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    actual = auth_prueba.contexto
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=actual.cuenta_id,
        tenant_id=actual.tenant_id,
        rol="SECRETARIA",
        miembro_id=actual.miembro_id,
        gestor_id=None,
        usuario_id=None,
        codigo="SECR-TEST",
        nombre="Secretaría de pruebas",
        cambio_clave_obligatorio=False,
    )
    propio = client.post("/api/v1/miembros/responsables-operativos", json={"nombre": "Marta Propia"})
    assert propio.status_code == 201, propio.text
    id_propio = propio.json()["miembro"]["id"]
    ajeno = Miembro(
        tenant_id=actual.tenant_id,
        codigo="RESP-AJENO-TEST",
        nombre="Responsable gerencia",
        rol="RESPONSABLE",
        activo=True,
        creado_por_cuenta_id=uuid.uuid4(),
    )
    # La referencia al creador debe existir: se reutiliza una cuenta real diferente
    # únicamente en las pruebas de permisos que no requieren resolver el creador.
    ajeno.creado_por_cuenta_id = None
    session.add(ajeno)
    session.commit()

    base = "/api/v1/miembros/responsables-operativos"
    listado = client.get(base + "/directorio")
    assert listado.status_code == 200, listado.text
    filas = {fila["id"]: fila for fila in listado.json()}
    assert filas[id_propio]["puede_gestionar"] is True
    assert filas[str(ajeno.id)]["puede_gestionar"] is False

    cambiar = client.patch(base + "/" + id_propio, json={"nombre": "Marta Actualizada"})
    assert cambiar.status_code == 200, cambiar.text
    assert client.patch(base + "/" + str(ajeno.id), json={"nombre": "Intrusión"}).status_code == 403
    assert client.post(base + "/" + str(ajeno.id) + "/desactivar").status_code == 403
    assert client.post(base + "/" + str(ajeno.id) + "/restablecer-acceso").status_code == 403
    session.refresh(ajeno)
    assert ajeno.activo is True
    assert ajeno.nombre == "Responsable gerencia"


def test_secretaria_desactiva_solo_responsable_sin_usuarios(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    actual = auth_prueba.contexto
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=actual.cuenta_id,
        tenant_id=actual.tenant_id,
        rol="SECRETARIA",
        miembro_id=actual.miembro_id,
        gestor_id=None,
        usuario_id=None,
        codigo="SECR-TEST",
        nombre="Secretaría de pruebas",
        cambio_clave_obligatorio=False,
    )
    nuevo = client.post("/api/v1/miembros/responsables-operativos", json={"nombre": "Marta Propia"})
    assert nuevo.status_code == 201, nuevo.text
    id_propio = nuevo.json()["miembro"]["id"]
    base = "/api/v1/miembros/responsables-operativos/" + id_propio
    usuario = Miembro(
        tenant_id=actual.tenant_id, codigo="USER-TEST-SECR",
        nombre="Usuario asignado", rol="USUARIO", activo=True,
        responsable_id=uuid.UUID(id_propio),
    )
    session.add(usuario)
    session.commit()
    assert client.post(base + "/desactivar").status_code == 409
    session.delete(usuario)
    session.commit()
    respuesta = client.post(base + "/desactivar")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "DESACTIVADO"
    assert client.post(base + "/restablecer-acceso").status_code == 409
