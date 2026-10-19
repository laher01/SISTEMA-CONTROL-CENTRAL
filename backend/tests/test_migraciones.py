from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from alembic import command
from app.models import Base
from tests.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL.startswith("postgresql"), reason="requiere PostgreSQL"
)


def test_migraciones_coinciden_con_modelos() -> None:
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as conexion:
        conexion.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    config = Config(Path(__file__).parent.parent / "alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")
    # PostgreSQL real: la instalación nueva comienza no publicada.
    with engine.begin() as conexion:
        assert (
            conexion.execute(
                text("SELECT activa FROM configuracion_landing_global WHERE id = 1")
            ).scalar_one()
            is False
        )

    # 0041 no modifica decisiones editoriales ya guardadas.
    for indice, activa in enumerate((True, False), start=3):
        with engine.begin() as conexion:
            conexion.execute(
                text(
                    "UPDATE configuracion_landing_global "
                    "SET activa = :activa, version = :version WHERE id = 1"
                ),
                {"activa": activa, "version": indice},
            )
            auditorias_antes = conexion.execute(
                text("SELECT count(*) FROM auditoria_landing_global")
            ).scalar_one()
        command.downgrade(config, "0040")
        command.upgrade(config, "0041")
        with engine.connect() as conexion:
            fila = conexion.execute(
                text("SELECT activa, version FROM configuracion_landing_global WHERE id = 1")
            ).one()
            assert fila.activa is activa
            assert fila.version == indice
            assert (
                conexion.execute(text("SELECT count(*) FROM auditoria_landing_global")).scalar_one()
                == auditorias_antes
            )
    with engine.connect() as conexion:
        diferencias = compare_metadata(MigrationContext.configure(conexion), Base.metadata)
    assert diferencias == []
    command.downgrade(config, "base")
    engine.dispose()
