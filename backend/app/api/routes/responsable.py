"""Vista de consulta del Responsable: pedidos, clientes y pagos de su equipo."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

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


class DistribucionIn(BaseModel):
    usuario_id: uuid.UUID
    monto: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


@router.post("/pedidos/{pedido_id}/distribuir")
def distribuir_pedido(
    pedido_id: uuid.UUID,
    datos: DistribucionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    """Responsable distribuye presupuestos asignados, sin crear facturas o pagos."""
    if auth.rol != RolMiembro.RESPONSABLE or auth.miembro_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Responsable")
    pedido = session.get(PedidoGerencia, pedido_id)
    if (
        pedido is None
        or pedido.tenant_id != tenant_id
        or pedido.responsable_id != auth.miembro_id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no asignado al Responsable")
    if pedido.estado != "ACTIVO":
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido no está activo")
    usuario = session.get(Miembro, datos.usuario_id)
    if (
        usuario is None
        or usuario.tenant_id != tenant_id
        or usuario.responsable_id != auth.miembro_id
        or usuario.rol != RolMiembro.USUARIO
        or not usuario.activo
        or usuario.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario fuera de su equipo")
    # Bloqueo de fila PostgreSQL para que dos distribuciones simultáneas no excedan el pedido.
    session.execute(
        select(PedidoGerencia.id).where(PedidoGerencia.id == pedido_id).with_for_update()
    ).first()
    asignaciones = list(
        session.scalars(
            select(AsignacionPedidoGerencia).where(
                AsignacionPedidoGerencia.tenant_id == tenant_id,
                AsignacionPedidoGerencia.pedido_id == pedido.id,
            )
        )
    )
    existentes = [
        a for a in asignaciones
        if a.usuario_id == usuario.id and a.gestor_id is None and a.proveedor_id is None
    ]
    if any(a.usuario_id == usuario.id for a in asignaciones) and not existentes:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El usuario ya tiene asignaciones específicas"
        )
    nuevo_total = sum(
        (Decimal(a.monto_asignado) for a in asignaciones if a not in existentes),
        Decimal("0"),
    ) + datos.monto
    if nuevo_total > Decimal(pedido.monto_solicitado):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Supera el presupuesto bruto")
    if existentes:
        existentes[0].monto_asignado = datos.monto
    else:
        session.add(
            AsignacionPedidoGerencia(
                tenant_id=tenant_id,
                pedido_id=pedido.id,
                usuario_id=usuario.id,
                monto_asignado=datos.monto,
                creado_por_cuenta_id=auth.cuenta_id,
            )
        )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de asignación") from exc
    return {"pedido_id": str(pedido.id), "total_asignado": str(nuevo_total)}


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
    pedidos = []
    for pedido in session.scalars(
        select(PedidoGerencia)
        .where(
            PedidoGerencia.tenant_id == tenant_id,
            PedidoGerencia.responsable_id == auth.miembro_id,
        )
        .order_by(PedidoGerencia.periodo_mes.desc())
    ):
        cliente = session.get(Empresa, pedido.cliente_id)
        if cliente is None or cliente.tenant_id != tenant_id:
            continue
        asignaciones = list(
            session.scalars(
                select(AsignacionPedidoGerencia).where(
                    AsignacionPedidoGerencia.tenant_id == tenant_id,
                    AsignacionPedidoGerencia.pedido_id == pedido.id,
                )
            )
        )
        asignado = sum((Decimal(a.monto_asignado) for a in asignaciones), Decimal("0"))
        pedidos.append(
            {
                "id": str(pedido.id),
                "cliente": cliente.razon_social,
                "ruc": cliente.ruc,
                "periodo": pedido.periodo_mes.isoformat(),
                "moneda": pedido.moneda,
                "monto_solicitado": str(pedido.monto_solicitado),
                "monto_asignado": str(asignado),
                "pendiente_distribuir": str(Decimal(pedido.monto_solicitado) - asignado),
                "estado": pedido.estado,
                "asignaciones": [
                    {
                        "usuario_id": str(a.usuario_id),
                        "monto": str(a.monto_asignado),
                    }
                    for a in asignaciones
                ],
            }
        )
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
        "usuarios": [{"id": str(u.id), "codigo": u.codigo, "nombre": u.nombre} for u in usuarios],
        "clientes": clientes,
        "pedidos": pedidos,
        "pagos": pagos,
    }
