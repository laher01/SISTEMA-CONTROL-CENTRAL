"""Regresiones de acceso y transición de la landing global."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.pagina_web import (
    CambiarLanding,
    _exigir_superadmin,
    actualizar_estado,
    estado_admin,
    estado_publico,
)


def auth(rol: str, *, cambio: bool = False) -> SimpleNamespace:
    return SimpleNamespace(rol=rol, cambio_clave_obligatorio=cambio, cuenta_id=uuid4())


def test_solo_superadmin_activo_puede_editar() -> None:
    for rol in ("ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO"):
        with pytest.raises(HTTPException) as err:
            _exigir_superadmin(auth(rol))
        assert err.value.status_code == 403
    with pytest.raises(HTTPException):
        _exigir_superadmin(auth("SUPERADMIN", cambio=True))
    _exigir_superadmin(auth("SUPERADMIN"))


def test_consulta_publica_no_requiere_cuenta() -> None:
    session = MagicMock()
    session.get.return_value = None
    estado = estado_publico(session)
    assert estado.activa is False
    assert estado.version == 1


def test_primera_activacion_requiere_superadmin_y_audita() -> None:
    session = MagicMock()
    session.scalar.return_value = None
    cuenta = auth("SUPERADMIN")
    resultado = actualizar_estado(CambiarLanding(activa=True, version=1), session, cuenta)
    assert resultado.activa is True
    assert resultado.version == 2
    assert session.add.call_count == 2
    auditoria = session.add.call_args.args[0]
    assert auditoria.anterior is False
    assert auditoria.nuevo is True
    session.commit.assert_called_once()


def test_lectura_administrativa_bloquea_otro_rol() -> None:
    session = MagicMock()
    with pytest.raises(HTTPException) as err:
        estado_admin(session, auth("ADMINISTRADOR"))
    assert err.value.status_code == 403
    session.get.assert_not_called()


def test_escritura_rechaza_roles_no_globales_sin_mutar() -> None:
    session = MagicMock()
    with pytest.raises(HTTPException) as err:
        actualizar_estado(CambiarLanding(activa=False, version=1), session, auth("ADMINISTRADOR"))
    assert err.value.status_code == 403
    session.commit.assert_not_called()


def test_version_obsoleta_rechazada_sin_commit() -> None:
    session = MagicMock()
    session.scalar.return_value = SimpleNamespace(activa=True, version=2, actualizado_por=None)
    with pytest.raises(HTTPException) as err:
        actualizar_estado(CambiarLanding(activa=False, version=1), session, auth("SUPERADMIN"))
    assert err.value.status_code == 409
    session.commit.assert_not_called()


def test_transicion_registra_auditoria_y_actualiza_version() -> None:
    session = MagicMock()
    actual = SimpleNamespace(activa=True, version=1, actualizado_por=None)
    session.scalar.return_value = actual
    cuenta = auth("SUPERADMIN")
    resultado = actualizar_estado(CambiarLanding(activa=False, version=1), session, cuenta)
    assert resultado.activa is False
    assert resultado.version == 2
    assert actual.actualizado_por == cuenta.cuenta_id
    auditoria = session.add.call_args.args[0]
    assert auditoria.anterior is True
    assert auditoria.nuevo is False
    assert auditoria.version == 2
    session.commit.assert_called_once()


def test_sin_cambio_no_genera_auditoria() -> None:
    session = MagicMock()
    session.scalar.return_value = SimpleNamespace(activa=False, version=2, actualizado_por=None)
    resultado = actualizar_estado(
        CambiarLanding(activa=False, version=2), session, auth("SUPERADMIN")
    )
    assert resultado.version == 2
    session.add.assert_not_called()
    session.commit.assert_called_once()
