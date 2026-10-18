"""PostgreSQL-only fiscal identity concurrency regression; isolated synthetic test."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente


def test_factura_identity_unique_during_two_concurrent_transactions(engine, auth_prueba):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL transaction concurrency")
    tenant_id = auth_prueba.contexto.tenant_id
    with Session(engine) as session:
        emisor = Empresa(tenant_id=tenant_id, ruc="20611111222", razon_social="Emisor sintético")
        receptor = Empresa(tenant_id=tenant_id, ruc="20633333444", razon_social="Receptor sintético")
        session.add_all([emisor, receptor])
        session.commit()
        emisor_id, receptor_id = emisor.id, receptor.id

    barrier = Barrier(2, timeout=20)

    def insert(_: int) -> str:
        with Session(engine) as session:
            item = Expediente(
                tenant_id=tenant_id, emisor_id=emisor_id, receptor_id=receptor_id,
                tipo_comprobante="FACT", serie="F001", correlativo="123456",
                fecha_emision=date(2026, 10, 18), moneda="PEN",
                importe_total=Decimal("100.00"), estado="NARANJA",
            )
            session.add(item)
            barrier.wait()
            try:
                session.commit()
                return "created"
            except IntegrityError:
                session.rollback()
                return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(insert, (1, 2)))
    assert sorted(results) == ["created", "duplicate"]
    with Session(engine) as session:
        count = session.scalar(
            select(func.count()).select_from(Expediente).where(
                Expediente.tenant_id == tenant_id,
                Expediente.emisor_id == emisor_id,
                Expediente.receptor_id == receptor_id,
                Expediente.tipo_comprobante == "FACT",
                Expediente.serie == "F001",
                Expediente.correlativo == "123456",
            )
        )
    assert count == 1
