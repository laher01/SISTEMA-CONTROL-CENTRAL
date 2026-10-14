"""Consultas de solo lectura: Contabilidad de Ítems, aislada por tenant."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, true
from sqlalchemy.sql.elements import ColumnElement

from app.api.deps import OperativeAuthDep, SessionDep
from app.item_models import AuditoriaFacturaItem, LineaComprobanteItem, ProductoItem
from app.models import Documento, Expediente
from app.services.ambito_gerencia import alcance_expedientes_gerente
from app.services.contabilidad_items_auditoria import registrar_decision, resolver_propuesta

router = APIRouter(prefix="/contabilidad-items", tags=["contabilidad-items"])


def _alcance(auth: OperativeAuthDep) -> ColumnElement[bool]:
    if auth.rol in ("ADMINISTRADOR", "SECRETARIA"):
        return true()
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
    ultimo_estado = (
        select(AuditoriaFacturaItem.estado)
        .where(
            AuditoriaFacturaItem.expediente_id == Expediente.id,
            AuditoriaFacturaItem.tenant_id == auth.tenant_id,
        )
        .order_by(AuditoriaFacturaItem.created_at.desc(), AuditoriaFacturaItem.id.desc())
        .limit(1)
        .scalar_subquery()
    )
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
            or_(
                ultimo_estado.is_(None),
                ultimo_estado.not_in(
                    ["INVALIDADA_CONFIRMADA", "INVALIDADA_PENDIENTE", "REACTIVACION_PENDIENTE"]
                ),
            ),
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
    stmt = (
        stmt.group_by(
            ProductoItem.id,
            ProductoItem.categoria,
            ProductoItem.descripcion,
            LineaComprobanteItem.unidad,
        )
        .order_by(ProductoItem.descripcion)
        .limit(limite)
    )
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

class DecisionItemsIn(BaseModel):
    accion: Literal["OBSERVAR", "DESACTIVAR", "REACTIVAR"]
    motivo: str = Field(min_length=3, max_length=1000)


@router.post("/expedientes/{expediente_id}/auditar")
def auditar_factura(
    expediente_id: uuid.UUID,
    datos: DecisionItemsIn,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    decision = registrar_decision(session, auth, expediente_id, datos.accion, datos.motivo)
    session.commit()
    return {"decision_id": str(decision.id), "estado": decision.estado}


@router.post("/auditorias/{decision_id}/resolver")
def resolver_auditoria(
    decision_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
    aprobar: bool = True,
) -> dict[str, str]:
    decision = resolver_propuesta(session, auth, decision_id, aprobar)
    session.commit()
    return {"decision_id": str(decision.id), "estado": decision.estado}
