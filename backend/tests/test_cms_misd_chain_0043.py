"""Prueba aislada de cadena Alembic compartida MISD → CMS; no alterar producción."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from tests.conftest import TEST_DATABASE_URL


def test_un_solo_head_0043_cms_despues_de_misd() -> None:
    config = Config(Path(__file__).resolve().parents[1] / "alembic.ini")
    heads = ScriptDirectory.from_config(config).get_heads()
    assert heads == ["0043"]
    script = ScriptDirectory.from_config(config)
    assert script.get_revision("0043").down_revision == "0042"
    assert script.get_revision("0042").down_revision == "0041"


def test_postgresql_actualiza_0042_a_0043_sin_alterar_estado_landing(engine) -> None:
    if engine.dialect.name != "postgresql":
        import pytest

        pytest.skip("Requiere PostgreSQL real")
    config = Config(Path(__file__).resolve().parents[1] / "alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    # El fixture engine crea tablas ORM previamente; limpiar esquema temporal de tests.
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    command.upgrade(config, "0042")
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE configuracion_landing_global SET activa = FALSE, version = 7 WHERE id = 1")
        )
    command.upgrade(config, "0043")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT activa, version FROM configuracion_landing_global WHERE id = 1")
        ).one() == (False, 7)
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0043"
    assert {"solicitudes_retiro_misd", "cms_landing_revision", "cms_landing_evento"}.issubset(
        inspect(engine).get_table_names()
    )
