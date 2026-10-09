import runpy
import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Base, CuentaAcceso, Tenant


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


def test_migracion_0017_protege_auditoria_y_downgrade_aislado(tmp_path: Path) -> None:
    motor = create_engine(f"sqlite:///{tmp_path / 'operaciones.db'}")
    tablas_previas = [t for t in Base.metadata.sorted_tables if not t.name.startswith("infra_")]
    Base.metadata.create_all(motor, tables=tablas_previas)
    carpeta = Path(__file__).parents[1] / "alembic/versions"
    anterior = runpy.run_path(str(carpeta / "20261009_0016_infraestructura.py"))
    actual = runpy.run_path(str(carpeta / "20261009_0017_operaciones_infra.py"))
    with motor.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            anterior["upgrade"]()
            actual["upgrade"]()
        tenant_id = connection.execute(
            Tenant.__table__.insert().values(nombre="Conservar")
        ).inserted_primary_key[0]
        cuenta_id = connection.execute(
            CuentaAcceso.__table__.insert().values(
                tenant_id=tenant_id,
                login="auditor",
                password_hash="hash",
            )
        ).inserted_primary_key[0]
        connection.execute(
            text("""
            INSERT INTO infra_eventos
                (id, actor_cuenta_id, correlacion_id, accion, recurso_id, resultado, datos)
            VALUES (:id, :actor, :correlacion, 'AUDITORIA', :recurso, 'EXITO', '{}')
        """),
            {
                "id": uuid.uuid4().hex,
                "actor": cuenta_id.hex,
                "correlacion": uuid.uuid4().hex,
                "recurso": uuid.uuid4().hex,
            },
        )
        for sentencia in ("UPDATE infra_eventos SET accion='OTRA'", "DELETE FROM infra_eventos"):
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(text(sentencia))
        with Operations.context(MigrationContext.configure(connection)):
            actual["downgrade"]()
        assert "infra_operaciones" not in inspect(connection).get_table_names()
        assert connection.scalar(select(Tenant.nombre)) == "Conservar"
    motor.dispose()
