"""Synthetic GRE reference and accounting boundary checks, no OCR inference."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem
from app.models import Documento, Empresa, Expediente, ReferenciaGRE
from app.services.ingesta import registrar_referencia_gre
from app.services.referencias_gre import ReferenciaFacturaGRE


def test_gre_provisional_does_not_invent_factura_or_economic_items(session: Session, auth_prueba):
    tenant_id = auth_prueba.contexto.tenant_id
    guide = Documento(
        tenant_id=tenant_id,
        sha256="3" * 64,
        nombre_original="gre.xml",
        mime_type="application/xml",
        tamano_bytes=20,
        ruta_storage="synthetic/gre",
        estado="PENDIENTE_RELACION",
        tipo_documento="GRR",
    )
    session.add(guide)
    session.flush()
    reference = ReferenciaFacturaGRE(
        serie="F001",
        correlativo="900",
        emisor_ruc="20611111001",
        receptor_ruc="20611111002",
    )
    first = registrar_referencia_gre(session, guide, reference)
    session.flush()
    first_id = first.id
    second = registrar_referencia_gre(session, guide, reference)
    session.commit()

    assert second.id == first_id
    assert (
        session.scalar(
            select(func.count())
            .select_from(ReferenciaGRE)
            .where(
            ReferenciaGRE.tenant_id == tenant_id,
            ReferenciaGRE.documento_id == guide.id,
            )
        )
        == 1
    )
    assert (
        session.scalar(
            select(func.count())
            .select_from(Expediente)
            .where(
            Expediente.tenant_id == tenant_id,
            Expediente.tipo_comprobante == "FACT",
            )
        )
        == 0
    )
    assert (
        session.scalar(
            select(func.count())
            .select_from(LineaComprobanteItem)
            .where(
            LineaComprobanteItem.tenant_id == tenant_id
            )
        )
        == 0
    )
    assert session.get(Documento, guide.id).expediente_id is None


def test_factura_and_guide_same_tenant_do_not_multiply_invoice_amount(
    session: Session, auth_prueba
):
    tenant_id = auth_prueba.contexto.tenant_id
    issuer = Empresa(tenant_id=tenant_id, ruc="20611111001", razon_social="Emisor prueba")
    buyer = Empresa(tenant_id=tenant_id, ruc="20611111002", razon_social="Cliente prueba")
    session.add_all([issuer, buyer])
    session.flush()
    dossier = Expediente(
        tenant_id=tenant_id,
        emisor_id=issuer.id,
        receptor_id=buyer.id,
        tipo_comprobante="FACT",
        serie="F001",
        correlativo="900",
        fecha_emision=date(2026, 10, 18),
        moneda="PEN",
        importe_total=Decimal("150.00"),
        estado="NARANJA",
    )
    session.add(dossier)
    session.flush()
    for name, kind, digest in (
        ("factura.xml", "FACT", "4" * 64),
        ("gre.xml", "GRR", "5" * 64),
        ("voucher.pdf", "VCHR", "6" * 64),
    ):
        session.add(
            Documento(
                tenant_id=tenant_id,
                expediente_id=dossier.id,
                sha256=digest,
                nombre_original=name,
                mime_type="application/octet-stream",
                tamano_bytes=5,
                ruta_storage=f"synthetic/{name}",
                estado="RELACIONADO",
                tipo_documento=kind,
            )
        )
    session.commit()
    assert (
        session.scalar(
            select(func.count())
            .select_from(Expediente)
            .where(
            Expediente.tenant_id == tenant_id,
            Expediente.serie == "F001",
            Expediente.correlativo == "900",
            )
        )
        == 1
    )
    assert session.scalar(
        select(Expediente.importe_total).where(Expediente.id == dossier.id)
    ) == Decimal("150.00")
    assert session.scalar(
        select(func.count()).select_from(Documento).where(
            Documento.tenant_id == tenant_id, Documento.expediente_id == dossier.id
        )
    ) == 3
