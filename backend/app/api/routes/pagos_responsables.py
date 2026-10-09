"""Comisiones auditables y pagos exclusivamente a Responsables por Gerencia."""

import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import (
    Auditoria,
    ComisionResponsableRegla,
    Empresa,
    Expediente,
    Miembro,
    PagoResponsableERP,
    PedidoGerencia,
)
from app.services import auditoria

router = APIRouter(prefix="/pagos-responsables", tags=["pagos-responsables"])
MONEDAS = {"PEN", "USD"}
CENTIMO = Decimal("0.01")
ROLES_LECTURA = (
    RolMiembro.SUPERADMIN,
    RolMiembro.ADMINISTRADOR,
    RolMiembro.GERENTE,
    RolMiembro.RESPONSABLE,
)


class ReglaComisionIn(BaseModel):
    responsable_id: uuid.UUID
    cliente_id: uuid.UUID
    porcentaje: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=4)
    motivo: str = Field(min_length=5, max_length=500)


class ProgramarPagoResponsableIn(BaseModel):
    responsable_id: uuid.UUID
    desde: date
    hasta: date
    moneda: str = Field(pattern="^(PEN|USD)$")
    observacion: str | None = Field(default=None, max_length=500)


class ConfirmarPagoResponsableIn(BaseModel):
    fecha_pago: date
    referencia_pago: str = Field(min_length=4, max_length=160)


def _ambito(auth: OperativeAuthDep, responsable_id: uuid.UUID | None = None) -> None:
    if auth.rol not in ROLES_LECTURA:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso al resumen de responsables")
    if auth.rol == RolMiembro.RESPONSABLE and (
        auth.miembro_id is None
        or (responsable_id is not None and responsable_id != auth.miembro_id)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Fuera de su equipo")


def _responsable(session: SessionDep, tenant_id: uuid.UUID, responsable_id: uuid.UUID) -> Miembro:
    r = session.get(Miembro, responsable_id)
    if (
        r is None
        or r.tenant_id != tenant_id
        or r.rol != RolMiembro.RESPONSABLE
        or not r.activo
        or r.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Responsable inválido")
    return r


def _periodo(desde: date, hasta: date, moneda: str) -> None:
    if hasta < desde or (hasta - desde).days > 366:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Periodo inválido: máximo 367 días")
    if moneda not in MONEDAS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Moneda inválida")


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTIMO, rounding=ROUND_HALF_UP)


def _calculo(
    session: SessionDep,
    tenant_id: uuid.UUID,
    desde: date,
    hasta: date,
    moneda: str,
    responsable_id: uuid.UUID | None,
) -> dict[str, object]:
    _periodo(desde, hasta, moneda)
    usuario = Miembro
    consulta = (
        select(
            usuario.responsable_id,
            Empresa.id,
            Empresa.ruc,
            Empresa.razon_social,
            Empresa.agente_retencion,
            func.sum(Expediente.importe_total).label("produccion"),
        )
        .join(usuario, Expediente.usuario_id == usuario.id)
        .join(Empresa, Expediente.receptor_id == Empresa.id)
        .where(
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
            Expediente.fecha_emision >= desde,
            Expediente.fecha_emision <= hasta,
            Expediente.moneda == moneda,
            usuario.tenant_id == tenant_id,
            usuario.rol == RolMiembro.USUARIO,
            usuario.deleted_at.is_(None),
            usuario.responsable_id.is_not(None),
            Empresa.tenant_id == tenant_id,
            Empresa.deleted_at.is_(None),
        )
    )
    if responsable_id is not None:
        consulta = consulta.where(usuario.responsable_id == responsable_id)
    consulta = consulta.group_by(
        usuario.responsable_id, Empresa.id, Empresa.ruc,
        Empresa.razon_social, Empresa.agente_retencion,
    )
    agrupados = list(session.execute(consulta))
    ids_responsables = {r[0] for r in agrupados}
    ids_clientes = {r[1] for r in agrupados}
    responsables = {
        r.id: r
        for r in session.scalars(
            select(Miembro).where(
                Miembro.tenant_id == tenant_id,
                Miembro.id.in_(ids_responsables),
                Miembro.rol == RolMiembro.RESPONSABLE,
                Miembro.deleted_at.is_(None),
            )
        )
    }
    reglas = {
        (r.responsable_id, r.cliente_id): r
        for r in session.scalars(
            select(ComisionResponsableRegla).where(
                ComisionResponsableRegla.tenant_id == tenant_id,
                ComisionResponsableRegla.responsable_id.in_(ids_responsables),
                ComisionResponsableRegla.cliente_id.in_(ids_clientes),
            )
        )
    }
    # Se comparan los pedidos de meses incluidos; un rango parcial compara
    # igualmente el pedido mensual, explicitado en el frontend.
    primer_mes = desde.replace(day=1)
    ultimo_mes = hasta.replace(day=1)
    pedidos = {
        (p.responsable_id, p.cliente_id): Decimal("0")
        for p in session.scalars(
            select(PedidoGerencia).where(
                PedidoGerencia.tenant_id == tenant_id,
                PedidoGerencia.periodo_mes >= primer_mes,
                PedidoGerencia.periodo_mes <= ultimo_mes,
                PedidoGerencia.moneda == moneda,
                PedidoGerencia.estado != "CANCELADO",
            )
        )
    }
    for pedido in session.scalars(
        select(PedidoGerencia).where(
            PedidoGerencia.tenant_id == tenant_id,
            PedidoGerencia.periodo_mes >= primer_mes,
            PedidoGerencia.periodo_mes <= ultimo_mes,
            PedidoGerencia.moneda == moneda,
            PedidoGerencia.estado != "CANCELADO",
        )
    ):
        llave = (pedido.responsable_id, pedido.cliente_id)
        pedidos[llave] = pedidos.get(llave, Decimal("0")) + Decimal(pedido.monto_solicitado)
    filas: list[dict[str, object]] = []
    total_produccion = Decimal("0")
    total_comisiones = Decimal("0")
    for rid, cid, ruc, empresa, es_agente, base in agrupados:
        responsable = responsables.get(rid)
        if responsable is None:
            continue
        importe = Decimal(base)
        regla = reglas.get((rid, cid))
        porcentaje = Decimal(regla.porcentaje) if regla else (
            Decimal("3.0") if es_agente else Decimal("3.5")
        )
        comision = _redondear(importe * porcentaje / Decimal("100"))
        pedido = pedidos.get((rid, cid), Decimal("0"))
        exceso = max(importe - pedido, Decimal("0"))
        filas.append({
            "responsable_id": str(rid),
            "responsable_codigo": responsable.codigo,
            "responsable_nombre": responsable.nombre,
            "cliente_id": str(cid),
            "cliente_ruc": ruc,
            "cliente_nombre": empresa,
            "agente_retencion": bool(es_agente),
            "produccion": str(_redondear(importe)),
            "porcentaje": str(porcentaje),
            "porcentaje_personalizado": regla is not None,
            "comision": str(comision),
            "pedido": str(_redondear(pedido)),
            "exceso": str(_redondear(exceso)),
        })
        total_produccion += importe
        total_comisiones += comision
    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "moneda": moneda,
        "total_produccion": str(_redondear(total_produccion)),
        "total_comisiones": str(_redondear(total_comisiones)),
        "filas": filas,
    }


