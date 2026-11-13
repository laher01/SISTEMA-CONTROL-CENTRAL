"""Exclusión operativa por rubro en los comprobantes activos."""

from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement

from app.item_models import LineaComprobanteItem, ProductoItem
from app.models import Documento, Expediente


def expediente_fuera_rubro() -> ColumnElement[bool]:
    return (
        select(LineaComprobanteItem.id)
        .join(ProductoItem, ProductoItem.id == LineaComprobanteItem.producto_id)
        .join(Documento, Documento.id == LineaComprobanteItem.documento_id)
        .where(
            Documento.expediente_id == Expediente.id,
            Documento.tenant_id == Expediente.tenant_id,
            Documento.deleted_at.is_(None),
            LineaComprobanteItem.tenant_id == Expediente.tenant_id,
            ProductoItem.tenant_id == Expediente.tenant_id,
            ProductoItem.fuera_rubro.is_(True),
        )
        .correlate(Expediente)
        .exists()
    )
