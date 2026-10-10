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


def test_responsable_edita_y_restablece_solo_su_usuario(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id, codigo="RESP-EDIT", nombre="Responsable edición",
        rol="RESPONSABLE", activo=True,
    )
    otro = Miembro(
        tenant_id=tenant_id, codigo="RESP-EXTRA", nombre="Otro responsable",
        rol="RESPONSABLE", activo=True,
    )
    session.add_all([responsable, otro])
    session.flush()
    propio = Miembro(
        tenant_id=tenant_id, codigo="USR-EDIT", nombre="Nombre anterior",
        rol="USUARIO", responsable_id=responsable.id, activo=True,
    )
    ajeno = Miembro(
        tenant_id=tenant_id, codigo="USR-EXTRA", nombre="No autorizado",
        rol="USUARIO", responsable_id=otro.id, activo=True,
    )
    session.add_all([propio, ajeno])
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
    ruta_propia = f"/api/v1/miembros/mis-usuarios/{propio.id}"
    ruta_ajena = f"/api/v1/miembros/mis-usuarios/{ajeno.id}"
    editar = client.patch(ruta_propia, json={"nombre": "Nombre corregido"})
    assert editar.status_code == 200, editar.text
    assert editar.json()["nombre"] == "Nombre corregido"
    tasas = client.patch(ruta_propia, json={"nombre": "Nombre corregido", "porcentaje_sin_retencion": "1.2500", "porcentaje_con_retencion": "0.8000"})
    assert tasas.status_code == 200, tasas.text
    assert tasas.json()["porcentaje_sin_retencion"] == "1.2500"
    assert tasas.json()["porcentaje_con_retencion"] == "0.8000"
    assert client.patch(ruta_propia, json={"nombre": "Nombre corregido", "porcentaje_con_retencion": "101"}).status_code == 422
    assert client.patch(ruta_ajena, json={"nombre": "Intento indebido"}).status_code == 404
    assert client.patch(ruta_propia, json={"nombre": "  "}).status_code == 422
    assert client.post(ruta_ajena + "/restablecer-acceso").status_code == 404
    reset = client.post(ruta_propia + "/restablecer-acceso")
    assert reset.status_code == 200, reset.text
    assert reset.json()["login"] == "USR-EDIT"
    assert len(reset.json()["clave_temporal"]) >= 8
