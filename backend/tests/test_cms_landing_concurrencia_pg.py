"""Regresión de dos escritores CMS sobre PostgreSQL, no sobre SQLite."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.services.cms_landing_core import EstadoEditorial
from app.services.cms_landing_store import cambiar_estado, evento_table, revision_table


def test_dos_sesiones_solo_una_transicion_auditable(engine: Engine, auth_prueba) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("La exclusión SELECT FOR UPDATE requiere PostgreSQL")

    actor = auth_prueba.contexto.cuenta_id
    with engine.begin() as connection:
        connection.execute(
            revision_table.insert().values(
                id=1,
                version=1,
                estado=EstadoEditorial.BORRADOR.value,
                contenido={"titulo": "Revisión concurrente"},
            )
        )
    inicio = Barrier(2)

    def ejecutar() -> str:
        with Session(engine) as sesion:
            inicio.wait(timeout=10)
            try:
                cambiar_estado(
                    sesion,
                    destino=EstadoEditorial.VISTA_PREVIA,
                    version_esperada=1,
                    rol="SUPERADMIN",
                    actor_id=actor,
                )
                return "aprobado"
            except ValueError:
                sesion.rollback()
                return "conflicto"

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = [f.result(timeout=25) for f in [pool.submit(ejecutar) for _ in range(2)]]

    assert sorted(resultados) == ["aprobado", "conflicto"]
    with Session(engine) as sesion:
        assert sesion.scalar(select(revision_table.c.version)) == 2
        assert len(sesion.execute(select(evento_table)).all()) == 1
