import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_contexto_actual
from app.core.config import Settings
from app.main import app
from app.models import Auditoria, Tenant
from app.models_infraestructura import EventoInfraestructura, NodoInfraestructura, ReporteNodo
from tests.conftest import AuthPrueba

RUTA = "/api/v1/infraestructura"
NODO = {
    "codigo": "ORACLE-01",
    "nombre": "Oracle staging",
    "hostname": "oracle-01",
    "endpoint_privado": "http://10.0.0.5:8000",
    "proveedor": "Oracle",
    "region": "Lima",
    "sistema_operativo": "Ubuntu",
    "entorno": "staging",
    "ram_bytes": 8 * 1024**3,
}


def crear(client: TestClient, auth_prueba: AuthPrueba) -> dict:
    auth_prueba.como_superadmin()
    respuesta = client.post(f"{RUTA}/nodos", json=NODO)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_registro_permisos_auditoria_y_sin_secreto(
    client: TestClient,
    auth_prueba: AuthPrueba,
    engine: Engine,
) -> None:
    for cambiar in (auth_prueba.como_admin, auth_prueba.como_gerente):
        cambiar()
        assert client.get(f"{RUTA}/dashboard", headers={"X-Role": "SUPERADMIN"}).status_code == 403
        assert client.post(f"{RUTA}/nodos", json=NODO).status_code == 403
    nodo = crear(client, auth_prueba)
    assert nodo["estado"] == "DESCONOCIDO"
    assert nodo["ram_bytes"] == 8 * 1024**3
    assert nodo["cpu_porcentaje"] is None
    assert "token_hash" not in nodo
    assert client.post(f"{RUTA}/nodos", json=NODO).status_code == 409
    with sessionmaker(engine)() as session:
        evento = session.scalar(select(EventoInfraestructura))
        assert evento is not None
        assert evento.actor_cuenta_id == auth_prueba.contexto.cuenta_id
        assert evento.correlacion_id
        assert session.scalar(select(Auditoria).where(Auditoria.accion == "infra.nodo.creado"))


def test_ninguna_cabecera_suplanta_sesion(client: TestClient) -> None:
    anterior = app.dependency_overrides.pop(get_contexto_actual)
    try:
        respuesta = client.get(f"{RUTA}/nodos", headers={"X-Role": "SUPERADMIN"})
        assert respuesta.status_code == 401
    finally:
        app.dependency_overrides[get_contexto_actual] = anterior


def test_agente_token_rotacion_idempotencia_y_alertas(
    client: TestClient,
    auth_prueba: AuthPrueba,
    engine: Engine,
) -> None:
    nodo = crear(client, auth_prueba)
    ruta = f"{RUTA}/agentes/{nodo['id']}/reportes"
    reporte = {
        "reporte_id": str(uuid.uuid4()),
        "cpu_porcentaje": 12.5,
        "ram_porcentaje": 91,
        "disco_porcentaje": 89,
        "servicios": {"backend": "OK", "postgresql": "FALLO"},
        "version": "1.2.3",
    }
    assert client.post(ruta, json=reporte).status_code == 401
    credencial = client.post(f"{RUTA}/nodos/{nodo['id']}/credencial")
    assert credencial.status_code == 200
    assert credencial.headers["cache-control"] == "no-store"
    token = credencial.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        client.post(ruta, json=reporte, headers={"Authorization": "Bearer incorrecto"}).status_code
        == 401
    )
    primero = client.post(ruta, json=reporte, headers=headers)
    assert primero.status_code == 200, primero.text
    assert client.post(ruta, json=reporte, headers=headers).json() == primero.json()
    assert (
        client.post(ruta, json={**reporte, "cpu_porcentaje": 20}, headers=headers).status_code
        == 409
    )
    dashboard = client.get(f"{RUTA}/dashboard").json()
    actual = dashboard["nodos"][0]
    assert actual["cpu_porcentaje"] == 12.5
    assert actual["estado"] == "CONECTADO"
    assert actual["metricas_vigentes"]
    assert set(actual["alertas"]) == {"RAM_ELEVADO", "DISCO_ELEVADO", "POSTGRESQL_NO_DISPONIBLE"}
    with sessionmaker(engine)() as session:
        registro = session.get(NodoInfraestructura, uuid.UUID(nodo["id"]))
        assert registro is not None
        assert registro.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert len(list(session.scalars(select(ReporteNodo)))) == 1
        registro.ultima_conexion = datetime.now(UTC) - timedelta(hours=1)
        session.commit()
    actual = client.get(f"{RUTA}/dashboard").json()["nodos"][0]
    assert actual["estado"] == "DESCONECTADO"
    assert not actual["metricas_vigentes"]
    assert "NODO_DESCONECTADO" in actual["alertas"]
    client.post(f"{RUTA}/nodos/{nodo['id']}/credencial")
    assert client.post(ruta, json=reporte, headers=headers).status_code == 401
    assert token not in client.get(f"{RUTA}/eventos").text
    assert token not in client.get(f"{RUTA}/nodos").text


