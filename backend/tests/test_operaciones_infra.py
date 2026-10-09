import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.models_operaciones_infra import OperacionInfra
from tests.conftest import AuthPrueba
from tests.test_infraestructura import NODO, RUTA


def nodo_con_agente(client: TestClient, codigo: str = "ORACLE-01") -> tuple[str, dict[str, str]]:
    nodo = client.post(f"{RUTA}/nodos", json={**NODO, "codigo": codigo})
    assert nodo.status_code == 201, nodo.text
    nodo_id = nodo.json()["id"]
    token = client.post(f"{RUTA}/nodos/{nodo_id}/credencial").json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    reporte = client.post(
        f"{RUTA}/agentes/{nodo_id}/reportes",
        headers=headers,
        json={
            "reporte_id": str(uuid.uuid4()),
            "servicios": {"backend": "OK", "postgresql": "OK"},
            "version": "0.1.0",
            "migracion": "0017",
        },
    )
    assert reporte.status_code == 200, reporte.text
    return nodo_id, headers


def version_aprobada(client: TestClient, migracion: str = "0017") -> str:
    respuesta = client.post(
        f"{RUTA}/versiones",
        json={
            "version": "0.2.0",
            "commit_git": "a" * 40,
            "imagen_docker": "ghcr.io/laher01/fact-central-backend",
            "digest": "sha256:" + "b" * 64,
            "imagen_frontend": "ghcr.io/laher01/fact-central-frontend",
            "digest_frontend": "sha256:" + "c" * 64,
            "construida_at": "2026-10-09T10:00:00Z",
            "entorno": "staging",
            "migracion_desde": "0017",
            "migracion_hasta": migracion,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    version_id = respuesta.json()["id"]
    aprobacion = client.post(
        f"{RUTA}/versiones/{version_id}/aprobar",
        json={
            "evidencia_ci": "https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/actions/runs/123",
        },
    )
    assert aprobacion.status_code == 200, aprobacion.text
    return version_id


def reclamar(client: TestClient, nodo_id: str, headers: dict[str, str]) -> dict | None:
    respuesta = client.post(f"{RUTA}/agentes/{nodo_id}/reclamar", headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["operacion"]


def test_despliegue_protegido_lease_evidencia_e_idempotencia(
    client: TestClient,
    auth_prueba: AuthPrueba,
    settings: Settings,
) -> None:
    auth_prueba.como_superadmin()
    nodo_id, headers = nodo_con_agente(client)
    version_id = version_aprobada(client)
    datos = {"solicitud_id": str(uuid.uuid4()), "nodo_id": nodo_id, "version_id": version_id}
    assert client.post(f"{RUTA}/despliegues", json=datos).status_code == 409
    settings.infra_operaciones_habilitadas = True
    solicitud = client.post(f"{RUTA}/despliegues", json=datos)
    assert solicitud.status_code == 201, solicitud.text
    assert client.post(f"{RUTA}/despliegues", json=datos).json()["id"] == solicitud.json()["id"]
    trabajo = reclamar(client, nodo_id, headers)
    assert trabajo is not None
    assert reclamar(client, nodo_id, headers) is None
    resultado_ruta = f"{RUTA}/agentes/{nodo_id}/operaciones/{trabajo['id']}/resultado"
    assert (
        client.post(
            resultado_ruta,
            headers=headers,
            json={
                "lease": "x" * 64,
                "estado": "FALLO",
            },
        ).status_code
        == 401
    )
    assert (
        client.post(
            resultado_ruta,
            headers=headers,
            json={
                "lease": trabajo["lease"],
                "estado": "EXITO",
            },
        ).status_code
        == 422
    )
    resultado = {
        "lease": trabajo["lease"],
        "estado": "EXITO",
        "backend_ok": True,
        "base_datos_ok": True,
        "imagen_verificada": True,
        "migracion": "0017",
    }
    exito = client.post(resultado_ruta, headers=headers, json=resultado)
    assert exito.status_code == 200, exito.text
    assert exito.json()["estado"] == "EXITO"
    assert client.post(resultado_ruta, headers=headers, json=resultado).status_code == 200
    assert (
        client.post(
            resultado_ruta, headers=headers, json={**resultado, "estado": "FALLO"}
        ).status_code
        == 409
    )
    assert client.get(f"{RUTA}/nodos").json()[0]["version_instalada"] == "0.2.0"
    assert client.post(f"{RUTA}/despliegues", json=datos).json()["id"] == trabajo["id"]
    assert trabajo["lease"] not in client.get(f"{RUTA}/operaciones").text
    assert trabajo["lease"] not in client.get(f"{RUTA}/eventos").text
    auth_prueba.como_admin()
    assert client.get(f"{RUTA}/operaciones").status_code == 403


def test_lote_fallido_detiene_nodos_siguientes(
    client: TestClient,
    auth_prueba: AuthPrueba,
    settings: Settings,
) -> None:
    auth_prueba.como_superadmin()
    settings.infra_operaciones_habilitadas = True
    primero, h1 = nodo_con_agente(client, "CANARY-01")
    segundo, h2 = nodo_con_agente(client, "RESTO-02")
    version_id = version_aprobada(client)
    datos = {
        "solicitud_id": str(uuid.uuid4()),
        "nodos": [primero, segundo],
        "version_id": version_id,
    }
    lote = client.post(f"{RUTA}/lotes", json=datos)
    assert lote.status_code == 201, lote.text
    assert reclamar(client, segundo, h2) is None
    trabajo = reclamar(client, primero, h1)
    assert trabajo
    respuesta = client.post(
        f"{RUTA}/agentes/{primero}/operaciones/{trabajo['id']}/resultado",
        headers=h1,
        json={"lease": trabajo["lease"], "estado": "FALLO", "codigo_error": "HEALTHCHECK"},
    )
    assert respuesta.status_code == 200
    assert reclamar(client, segundo, h2) is None
    assert client.post(f"{RUTA}/lotes", json=datos).status_code == 201


def test_backup_integridad_restauracion_y_migracion_segura(
    client: TestClient,
    auth_prueba: AuthPrueba,
    settings: Settings,
) -> None:
    auth_prueba.como_superadmin()
    settings.infra_operaciones_habilitadas = True
    nodo_id, headers = nodo_con_agente(client)
    version_id = version_aprobada(client, "0018")
    datos = {"solicitud_id": str(uuid.uuid4()), "nodo_id": nodo_id, "version_id": version_id}
    assert client.post(f"{RUTA}/despliegues", json=datos).status_code == 409
    assert client.post(f"{RUTA}/rollback-imagen", json=datos).status_code == 409
    backup = client.post(
        f"{RUTA}/backups", json={"solicitud_id": str(uuid.uuid4()), "nodo_id": nodo_id}
    )
    assert backup.status_code == 201
    trabajo = reclamar(client, nodo_id, headers)
    assert trabajo
    ruta_resultado = f"{RUTA}/agentes/{nodo_id}/operaciones/{trabajo['id']}/resultado"
    assert (
        client.post(
            ruta_resultado,
            headers=headers,
            json={
                "lease": trabajo["lease"],
                "estado": "EXITO",
            },
        ).status_code
        == 422
    )
    evidencia = {
        "lease": trabajo["lease"],
        "estado": "EXITO",
        "objeto": "backup.dump.age",
        "sha256": "a" * 64,
        "bytes": 1000,
        "dump_verificado": True,
    }
    assert client.post(ruta_resultado, headers=headers, json=evidencia).status_code == 200
    assert client.post(ruta_resultado, headers=headers, json=evidencia).status_code == 200
    backups = client.get(f"{RUTA}/backups").json()
    assert len(backups) == 1
    datos["backup_id"] = backups[0]["id"]
    assert client.post(f"{RUTA}/despliegues", json=datos).status_code == 409
    verificacion = client.post(
        f"{RUTA}/backups/{backups[0]['id']}/restauracion-verificada",
        json={
            "evidencia": "https://example.test/restore-evidence",
            "entorno": "staging",
        },
    )
    assert verificacion.status_code == 200
    assert client.post(f"{RUTA}/despliegues", json=datos).status_code == 201
    assert (
        client.post(
            f"{RUTA}/rollback-imagen", json={**datos, "solicitud_id": str(uuid.uuid4())}
        ).status_code
        == 409
    )


def test_lease_vencida_nunca_repite_comando(
    client: TestClient,
    auth_prueba: AuthPrueba,
    settings: Settings,
    engine: Engine,
) -> None:
    auth_prueba.como_superadmin()
    settings.infra_operaciones_habilitadas = True
    nodo_id, headers = nodo_con_agente(client)
    client.post(f"{RUTA}/backups", json={"solicitud_id": str(uuid.uuid4()), "nodo_id": nodo_id})
    trabajo = reclamar(client, nodo_id, headers)
    assert trabajo
    with sessionmaker(engine)() as session:
        operacion = session.get(OperacionInfra, uuid.UUID(trabajo["id"]))
        assert operacion
        operacion.lease_hasta = datetime.now(UTC) - timedelta(seconds=10)
        session.commit()
    assert reclamar(client, nodo_id, headers) is None
    client.post(f"{RUTA}/backups", json={"solicitud_id": str(uuid.uuid4()), "nodo_id": nodo_id})
    assert reclamar(client, nodo_id, headers) is None
    assert client.get(f"{RUTA}/operaciones").json()["operaciones"][-1]["estado"] == "FALLO"


def test_no_acepta_shell_ni_despliegues_productivos_por_defecto(
    client: TestClient,
    auth_prueba: AuthPrueba,
    settings: Settings,
) -> None:
    auth_prueba.como_superadmin()
    settings.infra_operaciones_habilitadas = True
    nodo = client.post(f"{RUTA}/nodos", json={**NODO, "entorno": "production"}).json()
    assert (
        client.post(
            f"{RUTA}/backups",
            json={
                "solicitud_id": str(uuid.uuid4()),
                "nodo_id": nodo["id"],
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{RUTA}/backups",
            json={
                "solicitud_id": str(uuid.uuid4()),
                "nodo_id": nodo["id"],
                "command": "rm -rf /",
            },
        ).status_code
        == 422
    )
