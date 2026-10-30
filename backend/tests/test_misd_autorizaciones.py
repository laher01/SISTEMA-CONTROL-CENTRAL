"""Reglas consultivas: la ventana no permite eliminar producción liquidada."""

from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Expediente, PermisoConfigurado, ahora
from app.services.misd_autorizaciones import politica_retiro, roles_aprobadores
from app.services.permisos import PERMISO_ELIMINAR_REGISTROS, permiso_habilitado
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_cadena_jerarquica_misd() -> None:
    assert roles_aprobadores("GESTOR") == ()
    assert roles_aprobadores("USUARIO") == ()
    assert roles_aprobadores("RESPONSABLE") == ("ADMINISTRADOR",)
    assert roles_aprobadores("ADMINISTRADOR") == ()
    assert roles_aprobadores("SECRETARIA") == ()


def test_ventana_de_correccion_y_prioridad_de_pagos(client: TestClient, session: Session) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("politica-misd.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente = session.get(Expediente, UUID(subida.json()["expediente_id"]))
    assert expediente is not None
    inicio = expediente.created_at
    dentro = politica_retiro(expediente, "GESTOR", inicio + timedelta(minutes=10), False)
    assert dentro["dentro_ventana_correccion"] is True
    assert dentro["requiere_aprobacion"] is False

    despues = politica_retiro(expediente, "RESPONSABLE", inicio + timedelta(minutes=31), False)
    assert despues["dentro_ventana_correccion"] is False
    assert despues["requiere_aprobacion"] is True
    assert despues["roles_aprobadores"] == ["ADMINISTRADOR"]

    bloqueado = politica_retiro(expediente, "GESTOR", inicio + timedelta(minutes=1), True)
    assert bloqueado["bloqueado_por_pago"] is False
    assert bloqueado["puede_solicitar"] is False
    assert bloqueado["requiere_aprobacion"] is False
    assert bloqueado["puede_eliminar_directamente"] is True

    secretaria = politica_retiro(expediente, "SECRETARIA", ahora(), False)
    assert secretaria["puede_solicitar"] is False


def test_permiso_retiro_respeta_configuracion_por_tenant(
    auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    permiso = PermisoConfigurado(
        tenant_id=tenant_id,
        rol="USUARIO",
        permiso=PERMISO_ELIMINAR_REGISTROS,
        habilitado=True,
    )
    session.add(permiso)
    session.flush()
    assert permiso_habilitado(session, tenant_id, "USUARIO", PERMISO_ELIMINAR_REGISTROS)
    permiso.habilitado = False
    session.flush()
    assert permiso_habilitado(session, tenant_id, "USUARIO", PERMISO_ELIMINAR_REGISTROS)

    session.delete(permiso)
    session.flush()
    assert permiso_habilitado(session, tenant_id, "USUARIO", PERMISO_ELIMINAR_REGISTROS)
    assert permiso_habilitado(session, tenant_id, "RESPONSABLE", PERMISO_ELIMINAR_REGISTROS)
    assert permiso_habilitado(session, tenant_id, "ADMINISTRADOR", PERMISO_ELIMINAR_REGISTROS)
    assert permiso_habilitado(session, tenant_id, "GESTOR", PERMISO_ELIMINAR_REGISTROS)
    assert not permiso_habilitado(session, tenant_id, "SECRETARIA", PERMISO_ELIMINAR_REGISTROS)
