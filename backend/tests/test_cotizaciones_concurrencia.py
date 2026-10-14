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


def test_api_importacion_semantica_simultanea_postgresql(engine, client) -> None:
    """Solicitudes HTTP paralelas compiten por una misma huella en PostgreSQL."""
    if engine.dialect.name != "postgresql":
        pytest.skip("La concurrencia HTTP exige PostgreSQL real")

    from test_separador_pdf import _paquete

    from app.models import RelacionDocumento

    archivos = [
        _paquete(
            [
                "COTIZACION No. 00450\nPROVEEDOR RUC 20615898598",
                f"COTIZACION No. 0045{indice + 1}\nPROVEEDOR RUC 20615898598",
            ]
        )
        for indice in range(2)
    ]
    barrera = Barrier(2, timeout=15)

    def enviar(pdf: bytes):
        barrera.wait()
        return client.post(
            "/api/v1/documentos/paquete",
            data={"confirmar": "true"},
            files={"archivo": ("lote.pdf", pdf, "application/pdf")},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        respuestas = list(pool.map(enviar, archivos))

    assert all(respuesta.status_code == 200 for respuesta in respuestas), [
        (respuesta.status_code, respuesta.text) for respuesta in respuestas
    ]
    assert sum(respuesta.json()["duplicados"] for respuesta in respuestas) == 1

    with Session(engine) as session:
        hijos = list(session.scalars(select(Documento).where(Documento.tipo_documento == "COT")))
        assert len(hijos) == 3
        assert len({hijo.huella_comercial for hijo in hijos}) == 3
        relaciones = list(session.scalars(select(RelacionDocumento)))
        assert len(relaciones) == 3