@router.get("/resumen")
def resumen(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    desde: date,
    hasta: date,
    moneda: str = "PEN",
) -> dict[str, object]:
    _ambito(auth)
    responsable_id = auth.miembro_id if auth.rol == RolMiembro.RESPONSABLE else None
    return _calculo(session, tenant_id, desde, hasta, moneda, responsable_id)


@router.put("/comision")
def modificar_comision(
    datos: ReglaComisionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    _ambito(auth, datos.responsable_id)
    _responsable(session, tenant_id, datos.responsable_id)
    cliente = session.get(Empresa, datos.cliente_id)
    if cliente is None or cliente.tenant_id != tenant_id or cliente.deleted_at is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cliente inválido")
    regla = session.scalar(
        select(ComisionResponsableRegla).where(
            ComisionResponsableRegla.tenant_id == tenant_id,
            ComisionResponsableRegla.responsable_id == datos.responsable_id,
            ComisionResponsableRegla.cliente_id == datos.cliente_id,
        )
    )
    anterior = (
        Decimal(regla.porcentaje)
        if regla is not None
        else Decimal("3.0" if cliente.agente_retencion else "3.5")
    )
    if regla is None:
        regla = ComisionResponsableRegla(
            tenant_id=tenant_id,
            responsable_id=datos.responsable_id,
            cliente_id=datos.cliente_id,
            porcentaje=datos.porcentaje,
            creado_por_cuenta_id=auth.cuenta_id,
            actualizado_por_cuenta_id=auth.cuenta_id,
        )
        session.add(regla)
        session.flush()
    else:
        regla.porcentaje = datos.porcentaje
        regla.actualizado_por_cuenta_id = auth.cuenta_id
    auditoria.registrar(
        session, tenant_id, "COMISION_RESPONSABLE_MODIFICADA",
        "comision_responsable", regla.id,
        {
            "responsable_id": str(datos.responsable_id),
            "cliente_id": str(datos.cliente_id),
            "anterior": str(anterior),
            "nuevo": str(datos.porcentaje),
            "actor": auth.codigo,
            "motivo": datos.motivo,
        },
    )
    session.commit()
    return {"porcentaje": str(datos.porcentaje)}


@router.get("/comision/{responsable_id}/{cliente_id}/historial")
def historial_comision(
    responsable_id: uuid.UUID,
    cliente_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[dict[str, object]]:
    _ambito(auth, responsable_id)
    regla = session.scalar(
        select(ComisionResponsableRegla).where(
            ComisionResponsableRegla.tenant_id == tenant_id,
            ComisionResponsableRegla.responsable_id == responsable_id,
            ComisionResponsableRegla.cliente_id == cliente_id,
        )
    )
    if regla is None:
        return []
    eventos = session.scalars(
        select(Auditoria).where(
            Auditoria.tenant_id == tenant_id,
            Auditoria.entidad == "comision_responsable",
            Auditoria.entidad_id == regla.id,
        ).order_by(Auditoria.created_at.desc()).limit(100)
    )
    return [
        {"fecha": e.created_at.isoformat(), "datos": e.datos or {}}
        for e in eventos
    ]


@router.post("/programar", status_code=status.HTTP_201_CREATED)
def programar(
    datos: ProgramarPagoResponsableIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    if auth.rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR, RolMiembro.GERENTE):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede programar pagos a Responsables")
    _responsable(session, tenant_id, datos.responsable_id)
    resumen_calculado = _calculo(
        session, tenant_id, datos.desde, datos.hasta, datos.moneda, datos.responsable_id,
    )
    filas = resumen_calculado["filas"]
    assert isinstance(filas, list)
    if not filas:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Sin producción en el periodo")
    # Rechaza solapamientos aunque se intente pagar con otro rango.
    solape = session.scalar(
        select(PagoResponsableERP.id).where(
            PagoResponsableERP.tenant_id == tenant_id,
            PagoResponsableERP.responsable_id == datos.responsable_id,
            PagoResponsableERP.moneda == datos.moneda,
            PagoResponsableERP.periodo_desde <= datos.hasta,
            PagoResponsableERP.periodo_hasta >= datos.desde,
            PagoResponsableERP.estado != "ANULADO",
        )
    )
    if solape is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe pago en periodo solapado")
    pago = PagoResponsableERP(
        tenant_id=tenant_id,
        responsable_id=datos.responsable_id,
        periodo_desde=datos.desde,
        periodo_hasta=datos.hasta,
        moneda=datos.moneda,
        produccion_total=Decimal(str(resumen_calculado["total_produccion"])),
        comision_total=Decimal(str(resumen_calculado["total_comisiones"])),
        detalle={"filas": filas},
        estado="PROGRAMADO",
        observacion=datos.observacion,
        creado_por_cuenta_id=auth.cuenta_id,
    )
    session.add(pago)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El pago ya existe") from exc
    auditoria.registrar(
        session, tenant_id, "PAGO_RESPONSABLE_PROGRAMADO", "pago_responsable", pago.id,
        {
            "responsable_id": str(datos.responsable_id),
            "periodo": f"{datos.desde} / {datos.hasta}",
            "importe": str(pago.comision_total),
            "actor": auth.codigo,
        },
    )
    session.commit()
    return {"id": str(pago.id), "estado": pago.estado, "comision_total": str(pago.comision_total)}


@router.get("")
def listar_pagos(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[dict[str, object]]:
    _ambito(auth)
    consulta = select(PagoResponsableERP).where(PagoResponsableERP.tenant_id == tenant_id)
    if auth.rol == RolMiembro.RESPONSABLE:
        consulta = consulta.where(PagoResponsableERP.responsable_id == auth.miembro_id)
    pagos = session.scalars(
        consulta.order_by(PagoResponsableERP.created_at.desc()).limit(150)
    )
    return [
        {
            "id": str(p.id),
            "responsable_id": str(p.responsable_id),
            "periodo_desde": p.periodo_desde.isoformat(),
            "periodo_hasta": p.periodo_hasta.isoformat(),
            "moneda": p.moneda,
            "produccion_total": str(p.produccion_total),
            "comision_total": str(p.comision_total),
            "estado": p.estado,
            "fecha_pago": p.fecha_pago.isoformat() if p.fecha_pago else None,
            "referencia_pago": p.referencia_pago,
        }
        for p in pagos
    ]


@router.post("/{pago_id}/confirmar")
def confirmar(
    pago_id: uuid.UUID,
    datos: ConfirmarPagoResponsableIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    if auth.rol != RolMiembro.GERENTE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Gerencia confirma pagos")
    pago = session.get(PagoResponsableERP, pago_id)
    if pago is None or pago.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    if pago.estado != "PROGRAMADO":
        raise HTTPException(status.HTTP_409_CONFLICT, "Pago ya registrado o anulado")
    pago.estado = "PAGADO"
    pago.fecha_pago = datos.fecha_pago
    pago.referencia_pago = datos.referencia_pago.strip()
    pago.pagado_por_cuenta_id = auth.cuenta_id
    auditoria.registrar(
        session, tenant_id, "PAGO_RESPONSABLE_CONFIRMADO", "pago_responsable", pago.id,
        {
            "importe": str(pago.comision_total),
            "fecha_pago": datos.fecha_pago.isoformat(),
            "referencia": datos.referencia_pago.strip(),
            "actor": auth.codigo,
        },
    )
    session.commit()
    return {"id": str(pago.id), "estado": pago.estado}
