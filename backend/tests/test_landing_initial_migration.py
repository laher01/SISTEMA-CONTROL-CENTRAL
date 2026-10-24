"""La instalación nueva comienza sin publicación pública; no migra estados existentes."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa


def test_landing_0039_seed_inactive_and_server_default(monkeypatch):
    migration = (
        Path(__file__).resolve().parents[1] / "alembic/versions/20261017_0039_landing_global.py"
    )
    spec = importlib.util.spec_from_file_location("landing_migration_0039", migration)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    statements = []
    columns = []

    def create_table(name, *args):
        if name == "configuracion_landing_global":
            columns.extend(arg for arg in args if isinstance(arg, sa.Column))

    monkeypatch.setattr(module.op, "create_table", create_table)
    monkeypatch.setattr(module.op, "execute", statements.append)
    module.upgrade()

    activa = next(col for col in columns if col.name == "activa")
    assert isinstance(activa.server_default.arg, sa.sql.elements.False_)
    assert [" ".join(statement.split()) for statement in statements] == [
        "INSERT INTO configuracion_landing_global (id, activa, version) VALUES (1, FALSE, 1)"
    ]


def test_landing_0039_downgrade_preserves_existing_behavior(monkeypatch):
    migration = (
        Path(__file__).resolve().parents[1] / "alembic/versions/20261017_0039_landing_global.py"
    )
    spec = importlib.util.spec_from_file_location("landing_migration_0039_down", migration)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dropped = []
    monkeypatch.setattr(module.op, "drop_table", dropped.append)
    module.downgrade()
    assert dropped == ["auditoria_landing_global", "configuracion_landing_global"]
