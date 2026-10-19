"""Reglas consultivas: la ventana no permite eliminar producción liquidada."""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Expediente, ahora
from app.services.misd_autorizaciones import politica_retiro, roles_aprobadores
from tests.xml import factura


def test_cadena_jerarquica_misd() -> None:
    assert roles_aprobadores("GESTOR") == ("USUARIO", "RESPONSABLE", "ADMINISTRADOR")
    assert roles_aprobadores("USUARIO") == ("RESPONSABLE", "ADMINISTRADOR")
    assert roles_aprobadores("RESPONSABLE") == ()
    assert roles_aprobadores("ADMINISTRADOR") == ()
    assert roles_aprobadores("SECRETARIA") == ()


def test_ventana_de_correccion_y_prioridad_de_pagos(
    client: TestClient, session: Session
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("politica-misd.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente = session.get(Expediente, subida.json()["expediente_id"])
    assert expediente is not None
    inicio = expediente.created_at
    dentro = politica_retiro(expediente, "GESTOR", inicio + timedelta(minutes=10), False)
    assert dentro["dentro_ventana_correccion"] is True
    assert dentro["requiere_aprobacion"] is False

    despues = politica_retiro(expediente, "GESTOR", inicio + timedelta(minutes=31), False)
    assert despues["dentro_ventana_correccion"] is False
    assert despues["requiere_aprobacion"] is True
    assert despues["roles_aprobadores"] == ["USUARIO", "RESPONSABLE", "ADMINISTRADOR"]

    bloqueado = politica_retiro(expediente, "GESTOR", inicio + timedelta(minutes=1), True)
    assert bloqueado["bloqueado_por_pago"] is True
    assert bloqueado["puede_solicitar"] is False
    assert bloqueado["requiere_aprobacion"] is False

    secretaria = politica_retiro(expediente, "SECRETARIA", ahora(), False)
    assert secretaria["puede_solicitar"] is False
