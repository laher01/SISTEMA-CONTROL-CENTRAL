"""Solicitud persistente y autorización MISD: sin borrar expedientes."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Auditoria, Expediente, SolicitudRetiroMISD
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_solicitud_aprobacion_no_borra_expediente(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("solicitud-misd.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    expediente_id = respuesta.json()["expediente_id"]
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Factura ingresada por error"},
    )
    assert creada.status_code == 201, creada.text
    solicitud_id = creada.json()["id"]
    assert creada.json()["estado"] == "PENDIENTE"
    duplicada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Factura ingresada por error"},
    )
    assert duplicada.status_code == 409

    auth_prueba.como_admin()
    lista = client.get("/api/v1/misd/solicitudes")
    assert lista.status_code == 200, lista.text
    assert any(item["id"] == solicitud_id for item in lista.json())
    decision = client.post(
        f"/api/v1/misd/solicitudes/{solicitud_id}/resolver",
        json={"aprobar": True, "motivo": "Confirmado para revisión MISD"},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["estado"] == "APROBADA"
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 200
    assert session.query(SolicitudRetiroMISD).count() == 1
    assert (
        session.query(Auditoria).filter(Auditoria.accion == "MISD_SOLICITUD_RESUELTA").count() == 1
    )
    assert session.get(Expediente, expediente_id).deleted_at is None
    repeticion = client.post(
        f"/api/v1/misd/solicitudes/{solicitud_id}/resolver",
        json={"aprobar": True, "motivo": "Segunda resolución no permitida"},
    )
    assert repeticion.status_code == 409


def test_secretaria_no_puede_solicitar_retiro(client: TestClient, auth_prueba: AuthPrueba) -> None:
    from dataclasses import replace

    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("secretaria-misd.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    auth_prueba.contexto = replace(auth_prueba.contexto, rol="SECRETARIA")
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={
            "expediente_id": respuesta.json()["expediente_id"],
            "motivo": "Documento equivocado",
        },
    )
    assert creada.status_code in (403, 404)
