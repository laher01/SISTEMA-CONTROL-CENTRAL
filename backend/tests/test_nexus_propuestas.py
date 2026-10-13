"""Regresiones del ciclo de aprobación de fórmulas NEXUS."""

import pytest

from app.services.nexus_propuestas import (
    EstadoFormula,
    PropuestaFormula,
    transicion_formula,
)


def test_borrador_no_autoriza_liquidacion() -> None:
    propuesta = PropuestaFormula(
        plantilla="DISTRIBUCION_JONA01_V1",
        version=1,
        estado=EstadoFormula.BORRADOR,
        usuario_codigo="JONA01",
        responsable_codigo="LUIS",
    )
    assert not propuesta.habilitada_para_liquidar()


def test_aprobada_habilita_y_revocada_bloquea() -> None:
    propuesta = PropuestaFormula(
        plantilla="PAGO_ESTANDAR_V1",
        version=2,
        estado=EstadoFormula.APROBADA,
        usuario_codigo="JOSE01",
        responsable_codigo="LUIS",
    )
    assert propuesta.habilitada_para_liquidar()
    assert transicion_formula(EstadoFormula.APROBADA, EstadoFormula.REVOCADA) == (
        EstadoFormula.REVOCADA
    )
    with pytest.raises(ValueError):
        transicion_formula(EstadoFormula.REVOCADA, EstadoFormula.APROBADA)


def test_no_aplicar_formula_especial_a_otros_usuarios() -> None:
    propuesta = PropuestaFormula(
        plantilla="DISTRIBUCION_JONA01_V1",
        version=1,
        estado=EstadoFormula.APROBADA,
        usuario_codigo="JOSE01",
        responsable_codigo="LUIS",
    )
    with pytest.raises(ValueError):
        propuesta.habilitada_para_liquidar()


def test_no_aprobar_plantillas_desconocidas() -> None:
    propuesta = PropuestaFormula(
        plantilla="PYTHON_EVAL",
        version=1,
        estado=EstadoFormula.APROBADA,
        usuario_codigo="JONA01",
        responsable_codigo="LUIS",
    )
    with pytest.raises(ValueError):
        propuesta.habilitada_para_liquidar()


def test_aprobacion_solo_responsable_propietario() -> None:
    from app.services.nexus_propuestas import validar_aprobacion

    propuesta = PropuestaFormula(
        plantilla="PAGO_ESTANDAR_V1",
        version=1,
        estado=EstadoFormula.BORRADOR,
        usuario_codigo="JOSE01",
        responsable_codigo="LUIS",
    )
    validar_aprobacion(
        aprobador_rol="RESPONSABLE", aprobador_id="r1",
        responsable_id="r1", propuesta=propuesta,
    )
    with pytest.raises(PermissionError):
        validar_aprobacion(
            aprobador_rol="USUARIO", aprobador_id="r1",
            responsable_id="r1", propuesta=propuesta,
        )
    with pytest.raises(PermissionError):
        validar_aprobacion(
            aprobador_rol="RESPONSABLE", aprobador_id="r2",
            responsable_id="r1", propuesta=propuesta,
        )


def test_version_siguiente() -> None:
    from app.services.nexus_propuestas import version_siguiente

    assert version_siguiente([]) == 1
    assert version_siguiente([1, 2, 4]) == 5
    with pytest.raises(ValueError):
        version_siguiente([-1])
