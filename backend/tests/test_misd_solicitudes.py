"""Regresión de la política jerárquica de eliminación."""

from dataclasses import replace
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Auditoria, ChatMensaje, CuentaAcceso, Miembro, SolicitudRetiroMISD
from tests.conftest import AuthPrueba
from tests.xml import factura


def _como_responsable(auth: AuthPrueba, session: Session, usuario_id: UUID | None = None) -> None:
    usuario = session.get(Miembro, usuario_id or auth.contexto.usuario_id)
    assert usuario is not None
    tenant_id = auth.contexto.tenant_id
    responsable = session.get(Miembro, usuario.responsable_id) if usuario.responsable_id else None
    if responsable is None:
        responsable = Miembro(
            tenant_id=tenant_id,
            codigo="RESP-MISD",
            nombre="Responsable MISD",
            rol="RESPONSABLE",
            activo=True,
        )
        session.add(responsable)
        session.flush()
        usuario.responsable_id = responsable.id
    cuenta = (
        session.query(CuentaAcceso)
        .filter_by(tenant_id=tenant_id, miembro_id=responsable.id)
        .first()
    )
    if cuenta is None:
        cuenta = CuentaAcceso(
            tenant_id=tenant_id,
            login="RESP-MISD",
            password_hash="hash-pruebas",
            miembro_id=responsable.id,
            activo=True,
            cambio_clave_obligatorio=False,
        )
        session.add(cuenta)
    session.commit()
    auth.contexto = replace(
        auth.contexto,
        cuenta_id=cuenta.id,
        miembro_id=responsable.id,
        rol="RESPONSABLE",
        usuario_id=None,
        gestor_id=None,
        codigo="RESP-MISD",
        nombre="Responsable MISD",
    )


def _como_administrador_real(auth: AuthPrueba, session: Session) -> None:
    tenant_id = auth.contexto.tenant_id
    administrador = Miembro(
        tenant_id=tenant_id,
        codigo="ADMIN-MISD",
        nombre="Aprobador MISD",
        rol="ADMINISTRADOR",
        activo=True,
    )
    session.add(administrador)
    session.flush()
    cuenta = CuentaAcceso(
        tenant_id=tenant_id,
        login="ADMIN-MISD",
        password_hash="hash-pruebas",
        miembro_id=administrador.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta)
    session.commit()
    auth.contexto = replace(
        auth.contexto,
        cuenta_id=cuenta.id,
        miembro_id=administrador.id,
        rol="ADMINISTRADOR",
        usuario_id=None,
        gestor_id=None,
        codigo="ADMIN-MISD",
        nombre="Administrador MISD",
    )


def test_responsable_solicita_admin_aprueba_y_responsable_ejecuta_purga_total(
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
    settings: Settings,
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("solicitud-misd.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    documento_id = subida.json()["id"]
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    _como_responsable(auth_prueba, session, usuario_id)

    solicitud = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Documento cargado por error"},
    )
    assert solicitud.status_code == 201, solicitud.text
    solicitud_id = solicitud.json()["id"]
    assert client.delete(f"/api/v1/expedientes/{expediente_id}").status_code == 409
    assert client.delete(f"/api/v1/documentos/{documento_id}").status_code == 409

    _como_administrador_real(auth_prueba, session)
    assert any(fila["id"] == solicitud_id for fila in client.get("/api/v1/misd/solicitudes").json())
    decision = client.post(
        f"/api/v1/misd/solicitudes/{solicitud_id}/resolver",
        json={"aprobar": True, "motivo": "Autorizado por administración"},
    )
    assert decision.status_code == 200, decision.text
    _como_responsable(auth_prueba, session, usuario_id)
    resultado = client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar")
    assert resultado.status_code == 200, resultado.text
    assert resultado.json()["estado"] == "EJECUTADA"
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 404
    assert session.query(SolicitudRetiroMISD).filter_by(id=UUID(solicitud_id)).count() == 0
    assert session.query(Auditoria).filter_by(entidad_id=UUID(solicitud_id)).count() == 0
    ruta = (
        settings.storage_dir
        / str(auth_prueba.contexto.tenant_id)
        / subida.json()["sha256"][:2]
        / subida.json()["sha256"]
    )
    assert not ruta.exists()


def test_usuario_elimina_sus_documentos_sin_solicitud_misd(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("usuario-directo.xml", factura(numero="F001-00000127"))},
    )
    assert subida.status_code == 201, subida.text
    tenant_id = auth_prueba.contexto.tenant_id
    usuario = session.get(Miembro, auth_prueba.usuario_id)
    assert usuario is not None
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-NOTIF",
        nombre="Responsable notificación",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    usuario.responsable_id = responsable.id
    responsable_cuenta = CuentaAcceso(
        tenant_id=tenant_id,
        login="RESP-NOTIF",
        password_hash="hash-pruebas",
        miembro_id=responsable.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    gestor_cuenta = CuentaAcceso(
        tenant_id=tenant_id,
        login="GEST-NOTIF",
        password_hash="hash-pruebas",
        gestor_id=auth_prueba.gestor_id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add_all([responsable_cuenta, gestor_cuenta])
    session.commit()
    eliminacion = client.delete(f"/api/v1/documentos/{subida.json()['id']}")
    assert eliminacion.status_code == 200, eliminacion.text
    session.expire_all()
    destinatarios = {mensaje.destinatario_cuenta_id for mensaje in session.query(ChatMensaje).all()}
    assert responsable_cuenta.id in destinatarios
    assert gestor_cuenta.id in destinatarios
    assert auth_prueba.contexto.cuenta_id not in destinatarios
    assert session.query(SolicitudRetiroMISD).count() == 0


def test_usuario_no_puede_solicitar_misd_y_si_borrar_su_documento(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("usuario-directo.xml", factura(numero="F001-00000127"))},
    )
    assert subida.status_code == 201, subida.text
    solicitud = client.post(
        "/api/v1/misd/solicitudes",
        json={
            "expediente_id": subida.json()["expediente_id"],
            "motivo": "Eliminar mi propio documento",
        },
    )
    assert solicitud.status_code == 404
    respuesta = client.delete(f"/api/v1/documentos/{subida.json()['id']}")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "completado"