def test_desactivacion_revoca_y_es_repetible(client: TestClient, auth_prueba: AuthPrueba) -> None:
    nodo = crear(client, auth_prueba)
    token = client.post(f"{RUTA}/nodos/{nodo['id']}/credencial").json()["token"]
    for _ in range(2):
        assert client.delete(f"{RUTA}/nodos/{nodo['id']}").status_code == 204
    assert client.get(f"{RUTA}/nodos").json()[0]["estado"] == "INACTIVO"
    assert client.post(f"{RUTA}/nodos/{nodo['id']}/credencial").status_code == 409
    respuesta = client.post(
        f"{RUTA}/agentes/{nodo['id']}/reportes",
        json={"reporte_id": str(uuid.uuid4()), "servicios": {"backend": "OK"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 401


def test_validacion_destinos_secretos_metricas_y_origen(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_superadmin()
    for endpoint in ("file:///etc/passwd", "http://user:secret@10.0.0.5", "http://169.254.169.254"):
        assert (
            client.post(f"{RUTA}/nodos", json={**NODO, "endpoint_privado": endpoint}).status_code
            == 422
        )
    assert client.post(f"{RUTA}/nodos", json={**NODO, "ssh_password": "secret"}).status_code == 422
    assert (
        client.post(
            f"{RUTA}/nodos", json=NODO, headers={"Origin": "https://ajeno.example"}
        ).status_code
        == 403
    )
    nodo = crear(client, auth_prueba)
    token = client.post(f"{RUTA}/nodos/{nodo['id']}/credencial").json()["token"]
    assert (
        client.post(
            f"{RUTA}/agentes/{nodo['id']}/reportes",
            headers={"Authorization": f"Bearer {token}"},
            json={"reporte_id": str(uuid.uuid4()), "cpu_porcentaje": 101, "servicios": {}},
        ).status_code
        == 422
    )


def test_asociacion_no_mueve_datos_ni_concede_acceso(
    client: TestClient,
    auth_prueba: AuthPrueba,
    engine: Engine,
) -> None:
    nodo = crear(client, auth_prueba)
    with sessionmaker(engine)() as session:
        tenant = Tenant(nombre="Otra administración")
        session.add(tenant)
        session.commit()
        tenant_id = str(tenant.id)
    datos = {"tenant_id": tenant_id, "nodo_id": nodo["id"]}
    respuesta = client.post(f"{RUTA}/asociaciones", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    assert client.post(f"{RUTA}/asociaciones", json=datos).json() == respuesta.json()
    assert client.get(f"{RUTA}/nodos").json()[0]["tenants"] == [tenant_id]
    auth_prueba.como_admin()
    assert client.get(f"{RUTA}/nodos").status_code == 403
    assert client.get(f"{RUTA}/eventos").status_code == 403


def test_version_por_digest_inmutable_y_salud(client: TestClient, auth_prueba: AuthPrueba) -> None:
    auth_prueba.como_superadmin()
    datos = {
        "version": "1.2.3",
        "commit_git": "a" * 40,
        "imagen_docker": "ghcr.io/laher01/backend",
        "digest": "sha256:" + "b" * 64,
        "construida_at": "2026-10-09T10:00:00Z",
        "entorno": "staging",
        "migracion_desde": "0015",
        "migracion_hasta": "0016",
    }
    respuesta = client.post(f"{RUTA}/versiones", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["validacion"] == "PENDIENTE"
    assert respuesta.json()["aprobacion"] == "PENDIENTE"
    assert client.post(f"{RUTA}/versiones", json=datos).status_code == 409
    assert client.post(f"{RUTA}/versiones", json={**datos, "digest": "latest"}).status_code == 422
    assert client.post(f"{RUTA}/versiones", json={**datos, "version": "01.2.3"}).status_code == 422
    assert client.get(f"{RUTA}/salud").json() == {
        "backend": "OK",
        "base_datos": "OK",
        "redis": "NO_CONFIGURADO",
    }


def test_origen_https_publico_detras_de_proxy_sin_confiar_en_cabeceras(
    client: TestClient,
    auth_prueba: AuthPrueba,
    settings: Settings,
) -> None:
    auth_prueba.como_superadmin()
    settings.tenant_domain = "factcentral.online"
    respuesta = client.post(
        f"http://factcentral.online{RUTA}/nodos",
        json=NODO,
        headers={"Origin": "https://factcentral.online"},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert (
        client.post(
            f"http://factcentral.online{RUTA}/nodos",
            json={**NODO, "codigo": "SEGUNDO"},
            headers={
                "Origin": "https://malicioso.factcentral.online",
                "X-Forwarded-Host": "malicioso.factcentral.online",
            },
        ).status_code
        == 403
    )
