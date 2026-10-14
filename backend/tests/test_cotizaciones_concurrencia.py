"""Verificación real de exclusión concurrente sobre PostgreSQL, nunca SQLite."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Documento


def _paquete(paginas: list[str]) -> bytes:
    """Genera dos o más páginas PDF legibles sin depender de otros módulos de pruebas."""
    import io

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    salida = PdfWriter()
    for contenido in paginas:
        hoja = salida.add_blank_page(width=595, height=842)
        fuente = DictionaryObject(
            {
                NameObject("/F1"): DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                    }
                )
            }
        )
        hoja[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fuente})
        operadores = ["BT /F1 10 Tf 20 780 Td"]
        for linea in contenido.splitlines():
            operadores.append(f"({linea}) Tj 0 -20 Td")
        operadores.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\\n".join(operadores).encode("ascii"))
        hoja[NameObject("/Contents")] = salida._add_object(stream)
    memoria = io.BytesIO()
    salida.write(memoria)
    return memoria.getvalue()


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
