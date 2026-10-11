"""Incidencias de recepción visibles solo en administración del tenant."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CorreoBuzon, CorreoMensaje, Miembro
from tests.conftest import AuthPrueba


def test_admin_visualiza_revision_y_no_mensajes_ingresados(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-INC",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    buzon = CorreoBuzon(
        tenant_id=tenant_id,
        direccion="incidencias@example.test",
        proveedor="GOOGLE",
        responsable_id=responsable.id,
        activo=False,
    )
    session.add(buzon)
    session.flush()
    for uid, estado in (("revision-1", "REVISION"), ("ok-1", "INGRESADO")):
        session.add(
            CorreoMensaje(
                tenant_id=tenant_id,
                buzon_id=buzon.id,
                identificador_externo=uid,
                remitente="desconocido@example.test",
                estado=estado,
                error="REMITENTE_NO_REGISTRADO" if estado == "REVISION" else None,
            )
        )
    session.commit()
    auth_prueba.como_admin()
    respuesta = client.get("/api/v1/correo/incidencias")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert len(datos) == 1
    assert datos[0]["motivo"] == "REMITENTE_NO_REGISTRADO"
    assert datos[0]["buzon"] == "incidencias@example.test"
    auth_prueba.como_gerente()
    assert client.get("/api/v1/correo/incidencias").status_code == 403
