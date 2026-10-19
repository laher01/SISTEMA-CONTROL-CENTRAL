"""Regresiones de persistencia editorial con base SQLite aislada."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.services.cms_landing_core import EstadoEditorial
from app.services.cms_landing_store import cambiar_estado


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE cms_landing_revision (id INTEGER PRIMARY KEY, "
            "version INTEGER NOT NULL, estado VARCHAR(24) NOT NULL, "
            "contenido JSON NOT NULL, actualizado_por CHAR(32))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE cms_landing_evento (id CHAR(32) PRIMARY KEY, "
            "version_anterior INTEGER NOT NULL, version_nueva INTEGER NOT NULL, "
            "anterior VARCHAR(24) NOT NULL, nuevo VARCHAR(24) NOT NULL, actor_id CHAR(32))"
        )
        connection.exec_driver_sql(
            "INSERT INTO cms_landing_revision "
            "(id, version, estado, contenido) VALUES "
            "(1, 1, 'borrador', '{\"titulo\": \"Prueba\"}')"
        )
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_superadmin_transicion_y_evento_atomico(session: Session) -> None:
    from sqlalchemy import text

    actor = uuid4()
    nueva = cambiar_estado(
        session,
        destino=EstadoEditorial.VISTA_PREVIA,
        version_esperada=1,
        rol="SUPERADMIN",
        actor_id=actor,
    )
    assert nueva.version == 2
    assert session.execute(text("SELECT COUNT(*) FROM cms_landing_evento")).scalar_one() == 1


def test_admin_no_puede_mutar(session: Session) -> None:
    from sqlalchemy import text

    with pytest.raises(PermissionError):
        cambiar_estado(
            session,
            destino=EstadoEditorial.VISTA_PREVIA,
            version_esperada=1,
            rol="ADMINISTRADOR",
            actor_id=uuid4(),
        )
    assert session.execute(text("SELECT version FROM cms_landing_revision")).scalar_one() == 1


def test_version_obsoleta_no_genera_evento(session: Session) -> None:
    from sqlalchemy import text

    with pytest.raises(ValueError, match="versión"):
        cambiar_estado(
            session,
            destino=EstadoEditorial.VISTA_PREVIA,
            version_esperada=0,
            rol="SUPERADMIN",
            actor_id=uuid4(),
        )
    assert session.execute(text("SELECT COUNT(*) FROM cms_landing_evento")).scalar_one() == 0


def test_error_de_auditoria_revierte_actualizacion(session: Session) -> None:
    from sqlalchemy import text

    session.execute(
        text(
            "CREATE TRIGGER bloquear_evento BEFORE INSERT ON cms_landing_evento "
            "BEGIN SELECT RAISE(ABORT, 'auditoria bloqueada'); END"
        )
    )
    session.commit()
    with pytest.raises(Exception, match="auditoria bloqueada"):
        cambiar_estado(
            session,
            destino=EstadoEditorial.VISTA_PREVIA,
            version_esperada=1,
            rol="SUPERADMIN",
            actor_id=uuid4(),
        )
    assert session.execute(text("SELECT version FROM cms_landing_revision")).scalar_one() == 1
    assert session.execute(text("SELECT COUNT(*) FROM cms_landing_evento")).scalar_one() == 0
