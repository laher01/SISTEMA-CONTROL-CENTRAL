import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_hoy
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.environ.get("FC_TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")


class Reloj:
    def __init__(self) -> None:
        self.hoy = date(2026, 9, 15)


@pytest.fixture
def engine() -> Iterator[Engine]:
    if TEST_DATABASE_URL.startswith("sqlite"):
        motor = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        motor = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(motor)
    Base.metadata.create_all(motor)
    yield motor
    Base.metadata.drop_all(motor)
    motor.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with sessionmaker(engine, expire_on_commit=False)() as s:
        yield s


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(storage_dir=tmp_path / "storage", tenant_default="pruebas")


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def client(engine: Engine, settings: Settings, reloj: Reloj) -> Iterator[TestClient]:
    fabrica = sessionmaker(engine, expire_on_commit=False)

    def sesion() -> Iterator[Session]:
        with fabrica() as s:
            yield s

    app.dependency_overrides[get_session] = sesion
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_hoy] = lambda: reloj.hoy
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
