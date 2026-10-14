"""Comprobaciones del contrato de almacenamiento de la huella comercial."""

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models import Documento


def test_esquema_huella_comercial_nullable_y_unica(engine, auth_prueba) -> None:
    columnas = {
        columna["name"]: columna for columna in inspect(engine).get_columns("documentos")
    }
    assert "huella_comercial" in columnas
    assert columnas["huella_comercial"]["nullable"] is True

    restricciones = inspect(engine).get_unique_constraints("documentos")
    assert any(
        set(constraint["column_names"]) == {"tenant_id", "huella_comercial"}
        for constraint in restricciones
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
        documento = session.scalar(
            select(Documento).where(Documento.sha256 == "c" * 64)
        )
        assert documento is not None
        assert documento.huella_comercial is None
