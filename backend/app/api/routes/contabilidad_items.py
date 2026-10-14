"""Consultas de solo lectura: Contabilidad de Ítems, aislada por tenant."""
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import OperativeAuthDep, SessionDep
from app.item_models import LineaComprobanteItem, ProductoItem
from app.models import Documento, Expediente
from app.services.ambito_gerencia import alcance_expedientes_gerente

router = APIRouter(prefix="/contabilidad-items", tags=["contabilidad-items"])


def _alcance(auth: OperativeAuthDep):
    if auth.rol in ("ADMINISTRADOR", "SECRETARIA"):
        return True
    if auth.rol == "GERENTE":
        return alcance_expedientes_gerente(auth)
    if auth.rol == "USUARIO":
        return Expediente.usuario_id == auth.usuario_id
    if auth.rol == "GESTOR":
        return Expediente.gestor_id == auth.gestor_id
    raise HTTPException(403, "Rol sin acceso al módulo")


@router.get("")
def resumen(
    session: SessionDep,
    auth: OperativeAuthDep,
    desde: date | None = None,
    hasta: date | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    limite: int = Query(100, ge=1, le=500),
) -> list[dict[str, str]]:
    """No mezcla unidades ni incluye facturas pendientes de auditoría."""
    alcance = _alcance(auth)
    stmt = (
        select(
            ProductoItem.id,
            ProductoItem.categoria,
            ProductoItem.descripcion,
            LineaComprobanteItem.unidad,
            func.sum(LineaComprobanteItem.cantidad).label("cantidad"),
        )
        .join(LineaComprobanteItem, LineaComprobanteItem.producto_id == ProductoItem.id)
        .join(Documento, Documento.id == LineaComprobanteItem.documento_id)
        .join(Expediente, Expediente.id == Documento.expediente_id)
        .where(
            ProductoItem.tenant_id == auth.tenant_id,
            LineaComprobanteItem.tenant_id == auth.tenant_id,
            Documento.tenant_id == auth.tenant_id,
            Expediente.tenant_id == auth.tenant_id,
            Documento.deleted_at.is_(None),
            Expediente.deleted_at.is_(None),
            ProductoItem.activo.is_(True),
            alcance,
            ~select(1)
            .select_from(__import__("app.item_models", fromlist=["AuditoriaFacturaItem"]).AuditoriaFacturaItem)
            .where(
                __import__("app.item_models", fromlist=["AuditoriaFacturaItem"]).AuditoriaFacturaItem.expediente_id
                == Expediente.id,
                __import__("app.item_models", fromlist=["AuditoriaFacturaItem"]).AuditoriaFacturaItem.tenant_id
                == auth.tenant_id,
                __import__("app.item_models", fromlist=["AuditoriaFacturaItem"]).AuditoriaFacturaItem.estado
                == "INVALIDADA_CONFIRMADA",
            )
            .exists(),
        )
    )
    if desde:
        stmt = stmt.where(Expediente.fecha_emision >= desde)
    if hasta:
        stmt = stmt.where(Expediente.fecha_emision <= hasta)
    if emisor_id:
        stmt = stmt.where(Expediente.emisor_id == emisor_id)
    if receptor_id:
        stmt = stmt.where(Expediente.receptor_id == receptor_id)
    stmt = stmt.group_by(
        ProductoItem.id,
        ProductoItem.categoria,
        ProductoItem.descripcion,
        LineaComprobanteItem.unidad,
    ).order_by(ProductoItem.descripcion).limit(limite)
    return [
        {
            "producto_id": str(r.id),
            "categoria": r.categoria,
            "descripcion": r.descripcion,
            "unidad": r.unidad,
            "cantidad": str(Decimal(r.cantidad)),
        }
        for r in session.execute(stmt)
    ]
