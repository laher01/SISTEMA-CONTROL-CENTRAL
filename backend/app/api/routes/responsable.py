"""Vista de consulta del Responsable: pedidos, clientes y pagos de su equipo."""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import (
    AsignacionPedidoGerencia,
    Empresa,
    Expediente,
    Miembro,
    PagoERP,
    PedidoGerencia,
)

router = APIRouter(prefix="/responsable", tags=["responsable"])


@router.get("/resumen")
def resumen_equipo(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> dict[str, object]:
    if auth.rol != RolMiembro.RESPONSABLE or auth.miembro_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Responsable")
    usuarios = list(
        session.scalars(
            select(Miembro)
            .where(
                Miembro.tenant_id == tenant_id,
                Miembro.responsable_id == auth.miembro_id,
                Miembro.rol == RolMiembro.USUARIO,
                Miembro.deleted_at.is_(None),
                Miembro.activo.is_(True),
            )
            .order_by(Miembro.codigo)
        )
    )
    ids = [u.id for u in usuarios]
    if not ids:
        return {"usuarios": [], "clientes": [], "pedidos": [], "pagos": []}

    clientes = [
        {
            "usuario_id": str(uid),
            "receptor_id": str(eid),
            "ruc": ruc,
            "razon_social": nombre,
            "moneda": moneda,
            "expedientes": cantidad,
            "produccion": str(Decimal(total)),
        }
        for uid, eid, ruc, nombre, moneda, cantidad, total in session.execute(
            select(
                Expediente.usuario_id,
                Empresa.id,
                Empresa.ruc,
                Empresa.razon_social,
                Expediente.moneda,
                func.count(Expediente.id),
                func.coalesce(func.sum(Expediente.importe_total), 0),
            )
            .join(Empresa, Expediente.receptor_id == Empresa.id)
            .where(
                Expediente.tenant_id == tenant_id,
                Empresa.tenant_id == tenant_id,
                Expediente.usuario_id.in_(ids),
                Expediente.deleted_at.is_(None),
            )
            .group_by(
                Expediente.usuario_id,
                Empresa.id,
                Empresa.ruc,
                Empresa.razon_social,
                Expediente.moneda,
            )
            .order_by(Empresa.razon_social)
        )
    ]
    pedidos = [
        {
            "usuario_id": str(uid),
            "cliente": nombre,
            "periodo": periodo.isoformat(),
            "moneda": moneda,
            "monto_asignado": str(Decimal(monto)),
            "estado": estado,
        }
        for uid, nombre, periodo, moneda, monto, estado in session.execute(
            select(
                AsignacionPedidoGerencia.usuario_id,
                Empresa.razon_social,
                PedidoGerencia.periodo_mes,
                PedidoGerencia.moneda,
                AsignacionPedidoGerencia.monto_asignado,
                PedidoGerencia.estado,
            )
            .join(PedidoGerencia, AsignacionPedidoGerencia.pedido_id == PedidoGerencia.id)
            .join(Empresa, PedidoGerencia.cliente_id == Empresa.id)
            .where(
                AsignacionPedidoGerencia.tenant_id == tenant_id,
                PedidoGerencia.tenant_id == tenant_id,
                Empresa.tenant_id == tenant_id,
                AsignacionPedidoGerencia.usuario_id.in_(ids),
            )
            .order_by(PedidoGerencia.periodo_mes.desc())
        )
    ]
    pagos = [
        {
            "usuario_id": str(p.usuario_id),
            "periodo_desde": p.periodo_desde.isoformat(),
            "periodo_hasta": p.periodo_hasta.isoformat(),
            "moneda": p.moneda,
            "produccion": str(p.produccion_total),
            "bruto": str(p.bruto),
            "adelantos": str(p.adelantos),
            "saldo": str(p.saldo),
            "estado": p.estado,
        }
        for p in session.scalars(
            select(PagoERP)
            .where(PagoERP.tenant_id == tenant_id, PagoERP.usuario_id.in_(ids))
            .order_by(PagoERP.periodo_hasta.desc())
        )
    ]
    return {
        "usuarios": [
            {"id": str(u.id), "codigo": u.codigo, "nombre": u.nombre}
            for u in usuarios
        ],
        "clientes": clientes,
        "pedidos": pedidos,
        "pagos": pagos,
    }
