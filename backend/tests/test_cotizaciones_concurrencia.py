"""Verificación real de exclusión concurrente sobre PostgreSQL, nunca SQLite."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Documento


def test_huella_comercial_concurrente_postgresql(engine, auth_prueba) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("La concurrencia comercial exige PostgreSQL real")

    tenant_id = auth_prueba.contexto.tenant_id
    huella = "b" * 64
    barrera = Barrier(2, timeout=15)

    def importar(numero: int) -> str:
        with Session(engine) as session:
            documento = Documento(
                tenant_id=tenant_id,
                tipo_documento="COT",
                estado="PENDIENTE",
                sha256=f"{numero:064x}",
                huella_comercial=huella,
                nombre_original=f"cotizacion-{numero}.pdf",
                mime_type="application/pdf",
                tamano_bytes=12,
                ruta_storage=f"pruebas/cotizacion-{numero}.pdf",
            )
            session.add(documento)
            barrera.wait()
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return "duplicado"
            return "creado"

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(importar, 1)
        b = pool.submit(importar, 2)
        resultados = [a.result(timeout=30), b.result(timeout=30)]

    assert sorted(resultados) == ["creado", "duplicado"]
    with Session(engine) as session:
        cantidad = session.scalar(
            select(func.count())
            .select_from(Documento)
            .where(Documento.tenant_id == tenant_id, Documento.huella_comercial == huella)
        )
    assert cantidad == 1
