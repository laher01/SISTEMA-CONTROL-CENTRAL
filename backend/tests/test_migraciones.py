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
    # Instalación limpia combinada: Etapa 7 (0039/0041) y MISD (0042).
    with engine.begin() as conexion:
        assert (
            conexion.execute(
                text("SELECT activa FROM configuracion_landing_global WHERE id = 1")
            ).scalar_one()
            is False
        )
        assert (
            conexion.execute(
                text("SELECT to_regclass('public.solicitudes_retiro_misd')")
            ).scalar_one()
            is not None
        )

    # Conservación editorial al retroceder y re-aplicar 0041→0042.
    for activa in (True, False):
        with engine.begin() as conexion:
            conexion.execute(
                text("UPDATE configuracion_landing_global SET activa = :activa WHERE id = 1"),
                {"activa": activa},
            )
        command.downgrade(config, "0040")
        command.upgrade(config, "head")
        with engine.connect() as conexion:
            assert (
                conexion.execute(
                    text("SELECT activa FROM configuracion_landing_global WHERE id = 1")
                ).scalar_one()
                is activa
            )
            assert conexion.execute(
                text("SELECT to_regclass('public.solicitudes_retiro_misd')")
            ).scalar_one() is not None

    with engine.connect() as conexion:
        diferencias = compare_metadata(MigrationContext.configure(conexion), Base.metadata)
    assert diferencias == []
    command.downgrade(config, "base")
    engine.dispose()
