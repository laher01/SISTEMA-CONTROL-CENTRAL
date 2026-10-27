"""Comprobaciones del contrato de almacenamiento de la huella comercial."""

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models import Documento


def test_esquema_huella_comercial_nullable_y_unica(engine, auth_prueba) -> None:
    columnas = {columna["name"]: columna for columna in inspect(engine).get_columns("documentos")}
    assert "huella_comercial" in columnas
    assert columnas["huella_comercial"]["nullable"] is True

    indices = inspect(engine).get_indexes("documentos")
    assert any(
        set(indice["column_names"]) == {"tenant_id", "huella_comercial"}
        and indice["unique"]
        for indice in indices
    )

    # La nueva columna no puede invalidar documentos históricos sin huella.
    tenant_id = auth_prueba.contexto.tenant_id
    with Session(engine) as session:
        session.add(
            Documento(
                tenant_id=tenant_id,
                tipo_documento="COT",
                estado="PENDIENTE",
                sha256="c" * 64,
                huella_comercial=None,
                nombre_original="legado.pdf",
                mime_type="application/pdf",
                tamano_bytes=10,
                ruta_storage="pruebas/legado.pdf",
            )
        )
        session.commit()
        documento = session.scalar(select(Documento).where(Documento.sha256 == "c" * 64))
        assert documento is not None
        assert documento.huella_comercial is None
