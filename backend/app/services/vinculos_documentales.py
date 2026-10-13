"""Crear vínculos N:M con evidencia explícita y aislamiento por tenant."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Documento, RelacionDocumento


class RelacionInvalida(ValueError):
    pass


TIPOS_PERMITIDOS = {
    "FACTURA_GRE": ({"FACT"}, {"GRR", "GRT"}),
    "GRE_TRANSPORTISTA": ({"GRR"}, {"GRT"}),
    "COTIZACION_OC": ({"COT"}, {"OC"}),
    "OC_FACTURA": ({"OC"}, {"FACT"}),
    "VOUCHER_FACTURA": ({"VCHR"}, {"FACT"}),
}


def vincular(
    session: Session,
    tenant_id: uuid.UUID,
    origen_id: uuid.UUID,
    destino_id: uuid.UUID,
    *,
    tipo: str,
    evidencia: str,
    confirmado_por_cuenta_id: uuid.UUID | None = None,
) -> RelacionDocumento:
    """Persistir solo asociaciones verificadas; nunca usar monto/fecha como única prueba."""
    if origen_id == destino_id or tipo not in TIPOS_PERMITIDOS:
        raise RelacionInvalida("Tipo de vínculo o documentos inválidos")
    if not evidencia.strip() or len(evidencia) > 500:
        raise RelacionInvalida("Falta evidencia verificable de la relación")
    documentos = list(
        session.scalars(
            select(Documento).where(
                Documento.tenant_id == tenant_id,
                Documento.id.in_((origen_id, destino_id)),
                Documento.deleted_at.is_(None),
            )
        )
    )
    if len(documentos) != 2:
        raise RelacionInvalida("Ambos documentos deben existir dentro del mismo tenant")
    por_id = {documento.id: documento for documento in documentos}
    desde, hacia = TIPOS_PERMITIDOS[tipo]
    if (
        por_id[origen_id].tipo_documento not in desde
        or por_id[destino_id].tipo_documento not in hacia
    ):
        raise RelacionInvalida("Tipos documentales incompatibles")
    previo = session.scalar(
        select(RelacionDocumento).where(
            RelacionDocumento.tenant_id == tenant_id,
            RelacionDocumento.origen_id == origen_id,
            RelacionDocumento.destino_id == destino_id,
            RelacionDocumento.tipo == tipo,
        )
    )
    if previo is not None:
        return previo
    relacion = RelacionDocumento(
        tenant_id=tenant_id,
        origen_id=origen_id,
        destino_id=destino_id,
        tipo=tipo,
        evidencia=evidencia.strip(),
        confirmado_por_cuenta_id=confirmado_por_cuenta_id,
    )
    session.add(relacion)
    session.flush()
    return relacion
