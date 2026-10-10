"""Comisiones auditables y pagos exclusivamente a Responsables por Gerencia."""

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.enums import RolMiembro
from app.models import (
    Auditoria,
    ComisionResponsableRegla,
    Empresa,
    Expediente,
    Miembro,
    MovimientoPagoResponsable,
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
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Periodo inválido: máximo 367 días"
        )
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
    gerente_id: uuid.UUID | None = None,
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
    if gerente_id is not None:
        consulta = consulta.where(Expediente.gerente_id == gerente_id)
    else:
        # Los expedientes sin atribución no se liquidan por aproximación.
        consulta = consulta.where(Expediente.gerente_id.is_not(None))
    consulta = consulta.group_by(
        usuario.responsable_id,
        Empresa.id,
        Empresa.ruc,
        Empresa.razon_social,
        Empresa.agente_retencion,
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
    pedidos: dict[tuple[uuid.UUID | None, uuid.UUID], Decimal] = {}
    for pedido_item in session.scalars(
        select(PedidoGerencia).where(
            PedidoGerencia.tenant_id == tenant_id,
            PedidoGerencia.periodo_mes >= primer_mes,
            PedidoGerencia.periodo_mes <= ultimo_mes,
            PedidoGerencia.moneda == moneda,
            PedidoGerencia.estado != "CANCELADO",
            PedidoGerencia.gerente_id == gerente_id
            if gerente_id is not None
            else PedidoGerencia.gerente_id.is_not(None),
        )
    ):
        llave = (pedido_item.responsable_id, pedido_item.cliente_id)
        pedidos[llave] = pedidos.get(llave, Decimal("0")) + Decimal(pedido_item.monto_solicitado)
    filas: list[dict[str, object]] = []
    total_produccion = Decimal("0")
    total_comisiones = Decimal("0")
    for rid, cid, ruc, empresa, es_agente, base in agrupados:
        responsable = responsables.get(rid)
        if responsable is None:
            continue
        importe = Decimal(base)
        regla = reglas.get((rid, cid))
        porcentaje = (
            Decimal(regla.porcentaje)
            if regla
            else (Decimal("3.0") if es_agente else Decimal("3.5"))
        )
        comision = _redondear(importe * porcentaje / Decimal("100"))
        pedido_base = pedidos.get((rid, cid), Decimal("0"))
        exceso = max(importe - pedido_base, Decimal("0"))
        filas.append(
            {
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
                "pedido": str(_redondear(pedido_base)),
                "exceso": str(_redondear(exceso)),
            }
        )
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
    gerente_id = auth.miembro_id if auth.rol == RolMiembro.GERENTE else None
    if auth.rol == RolMiembro.GERENTE and gerente_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Gerente sin identidad")
    resultado = _calculo(session, tenant_id, desde, hasta, moneda, responsable_id, gerente_id)
    if auth.rol == RolMiembro.GERENTE and auth.codigo == "GRTEGLOBAL":
        # Solo informativo: sin pedido/gerente verificados no genera comisiones pagables.
        consulta_historica = (
            select(
                Miembro.responsable_id,
                func.sum(Expediente.importe_total),
                func.count(Expediente.id),
            )
            .outerjoin(Miembro, Expediente.usuario_id == Miembro.id)
            .where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                Expediente.gerente_id.is_(None),
                Expediente.fecha_emision.between(desde, hasta),
                Expediente.moneda == moneda,
            )
            .group_by(Miembro.responsable_id)
        )
        historicos = list(session.execute(consulta_historica))
        responsables = {
            m.id: m
            for m in session.scalars(
                select(Miembro).where(
                    Miembro.tenant_id == tenant_id,
                    Miembro.id.in_([fila[0] for fila in historicos]),
                )
            )
        }
        resultado["pendientes_atribucion"] = [
            {
                "responsable_id": str(rid) if rid else "sin-responsable",
                "responsable": responsables[rid].codigo
                if rid in responsables
                else "SIN RESPONSABLE",
                "registros": n,
                "produccion": str(_redondear(Decimal(total))),
            }
            for rid, total, n in historicos
        ]
        resultado["total_pendiente_atribucion"] = str(
            _redondear(sum((Decimal(total) for _, total, _ in historicos), Decimal("0")))
        )
    return resultado


