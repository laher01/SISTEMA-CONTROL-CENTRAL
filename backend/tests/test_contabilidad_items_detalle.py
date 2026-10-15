"""Contrato HTTP de detalle de Contabilidad de Ítems."""

import uuid
from dataclasses import replace

import pytest
from fastapi import HTTPException

from app.api.routes.contabilidad_items import detalle_expediente


def test_detalle_no_revela_expediente_inexistente(session, auth_prueba):
    contexto = auth_prueba.contexto
    with pytest.raises(HTTPException) as error:
        detalle_expediente(uuid.uuid4(), session, contexto)
    assert error.value.status_code == 404


def test_detalle_deniega_rol_sin_acceso(session, auth_prueba):
    contexto = replace(auth_prueba.contexto, rol="SUPERADMIN")
    with pytest.raises(HTTPException) as error:
        detalle_expediente(uuid.uuid4(), session, contexto)
    assert error.value.status_code == 403
