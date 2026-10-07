from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import Empresa, Expediente, Gestor, Miembro
from app.schemas import ComprasProveedorFila, ProduccionFila, ProduccionResumen

router = APIRouter(prefix="/produccion", tags=["produccion"])


@router.get("/resumen", response_model=ProduccionResumen)
def resumen(session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep) -> ProduccionResumen:
    _validar_acceso_produccion(auth.rol)
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
        .where(*_scope(auth))
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
def compras(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[ComprasProveedorFila]:
    _validar_acceso_produccion(auth.rol)
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
        .where(*_scope(auth))
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


def _scope(auth: OperativeAuthDep) -> tuple[ColumnElement[bool], ...]:
    if auth.rol == "GESTOR":
        return (Expediente.gestor_id == auth.gestor_id,)
    if auth.rol == RolMiembro.USUARIO:
        return (Expediente.usuario_id == auth.usuario_id,)
    return ()


def _validar_acceso_produccion(rol: str) -> None:
    if rol not in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
        RolMiembro.USUARIO,
        "GESTOR",
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para ver Producción")
