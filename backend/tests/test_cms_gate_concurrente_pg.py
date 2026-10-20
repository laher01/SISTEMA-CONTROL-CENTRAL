"""Exclusión PostgreSQL del gate público frente a desactivación concurrente."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import ConfiguracionLandingGlobal


def test_gate_publico_impide_desactivacion_durante_lectura(engine) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("Requiere PostgreSQL real y bloqueos FOR SHARE")
    with Session(engine) as inicial:
        inicial.add(ConfiguracionLandingGlobal(id=1, activa=True, version=1))
        inicial.commit()

    with Session(engine) as lectura:
        config = lectura.scalar(
            select(ConfiguracionLandingGlobal)
            .where(ConfiguracionLandingGlobal.id == 1)
            .with_for_update(read=True)
        )
        assert config is not None and config.activa is True
        with Session(engine) as desactivacion:
            desactivacion.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(DBAPIError):
                desactivacion.execute(
                    text("UPDATE configuracion_landing_global SET activa = FALSE WHERE id = 1")
                )
            desactivacion.rollback()
        lectura.rollback()
    with Session(engine) as desactivacion:
        desactivacion.execute(
            text("UPDATE configuracion_landing_global SET activa = FALSE WHERE id = 1")
        )
        desactivacion.commit()
    with Session(engine) as confirmar:
        assert confirmar.get(ConfiguracionLandingGlobal, 1).activa is False
