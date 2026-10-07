from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from app.api.deps import SessionDep, TenantDep
from app.models import Empresa, Expediente, Gestor, Miembro
from app.schemas import ComprasProveedorFila, ProduccionFila, ProduccionResumen

router = APIRouter(prefix="/produccion", tags=["produccion"])


@router.get("/resumen", response_model=ProduccionResumen)
def resumen(session: SessionDep, tenant_id: TenantDep) -> ProduccionResumen:
    consulta = (
        select(
            Expediente.usuario_id,
            Miembro.codigo,
            Miembro.nombre,
            Expediente.gestor_id,
            Gestor.codigo,
            Gestor.nombre,
            Expediente.moneda,
            func.count(Expediente.id),
            func.coalesce(func.sum(Expediente.importe_total), 0),
        )
        .outerjoin(Miembro, Expediente.usuario_id == Miembro.id)
        .outerjoin(Gestor, Expediente.gestor_id == Gestor.id)
        .where(
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
        )
        .group_by(
            Expediente.usuario_id,
            Miembro.codigo,
            Miembro.nombre,
            Expediente.gestor_id,
            Gestor.codigo,
            Gestor.nombre,
            Expediente.moneda,
        )
        .order_by(Miembro.codigo, Gestor.codigo, Expediente.moneda)
    )
    filas = [
        ProduccionFila(
            usuario_id=usuario_id,
            usuario_codigo=usuario_codigo or "SIN-USUARIO",
            usuario_nombre=usuario_nombre or "Sin usuario asignado",
            gestor_id=gestor_id,
            gestor_codigo=gestor_codigo or "SIN-GESTOR",
            gestor_nombre=gestor_nombre or "Sin gestor asignado",
            moneda=moneda,
            expedientes=expedientes,
            importe_total=Decimal(importe_total),
        )
        for (
            usuario_id,
            usuario_codigo,
            usuario_nombre,
            gestor_id,
            gestor_codigo,
            gestor_nombre,
            moneda,
            expedientes,
            importe_total,
        ) in session.execute(consulta)
    ]
    return ProduccionResumen(filas=filas)


@router.get("/compras", response_model=list[ComprasProveedorFila])
def compras(session: SessionDep, tenant_id: TenantDep) -> list[ComprasProveedorFila]:
    emisor = aliased(Empresa)
    receptor = aliased(Empresa)
    consulta = (
        select(
            Miembro.codigo,
            Gestor.codigo,
            emisor.ruc,
            emisor.razon_social,
            receptor.ruc,
            receptor.razon_social,
            Expediente.moneda,
            func.count(Expediente.id),
            func.coalesce(func.sum(Expediente.importe_total), 0),
        )
        .outerjoin(Miembro, Expediente.usuario_id == Miembro.id)
        .outerjoin(Gestor, Expediente.gestor_id == Gestor.id)
        .join(emisor, Expediente.emisor_id == emisor.id)
        .join(receptor, Expediente.receptor_id == receptor.id)
        .where(
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
        )
        .group_by(
            Miembro.codigo,
            Gestor.codigo,
            emisor.ruc,
            emisor.razon_social,
            receptor.ruc,
            receptor.razon_social,
            Expediente.moneda,
        )
        .order_by(Miembro.codigo, Gestor.codigo, emisor.razon_social, receptor.razon_social)
    )
    return [
        ComprasProveedorFila(
            usuario_codigo=usuario_codigo or "SIN-USUARIO",
            gestor_codigo=gestor_codigo or "SIN-GESTOR",
            emisor_ruc=emisor_ruc,
            emisor_razon_social=emisor_nombre,
            receptor_ruc=receptor_ruc,
            receptor_razon_social=receptor_nombre,
            moneda=moneda,
            expedientes=expedientes,
            importe_total=Decimal(importe_total),
        )
        for (
            usuario_codigo,
            gestor_codigo,
            emisor_ruc,
            emisor_nombre,
            receptor_ruc,
            receptor_nombre,
            moneda,
            expedientes,
            importe_total,
        ) in session.execute(consulta)
    ]