@router.put("/comision")
def modificar_comision(
    datos: ReglaComisionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    _ambito(auth, datos.responsable_id)
    if auth.rol == RolMiembro.GERENTE:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Las comisiones personalizadas globales requieren Administración",
        )
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
        session,
        tenant_id,
        "COMISION_RESPONSABLE_MODIFICADA",
        "comision_responsable",
        regla.id,
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
    if auth.rol == RolMiembro.GERENTE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Historial reservado a Administración")
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
        select(Auditoria)
        .where(
            Auditoria.tenant_id == tenant_id,
            Auditoria.entidad == "comision_responsable",
            Auditoria.entidad_id == regla.id,
        )
        .order_by(Auditoria.created_at.desc())
        .limit(100)
    )
    return [{"fecha": e.created_at.isoformat(), "datos": e.datos or {}} for e in eventos]


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
    if auth.rol != RolMiembro.GERENTE or auth.miembro_id is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "La liquidación de Gerencia requiere Gerente pagador identificado",
        )
    resumen_calculado = _calculo(
        session,
        tenant_id,
        datos.desde,
        datos.hasta,
        datos.moneda,
        datos.responsable_id,
        auth.miembro_id,
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
            PagoResponsableERP.gerente_id == auth.miembro_id,
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
        gerente_id=auth.miembro_id,
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
        session,
        tenant_id,
        "PAGO_RESPONSABLE_PROGRAMADO",
        "pago_responsable",
        pago.id,
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
    if auth.rol == RolMiembro.GERENTE:
        consulta = consulta.where(PagoResponsableERP.gerente_id == auth.miembro_id)
    pagos = list(
        session.scalars(consulta.order_by(PagoResponsableERP.created_at.desc()).limit(150))
    )
    ids = [p.id for p in pagos]
    abonos = {
        pid: Decimal(str(total or 0))
        for pid, total in session.execute(
            select(
                MovimientoPagoResponsable.pago_id,
                func.sum(MovimientoPagoResponsable.monto),
            )
            .where(
                MovimientoPagoResponsable.tenant_id == tenant_id,
                MovimientoPagoResponsable.pago_id.in_(ids),
            )
            .group_by(MovimientoPagoResponsable.pago_id)
        )
    }
    return [
        {
            "id": str(p.id),
            "responsable_id": str(p.responsable_id),
            "gerente_id": str(p.gerente_id) if p.gerente_id else None,
            "periodo_desde": p.periodo_desde.isoformat(),
            "periodo_hasta": p.periodo_hasta.isoformat(),
            "moneda": p.moneda,
            "produccion_total": str(p.produccion_total),
            "comision_total": str(p.comision_total),
            "estado": p.estado,
            "fecha_pago": p.fecha_pago.isoformat() if p.fecha_pago else None,
            "referencia_pago": p.referencia_pago,
            "abonado": str(
                p.comision_total if p.estado == "PAGADO" else abonos.get(p.id, Decimal("0"))
            ),
            "saldo": str(
                Decimal("0")
                if p.estado == "PAGADO"
                else max(Decimal("0"), p.comision_total - abonos.get(p.id, Decimal("0")))
            ),
            "fecha_reprogramada": (
                p.fecha_reprogramada.isoformat() if p.fecha_reprogramada else None
            ),
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
    if auth.rol == RolMiembro.GERENTE and pago.gerente_id != auth.miembro_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    if pago.estado != "PROGRAMADO":
        raise HTTPException(status.HTTP_409_CONFLICT, "Pago ya registrado o anulado")
    pago.estado = "PAGADO"
    pago.fecha_pago = datos.fecha_pago
    pago.referencia_pago = datos.referencia_pago.strip()
    pago.pagado_por_cuenta_id = auth.cuenta_id
    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_RESPONSABLE_CONFIRMADO",
        "pago_responsable",
        pago.id,
        {
            "importe": str(pago.comision_total),
            "fecha_pago": datos.fecha_pago.isoformat(),
            "referencia": datos.referencia_pago.strip(),
            "actor": auth.codigo,
        },
    )
    session.commit()
    return {"id": str(pago.id), "estado": pago.estado}


class ReprogramarPagoIn(BaseModel):
    fecha: date
    motivo: str = Field(min_length=5, max_length=500)


@router.post("/{pago_id}/reprogramar")
def reprogramar_pago(
    pago_id: uuid.UUID,
    datos: ReprogramarPagoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    if auth.rol != RolMiembro.GERENTE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Gerencia reprograma")
    pago = session.get(PagoResponsableERP, pago_id)
    if pago is None or pago.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    if auth.rol == RolMiembro.GERENTE and pago.gerente_id != auth.miembro_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    if pago.estado in ("PAGADO", "ANULADO"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Liquidación cerrada")
    if datos.fecha.replace(day=1) <= pago.periodo_hasta.replace(day=1):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Reprogramación debe indicar un mes posterior al periodo",
        )
    pago.fecha_reprogramada = datos.fecha
    pago.observacion = datos.motivo
    pago.estado = "REPROGRAMADO"
    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_RESPONSABLE_REPROGRAMADO",
        "pago_responsable",
        pago.id,
        {"fecha": datos.fecha.isoformat(), "motivo": datos.motivo, "actor": auth.codigo},
    )
    session.commit()
    return {"id": str(pago.id), "estado": pago.estado}


@router.post("/{pago_id}/abonar")
async def abonar_responsable(
    pago_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    settings: SettingsDep,
    accion: Literal["TOTAL", "ADELANTO"] = Form(...),
    monto: Decimal | None = Form(None),
    fecha: date = Form(...),
    referencia: str = Form(...),
    comprobante: UploadFile = File(...),
) -> dict[str, str]:
    if auth.rol != RolMiembro.GERENTE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Gerencia registra abonos")
    pago = session.scalar(
        select(PagoResponsableERP)
        .where(
            PagoResponsableERP.id == pago_id,
            PagoResponsableERP.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if pago is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    if auth.rol == RolMiembro.GERENTE and pago.gerente_id != auth.miembro_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    if pago.estado in ("PAGADO", "ANULADO"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Liquidación cerrada")
    abonado = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(MovimientoPagoResponsable.monto), 0)).where(
                MovimientoPagoResponsable.tenant_id == tenant_id,
                MovimientoPagoResponsable.pago_id == pago.id,
            )
        )
        or 0
    )
    saldo = pago.comision_total - abonado
    valor = saldo if accion == "TOTAL" else monto
    if valor is None or valor <= 0 or valor > saldo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Importe fuera del saldo")
    if valor != valor.quantize(CENTIMO):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Importe con más de dos decimales"
        )
    referencia = referencia.strip()
    if len(referencia) < 4 or len(referencia) > 160:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Referencia inválida")
    repetido = session.scalar(
        select(MovimientoPagoResponsable.id).where(
            MovimientoPagoResponsable.pago_id == pago.id,
            MovimientoPagoResponsable.referencia == referencia,
        )
    )
    if repetido is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Referencia ya registrada")
    tipos = {"image/png": ".png", "image/jpeg": ".jpg", "application/pdf": ".pdf"}
    extension = tipos.get(comprobante.content_type or "")
    if extension is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Solo PDF, JPG o PNG")
    datos_archivo = await comprobante.read(10 * 1024 * 1024 + 1)
    if not datos_archivo or len(datos_archivo) > 10 * 1024 * 1024:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Comprobante vacío o muy grande")
    firma_valida = (
        (extension == ".pdf" and datos_archivo.startswith(b"%PDF-"))
        or (extension == ".png" and datos_archivo.startswith(b"\x89PNG\r\n\x1a\n"))
        or (extension == ".jpg" and datos_archivo.startswith(b"\xff\xd8\xff"))
    )
    if not firma_valida:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Contenido de comprobante inválido"
        )
    carpeta = Path(settings.storage_dir) / "pagos-responsables" / str(tenant_id) / str(pago.id)
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = uuid.uuid4().hex + extension
    ruta = carpeta / archivo
    ruta.write_bytes(datos_archivo)
    try:
        movimiento = MovimientoPagoResponsable(
            tenant_id=tenant_id,
            pago_id=pago.id,
            monto=valor,
            fecha=fecha,
            referencia=referencia,
            comprobante_archivo=archivo,
            creado_por_cuenta_id=auth.cuenta_id,
        )
        session.add(movimiento)
        session.flush()
        pago.estado = "PAGADO" if valor == saldo else "PARCIAL"
        if pago.estado == "PAGADO":
            pago.fecha_pago = fecha
            pago.referencia_pago = referencia
            pago.pagado_por_cuenta_id = auth.cuenta_id
        auditoria.registrar(
            session,
            tenant_id,
            "PAGO_RESPONSABLE_ABONADO",
            "pago_responsable",
            pago.id,
            {"monto": str(valor), "saldo": str(saldo - valor), "actor": auth.codigo},
        )
        session.commit()
    except Exception:
        session.rollback()
        ruta.unlink(missing_ok=True)
        raise
    return {
        "id": str(pago.id),
        "estado": pago.estado,
        "abonado": str(abonado + valor),
        "saldo": str(saldo - valor),
    }


