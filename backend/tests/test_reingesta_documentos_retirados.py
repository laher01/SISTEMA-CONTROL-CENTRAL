from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.enums import Moneda, TipoComprobante
from app.models import Alerta, Documento, Expediente, ahora
from app.services.ingesta import (
    ArchivoSubido,
    DocumentoDuplicado,
    crear_expediente,
    ingerir_documento,
)
from app.storage import AlmacenLocal


def test_reingresa_sha_de_documento_retirado_y_bloquea_el_activo(
    session: Session, settings, reloj, auth_prueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    contenido = b"%PDF-1.4\narchivo de prueba sin datos fiscales\n"
    almacen = AlmacenLocal(settings.storage_dir)

    anterior = ingerir_documento(
        session,
        almacen,
        settings,
        reloj.hoy,
        tenant_id,
        ArchivoSubido("factura.pdf", "application/pdf", contenido),
    )
    anterior.deleted_at = ahora()
    session.commit()

    nuevo = ingerir_documento(
        session,
        almacen,
        settings,
        reloj.hoy,
        tenant_id,
        ArchivoSubido("factura-nueva.pdf", "application/pdf", contenido),
    )
    session.commit()

    assert nuevo.id != anterior.id
    assert nuevo.sha256 == anterior.sha256
    anterior_guardado = session.get(Documento, anterior.id)
    nuevo_guardado = session.get(Documento, nuevo.id)
    assert anterior_guardado is not None and anterior_guardado.deleted_at is not None
    assert nuevo_guardado is not None and nuevo_guardado.deleted_at is None

    with pytest.raises(DocumentoDuplicado):
        ingerir_documento(
            session,
            almacen,
            settings,
            reloj.hoy,
            tenant_id,
            ArchivoSubido("duplicado-activo.pdf", "application/pdf", contenido),
        )


def test_crea_nuevo_expediente_fiscal_si_el_anterior_esta_retirado_y_conserva_alertas(
    session: Session, settings, reloj, auth_prueba
) -> None:
    reloj.hoy = date(2026, 10, 27)
    tenant_id = auth_prueba.contexto.tenant_id

    def crear() -> Expediente:
        return crear_expediente(
            session,
            settings,
            reloj.hoy,
            tenant_id=tenant_id,
            receptor=("20175642341", "ESTACION DE SERVICIOS SAN JOSE SAC"),
            emisor=("20400000001", "PROVEEDOR DE PRUEBA"),
            tipo_comprobante=TipoComprobante.FACT,
            serie="F091",
            correlativo="7220",
            fecha_emision=date(2026, 9, 30),
            moneda=Moneda.PEN,
            importe_total=Decimal("31200.00"),
            requiere_guia=True,
            gestor_id=None,
            usuario_id=auth_prueba.contexto.usuario_id,
            creado_por_cuenta_id=auth_prueba.contexto.cuenta_id,
        )

    anterior = crear()
    session.commit()
    alertas_antes = list(session.scalars(select(Alerta).where(Alerta.expediente_id == anterior.id)))
    assert alertas_antes

    anterior.deleted_at = ahora()
    session.commit()

    nuevo = crear()
    session.commit()

    assert nuevo.id != anterior.id
    assert nuevo.deleted_at is None
    anterior_guardado = session.get(Expediente, anterior.id)
    assert anterior_guardado is not None and anterior_guardado.deleted_at is not None
    alertas_despues = list(
        session.scalars(select(Alerta).where(Alerta.expediente_id == anterior.id))
    )
    assert [(a.id, a.tipo, a.mensaje, a.resuelta, a.resuelta_at) for a in alertas_despues] == [
        (a.id, a.tipo, a.mensaje, a.resuelta, a.resuelta_at) for a in alertas_antes
    ]

    with pytest.raises(IntegrityError):
        crear()
    session.rollback()
