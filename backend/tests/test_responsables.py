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
        tenant_id=tenant_id,
        codigo="USER-PROP",
        nombre="Usuario propio",
        rol="USUARIO",
        activo=True,
        responsable_id=responsable.id,
    )
    usuario_ajeno = Miembro(
        tenant_id=tenant_id,
        codigo="USER-AJENO",
        nombre="Usuario ajeno",
        rol="USUARIO",
        activo=True,
        responsable_id=otro.id,
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


def test_responsable_crea_usuario_en_su_equipo(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-CREA",
        nombre="Responsable Alta",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.commit()
    ruta = "/api/v1/miembros/mis-usuarios"
    datos = {"nombre": "Eduardo Ayala", "porcentaje_produccion": "1.7500"}
    assert client.post(ruta, json=datos).status_code == 403

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
    respuesta = client.post(ruta, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    creado = respuesta.json()
    assert creado["miembro"]["codigo"] == "EDA-001-US"
    assert creado["miembro"]["responsable_id"] == str(responsable.id)
    assert creado["miembro"]["rol"] == "USUARIO"
    assert creado["credencial"]["login"] == "EDA-001-US"
    assert creado["credencial"]["clave_temporal"]
    assert [x["codigo"] for x in client.get(ruta).json()] == ["EDA-001-US"]
    assert client.get("/api/v1/miembros").status_code == 403
    assert (
        client.post(
            "/api/v1/miembros", json={"nombre": "Gerente Fraude", "rol": "GERENTE"}
        ).status_code
        == 403
    )
    assert client.post(ruta, json={"nombre": "  "}).status_code == 422
    assert (
        client.post(
            ruta, json={"nombre": "Otro Usuario", "porcentaje_produccion": "120"}
        ).status_code
        == 422
    )

def test_responsable_crea_codigo_manual_y_edita_solo_su_usuario(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant = auth_prueba.contexto.tenant_id
    responsable = Miembro(tenant_id=tenant, codigo="RES-TEST", nombre="Responsable", rol="RESPONSABLE", activo=True)
    otro = Miembro(tenant_id=tenant, codigo="RES-OTRO", nombre="Otro Responsable", rol="RESPONSABLE", activo=True)
    session.add_all([responsable, otro])
    session.flush()
    ajeno = Miembro(tenant_id=tenant, codigo="AJENO01", nombre="Usuario ajeno", rol="USUARIO", responsable_id=otro.id, activo=True)
    session.add(ajeno)
    session.commit()
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=auth_prueba.contexto.cuenta_id, tenant_id=tenant, rol="RESPONSABLE",
        miembro_id=responsable.id, gestor_id=None, usuario_id=None, codigo=responsable.codigo,
        nombre=responsable.nombre, cambio_clave_obligatorio=False,
    )
    ruta = "/api/v1/miembros/mis-usuarios"
    r = client.post(ruta, json={"nombre": "José Carlos", "codigo": "JOSE01", "porcentaje_produccion": "1.5"})
    assert r.status_code == 201, r.text
    usuario = r.json()["miembro"]
    assert usuario["codigo"] == "JOSE01"
    assert client.post(ruta, json={"nombre": "Duplicado", "codigo": "JOSE01"}).status_code == 409
    assert client.post(ruta, json={"nombre": "Inválido", "codigo": "INVALIDO!"}).status_code == 422
    datos = {"nombre": "José Carlos Editado", "codigo": "JOSE02", "porcentaje_produccion": "2.5"}
    assert client.patch(f"{ruta}/{ajeno.id}", json=datos).status_code == 404
    actual = client.patch(f"{ruta}/{usuario['id']}", json=datos)
    assert actual.status_code == 200, actual.text
    assert actual.json()["codigo"] == "JOSE02"
    assert actual.json()["nombre"] == "José Carlos Editado"
    assert client.patch(f"{ruta}/{usuario['id']}", json={**datos, "codigo": "AJENO01"}).status_code == 409
