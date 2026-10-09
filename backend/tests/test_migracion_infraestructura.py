import runpy
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select

from app.models import Base, Tenant


def test_migracion_0016_expande_y_conserva_datos(tmp_path: Path) -> None:
    motor = create_engine(f"sqlite:///{tmp_path / 'migracion.db'}")
    tablas_previas = [t for t in Base.metadata.sorted_tables if not t.name.startswith("infra_")]
    Base.metadata.create_all(motor, tables=tablas_previas)
    migracion = runpy.run_path(
        str(Path(__file__).parents[1] / "alembic/versions/20261009_0016_infraestructura.py")
    )
    assert migracion["down_revision"] == "0015"
    with motor.begin() as connection:
        connection.execute(Tenant.__table__.insert().values(nombre="Datos anteriores"))
        previas = set(inspect(connection).get_table_names())
        with Operations.context(MigrationContext.configure(connection)):
            migracion["upgrade"]()
        nuevas = set(inspect(connection).get_table_names())
        assert nuevas - previas == {
            "infra_nodos",
            "infra_reportes",
            "infra_versiones",
            "infra_tenant_nodo",
            "infra_eventos",
        }
        assert connection.scalar(select(Tenant.nombre)) == "Datos anteriores"
        with Operations.context(MigrationContext.configure(connection)):
            migracion["downgrade"]()
        assert set(inspect(connection).get_table_names()) == previas
        assert connection.scalar(select(Tenant.nombre)) == "Datos anteriores"
    motor.dispose()