@router.get("/{pago_id}/movimientos")
def movimientos_responsable(
    pago_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[dict[str, str]]:
    _ambito(auth)
    pago = session.get(PagoResponsableERP, pago_id)
    if pago is None or pago.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    if auth.rol == RolMiembro.GERENTE and pago.gerente_id != auth.miembro_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    _ambito(auth, pago.responsable_id)
    movimientos = session.scalars(
        select(MovimientoPagoResponsable)
        .where(
            MovimientoPagoResponsable.tenant_id == tenant_id,
            MovimientoPagoResponsable.pago_id == pago_id,
        )
        .order_by(MovimientoPagoResponsable.created_at)
    )
    return [
        {
            "id": str(m.id),
            "fecha": m.fecha.isoformat(),
            "monto": str(m.monto),
            "referencia": m.referencia,
        }
        for m in movimientos
    ]


@router.get("/{pago_id}/movimientos/{movimiento_id}/comprobante")
def descargar_comprobante_responsable(
    pago_id: uuid.UUID,
    movimiento_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    settings: SettingsDep,
) -> FileResponse:
    _ambito(auth)
    pago = session.get(PagoResponsableERP, pago_id)
    if pago is None or pago.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    if auth.rol == RolMiembro.GERENTE and pago.gerente_id != auth.miembro_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    _ambito(auth, pago.responsable_id)
    movimiento = session.get(MovimientoPagoResponsable, movimiento_id)
    if movimiento is None or movimiento.tenant_id != tenant_id or movimiento.pago_id != pago.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")
    archivo = Path(settings.storage_dir) / "pagos-responsables" / str(tenant_id)
    ruta = archivo / str(pago.id) / movimiento.comprobante_archivo
    if not ruta.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comprobante no disponible")
    return FileResponse(ruta, filename=movimiento.comprobante_archivo)
