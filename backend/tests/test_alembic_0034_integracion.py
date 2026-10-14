"""Ejecuta la cadena Alembic completa en PostgreSQL desechable, sin producción."""

import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from alembic import command


def test_alembic_0034_en_base_postgresql_aislada() -> None:
    import os

    url = os.environ.get("FC_TEST_DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("La prueba de migración necesita PostgreSQL real")

    database = f"fc_migration_check_{uuid.uuid4().hex[:12]}"
    base = make_url(url)
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    temporal = base.set(database=database)
    creada = False
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{database}"'))
        creada = True
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", temporal.render_as_string(hide_password=False))
        command.upgrade(config, "head")
        engine = create_engine(temporal)
        try:
            inspector = inspect(engine)
            columnas = {col["name"]: col for col in inspector.get_columns("documentos")}
            assert columnas["huella_comercial"]["nullable"]
            assert any(
                set(item["column_names"]) == {"tenant_id", "huella_comercial"}
                for item in inspector.get_unique_constraints("documentos")
            )
            with engine.connect() as conn:
                assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0034"
            command.upgrade(config, "head")
        finally:
            engine.dispose()
    finally:
        if creada:
            with admin.connect() as conn:
                conn.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :db AND pid <> pg_backend_pid()"
                    ),
                    {"db": database},
                )
                conn.execute(text(f'DROP DATABASE IF EXISTS "{database}"'))
        admin.dispose()
