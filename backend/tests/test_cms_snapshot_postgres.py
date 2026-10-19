"""Conservar el snapshot editorial en PostgreSQL durante una nueva edición."""

import pytest
from sqlalchemy import select

from app.services.cms_landing_core import EstadoEditorial
from app.services.cms_landing_store import (
    cambiar_estado,
    evento_table,
    publicacion_table,
    revision_table,
)


def test_snapshot_publico_permanece_tras_reabrir_pg(engine, auth_prueba) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("Solo PostgreSQL con SELECT FOR UPDATE real")

    from sqlalchemy.orm import Session

    actor = auth_prueba.contexto.cuenta_id
    with Session(engine) as session:
        session.execute(
            revision_table.insert().values(
                id=1,
                version=1,
                estado=EstadoEditorial.BORRADOR.value,
                contenido={"titulo": "Versión original"},
                actualizado_por=actor,
            )
        )
        session.commit()
        version = 1
        for destino in (
            EstadoEditorial.VISTA_PREVIA,
            EstadoEditorial.APROBADO,
            EstadoEditorial.PUBLICADO,
        ):
            version = cambiar_estado(
                session,
                destino=destino,
                version_esperada=version,
                rol="SUPERADMIN",
                actor_id=actor,
            ).version
        anterior = session.execute(select(publicacion_table)).mappings().one()
        assert anterior["version_editorial"] == 4

        version = cambiar_estado(
            session,
            destino=EstadoEditorial.BORRADOR,
            version_esperada=version,
            rol="SUPERADMIN",
            actor_id=actor,
        ).version
        session.execute(
            revision_table.update()
            .where(revision_table.c.id == 1)
            .values(contenido={"titulo": "Nuevo borrador"})
        )
        session.commit()
        snapshot = session.execute(select(publicacion_table)).mappings().one()
        assert snapshot["version_editorial"] == anterior["version_editorial"]
        assert snapshot["contenido"] == anterior["contenido"]
        assert session.scalar(select(revision_table.c.version)) == version
        assert len(session.execute(select(evento_table)).all()) == 4
