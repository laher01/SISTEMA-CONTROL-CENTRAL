"""Los vínculos N:M no deben autorizar falsos positivos ni cruces de tenant."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Documento, Tenant
from app.services.vinculos_documentales import RelacionInvalida, vincular


def _doc(session: Session, tenant_id: uuid.UUID, tipo: str, indice: int) -> Documento:
    documento = Documento(
        tenant_id=tenant_id,
        tipo_documento=tipo,
        estado="PENDIENTE_RELACION",
        sha256=f"{indice:064x}",
        nombre_original=f"{indice}.pdf",
        mime_type="application/pdf",
        tamano_bytes=10,
        ruta_storage=f"/tmp/{indice}.pdf",
    )
    session.add(documento)
    session.flush()
    return documento


def test_cotizacion_orden_idempotente_y_varias_relaciones(session: Session) -> None:
    tenant = Tenant(nombre="TENANT VINCULOS A", codigo="VINCULOSA")
    session.add(tenant)
    session.flush()
    cotizacion = _doc(session, tenant.id, "COT", 10)
    oc1 = _doc(session, tenant.id, "OC", 11)
    oc2 = _doc(session, tenant.id, "OC", 12)
    primera = vincular(
        session,
        tenant.id,
        cotizacion.id,
        oc1.id,
        tipo="COTIZACION_OC",
        evidencia="OC cita cotización COT-001",
    )
    repetida = vincular(
        session,
        tenant.id,
        cotizacion.id,
        oc1.id,
        tipo="COTIZACION_OC",
        evidencia="OC cita cotización COT-001",
    )
    segunda = vincular(
        session,
        tenant.id,
        cotizacion.id,
        oc2.id,
        tipo="COTIZACION_OC",
        evidencia="OC cita cotización COT-001",
    )
    assert primera.id == repetida.id
    assert primera.id != segunda.id


def test_no_cruzar_tenant_ni_aceptar_sin_evidencia(session: Session) -> None:
    a = Tenant(nombre="TENANT VINCULOS B", codigo="VINCULOSB")
    b = Tenant(nombre="TENANT VINCULOS C", codigo="VINCULOSC")
    session.add_all([a, b])
    session.flush()
    factura = _doc(session, a.id, "FACT", 20)
    voucher = _doc(session, b.id, "VCHR", 21)
    with pytest.raises(RelacionInvalida):
        vincular(
            session,
            a.id,
            voucher.id,
            factura.id,
            tipo="VOUCHER_FACTURA",
            evidencia="Referencia de transferencia",
        )
    voucher_mismo_tenant = _doc(session, a.id, "VCHR", 22)
    with pytest.raises(RelacionInvalida):
        vincular(
            session,
            a.id,
            voucher_mismo_tenant.id,
            factura.id,
            tipo="VOUCHER_FACTURA",
            evidencia=" ",
        )
