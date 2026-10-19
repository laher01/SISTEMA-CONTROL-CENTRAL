"""Regresiones del endpoint de cobertura: nunca omitir validación de fechas y alcance."""

from dataclasses import replace
from datetime import date

import pytest
from fastapi import HTTPException

from app.api.routes.contabilidad_items import cobertura_items


def test_cobertura_rechaza_rango_invertido(session, auth_prueba):
    with pytest.raises(HTTPException) as error:
        cobertura_items(
            session,
            auth_prueba.contexto,
            desde=date(2026, 10, 15),
            hasta=date(2026, 10, 14),
        )
    assert error.value.status_code == 422


def test_cobertura_rechaza_rol_sin_acceso(session, auth_prueba):
    contexto = replace(auth_prueba.contexto, rol="SUPERADMIN")
    with pytest.raises(HTTPException) as error:
        cobertura_items(session, contexto)
    assert error.value.status_code == 403


def test_cobertura_vacia_no_inventa_documentos(session, auth_prueba):
    resultado = cobertura_items(session, auth_prueba.contexto)
    assert resultado["expedientes"] >= 0
    assert resultado["con_lineas"] <= resultado["con_documentos"] <= resultado["expedientes"]
    assert resultado["sin_lineas"] == resultado["expedientes"] - resultado["con_lineas"]
    assert resultado["sin_documentos"] == resultado["expedientes"] - resultado["con_documentos"]
