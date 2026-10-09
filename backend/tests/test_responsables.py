import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Miembro
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_responsable_solo_ve_sus_usuarios(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-PRUEBA",
        nombre="Responsable pruebas",
        rol="RESPONSABLE",
        activo=True,
    )
    otro = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-OTRO",
        nombre="Otro Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add_all([responsable, otro])
    session.flush()
    usuario_propio = Miembro(
        tenant_id=tenant_id, codigo="USER-PROP", nombre="Usuario propio",
        rol="USUARIO", activo=True, responsable_id=responsable.id,
    )
    usuario_ajeno = Miembro(
        tenant_id=tenant_id, codigo="USER-AJENO", nombre="Usuario ajeno",
        rol="USUARIO", activo=True, responsable_id=otro.id,
    )
    session.add_all([usuario_propio, usuario_ajeno])
    session.commit()
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=auth_prueba.contexto.cuenta_id,
        tenant_id=tenant_id,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        gestor_id=None,
        usuario_id=None,
        codigo=responsable.codigo,
        nombre=responsable.nombre,
        cambio_clave_obligatorio=False,
    )
    respuesta = client.get("/api/v1/miembros/mis-usuarios")
    assert respuesta.status_code == 200, respuesta.text
    assert [u["codigo"] for u in respuesta.json()] == ["USER-PROP"]
    assert client.get("/api/v1/dashboard/resumen").status_code == 403
    assert client.get("/api/v1/miembros").status_code == 403


def test_asignacion_solo_administracion_y_mismo_tenant(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id, codigo="RESP01", nombre="Resp", rol="RESPONSABLE", activo=True
    )
    session.add(responsable)
    session.commit()
    url = f"/api/v1/miembros/{auth_prueba.contexto.miembro_id}/responsable"
    assert client.put(url, json={"responsable_id": str(responsable.id)}).status_code == 403
    auth_prueba.como_admin()
    r = client.put(url, json={"responsable_id": str(responsable.id)})
    assert r.status_code == 200, r.text
    assert r.json()["responsable_id"] == str(responsable.id)
    assert client.put(url, json={"responsable_id": str(uuid.uuid4())}).status_code == 422
