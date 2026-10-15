"""Rechaza períodos inválidos antes de consultar datos contables."""

from datetime import date

import pytest
from fastapi import HTTPException

from app.api.routes.contabilidad_items import resumen


def test_resumen_rechaza_fecha_invertida(session, auth_prueba):
    auth_prueba.como_admin()
    with pytest.raises(HTTPException) as error:
        resumen(
            session=session,
            auth=auth_prueba.contexto,
            desde=date(2026, 10, 15),
            hasta=date(2026, 10, 14),
            limite=100,
        )
    assert error.value.status_code == 422
