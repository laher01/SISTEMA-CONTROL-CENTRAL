"""Regresión MISD: el advisory lock precede a cualquier lectura de elegibilidad.

Esta prueba verifica el contrato estructural de rutas. No sustituye los ensayos
con dos sesiones PostgreSQL sobre carreras reales de liquidación y retirada.
"""

import ast
import inspect
import textwrap

import pytest

from app.api.routes import solicitudes_retiro_misd


@pytest.mark.parametrize("operacion", ["solicitar", "resolver", "ejecutar"])
def test_misd_adquiere_lock_antes_de_leer_estado(operacion: str) -> None:
    funcion = getattr(solicitudes_retiro_misd, operacion)
    arbol = ast.parse(textwrap.dedent(inspect.getsource(funcion)))
    definicion = arbol.body[0]
    assert isinstance(definicion, ast.FunctionDef)
    primera = definicion.body[0]
    if isinstance(primera, ast.Expr) and isinstance(primera.value, ast.Constant):
        # Ejecutar conserva un docstring como primera sentencia.
        primera = definicion.body[1]
    assert isinstance(primera, ast.Expr)
    llamada = primera.value
    assert isinstance(llamada, ast.Call)
    assert isinstance(llamada.func, ast.Name)
    assert llamada.func.id == "bloquear_tenant_financiero"
    assert len(llamada.args) == 2
    assert isinstance(llamada.args[0], ast.Name)
    assert llamada.args[0].id == "session"
    assert isinstance(llamada.args[1], ast.Name)
    assert llamada.args[1].id == "tenant_id"
