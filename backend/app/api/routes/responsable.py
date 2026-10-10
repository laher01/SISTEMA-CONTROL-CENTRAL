"""Vista de consulta del Responsable: pedidos, clientes y pagos de su equipo."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import (
    AdelantoERP,
    AplicacionAdelantoERP,
    AsignacionPedidoGerencia,
    Empresa,
    Expediente,
    Miembro,
    PagoERP,
    PedidoGerencia,
    PlanLiquidacion,
    SaldoCompraERP,
)
from app.services import auditoria

router = APIRouter(prefix="/responsable", tags=["responsable"])


class DistribucionIn(BaseModel):
    usuario_id: uuid.UUID
    monto: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class ProgramarUsuarioIn(BaseModel):
    usuario_id: uuid.UUID
    desde: date
    hasta: date
    moneda: str = Field(pattern="^(PEN|USD)$")
    saldo_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    porcentajes_saldos: dict[uuid.UUID, Decimal] = Field(default_factory=dict)
    adelanto_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    porcentaje_manual: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=7, decimal_places=4
    )
    observacion_adelantos: str | None = Field(default=None, max_length=500)


class NuevoSaldoIn(BaseModel):
    usuario_id: uuid.UUID
    periodo_mes: date
    moneda: str = Field(pattern="^(PEN|USD)$")
    monto: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    detalle: str = Field(min_length=8, max_length=500)


class ConfirmarLiquidacionIn(BaseModel):
    fecha_pago: date
    referencia_pago: str = Field(min_length=4, max_length=160)


def _usuario_del_responsable(
    session: SessionDep, tenant_id: uuid.UUID, responsable_id: uuid.UUID, usuario_id: uuid.UUID
) -> Miembro:
    usuario = session.get(Miembro, usuario_id)
    if (
        usuario is None
        or usuario.tenant_id != tenant_id
        or usuario.responsable_id != responsable_id
        or usuario.rol != RolMiembro.USUARIO
        or not usuario.activo
        or usuario.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario fuera del equipo")
    return usuario


def _autorizar_pago(
    session: SessionDep, tenant_id: uuid.UUID, auth: OperativeAuthDep, usuario_id: uuid.UUID
) -> Miembro:
    if auth.rol == RolMiembro.RESPONSABLE and auth.miembro_id is not None:
        return _usuario_del_responsable(session, tenant_id, auth.miembro_id, usuario_id)
    if auth.rol in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR):
        usuario = session.get(Miembro, usuario_id)
        if (
            usuario is not None
            and usuario.tenant_id == tenant_id
            and usuario.rol == RolMiembro.USUARIO
            and usuario.activo
            and usuario.deleted_at is None
        ):
            return usuario
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin autorización para este Usuario")


def _componentes_pendientes(
    session: SessionDep,
    tenant_id: uuid.UUID,
    datos: ProgramarUsuarioIn,
) -> tuple[list[SaldoCompraERP], list[AdelantoERP], int]:
    if len(datos.saldo_ids) != len(set(datos.saldo_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Saldos repetidos")
    if len(datos.adelanto_ids) != len(set(datos.adelanto_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Adelantos repetidos")
    saldos = list(
        session.scalars(
            select(SaldoCompraERP)
            .where(
                SaldoCompraERP.tenant_id == tenant_id,
                SaldoCompraERP.usuario_id == datos.usuario_id,
                SaldoCompraERP.moneda == datos.moneda,
                SaldoCompraERP.pago_id.is_(None),
                SaldoCompraERP.id.in_(datos.saldo_ids),
            )
            .with_for_update()
        )
    )
    adelantos = list(
        session.scalars(
            select(AdelantoERP)
            .where(
                AdelantoERP.tenant_id == tenant_id,
                AdelantoERP.usuario_id == datos.usuario_id,
                AdelantoERP.moneda == datos.moneda,
                AdelantoERP.aplicado.is_(False),
                AdelantoERP.id.in_(datos.adelanto_ids),
            )
            .with_for_update()
        )
    )
    if len(saldos) != len(datos.saldo_ids) or len(adelantos) != len(datos.adelanto_ids):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Saldo o adelanto no disponible: actualice la vista antes de liquidar",
        )
    pendientes = int(
        session.scalar(
            select(func.count(AdelantoERP.id)).where(
                AdelantoERP.tenant_id == tenant_id,
                AdelantoERP.usuario_id == datos.usuario_id,
                AdelantoERP.moneda == datos.moneda,
                AdelantoERP.aplicado.is_(False),
            )
        )
        or 0
    )
    return saldos, adelantos, pendientes


def _base_pago_usuario(
    session: SessionDep, tenant_id: uuid.UUID, datos: ProgramarUsuarioIn
) -> tuple[Decimal, Decimal, Decimal, uuid.UUID | None]:
    if datos.hasta < datos.desde or (datos.hasta - datos.desde).days > 366:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Periodo inválido")
    usuario = session.get(Miembro, datos.usuario_id)
    if usuario is None or usuario.tenant_id != tenant_id or usuario.rol != RolMiembro.USUARIO:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Usuario inválido")
    plan = session.scalar(
        select(PlanLiquidacion)
        .where(
            PlanLiquidacion.tenant_id == tenant_id,
            PlanLiquidacion.usuario_id == datos.usuario_id,
            PlanLiquidacion.activo.is_(True),
            PlanLiquidacion.vigencia_desde <= datos.desde,
            (
                PlanLiquidacion.vigencia_hasta.is_(None)
                | (PlanLiquidacion.vigencia_hasta >= datos.hasta)
            ),
        )
        .order_by(PlanLiquidacion.vigencia_desde.desc())
        .limit(1)
    )
    if datos.porcentaje_manual is not None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Configure los dos porcentajes contractuales en Organización; "
            "no se admite una tasa manual única en liquidaciones nuevas",
        )
    produccion_con = Decimal("0")
    produccion_sin = Decimal("0")
    facturas = session.execute(
        select(Expediente.importe_total, Empresa.agente_retencion)
        .join(
            Empresa,
            (Empresa.id == Expediente.receptor_id) & (Empresa.tenant_id == Expediente.tenant_id),
        )
        .where(
            Expediente.tenant_id == tenant_id,
            Expediente.usuario_id == datos.usuario_id,
            Expediente.deleted_at.is_(None),
            Expediente.moneda == datos.moneda,
            Expediente.fecha_emision >= datos.desde,
            Expediente.fecha_emision <= datos.hasta,
        )
    ).all()
    for importe, es_agente in facturas:
        if es_agente:
            produccion_con += Decimal(importe)
        else:
            produccion_sin += Decimal(importe)
    tasa_con = Decimal(
        usuario.porcentaje_con_agente
        if usuario.porcentaje_con_agente is not None
        else usuario.porcentaje_produccion or 0
    )
    tasa_sin = Decimal(
        usuario.porcentaje_sin_agente
        if usuario.porcentaje_sin_agente is not None
        else usuario.porcentaje_produccion or 0
    )
    from app.services.liquidacion_dos_tasas import FacturaProduccion, liquidar_dos_tasas

    calculo = liquidar_dos_tasas(
        [
            FacturaProduccion(importe=Decimal(importe), agente_retencion=bool(es_agente))
            for importe, es_agente in facturas
        ],
        porcentaje_con_agente=tasa_con,
        porcentaje_sin_agente=tasa_sin,
    )
    produccion = produccion_con + produccion_sin
    # El campo histórico porcentaje sigue almacenando una tasa efectiva informativa.
    tasa = (
        (calculo["bruto"] * Decimal("100") / produccion).quantize(Decimal("0.0001"))
        if produccion > 0
        else Decimal("0")
    )
    return produccion, tasa, calculo["bruto"], plan.id if plan is not None else None


@router.get("/pagos/liquidaciones")
def listar_liquidaciones_de_usuario(
    usuario_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[dict[str, str]]:
    _autorizar_pago(session, tenant_id, auth, usuario_id)
    pagos = session.scalars(
        select(PagoERP)
        .where(PagoERP.tenant_id == tenant_id, PagoERP.usuario_id == usuario_id)
        .order_by(PagoERP.periodo_desde.desc())
        .limit(60)
    )
    return [
        {
            "id": str(p.id),
            "periodo_desde": p.periodo_desde.isoformat(),
            "periodo_hasta": p.periodo_hasta.isoformat(),
            "moneda": p.moneda,
            "produccion_total": str(p.produccion_total),
            "porcentaje": str(p.porcentaje),
            "bruto": str(p.bruto),
            "adelantos": str(p.adelantos),
            "saldo": str(p.saldo),
            "estado": p.estado,
            "observacion_adelantos": p.observacion_adelantos or "",
            "referencia_pago": p.referencia_pago or "",
        }
        for p in pagos
    ]


@router.get("/pagos/saldos")
def listar_saldos_pendientes(
    usuario_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[dict[str, str]]:
    _autorizar_pago(session, tenant_id, auth, usuario_id)
    saldos = session.scalars(
        select(SaldoCompraERP)
        .where(
            SaldoCompraERP.tenant_id == tenant_id,
            SaldoCompraERP.usuario_id == usuario_id,
            SaldoCompraERP.pago_id.is_(None),
        )
        .order_by(SaldoCompraERP.periodo_mes)
    )
    return [
        {
            "id": str(s.id),
            "periodo_mes": s.periodo_mes.isoformat(),
            "moneda": s.moneda,
            "monto": str(s.monto),
            "detalle": s.detalle,
        }
        for s in saldos
    ]


@router.post("/pagos/saldos", status_code=status.HTTP_201_CREATED)
def registrar_saldo_pendiente(
    datos: NuevoSaldoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    _autorizar_pago(session, tenant_id, auth, datos.usuario_id)
    if datos.periodo_mes.day != 1:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Use el primer día del mes")
    duplicado = session.scalar(
        select(SaldoCompraERP.id).where(
            SaldoCompraERP.tenant_id == tenant_id,
            SaldoCompraERP.usuario_id == datos.usuario_id,
            SaldoCompraERP.periodo_mes == datos.periodo_mes,
            SaldoCompraERP.moneda == datos.moneda,
            SaldoCompraERP.monto == datos.monto,
            SaldoCompraERP.detalle == datos.detalle.strip(),
            SaldoCompraERP.pago_id.is_(None),
        )
    )
    if duplicado is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese saldo pendiente ya está registrado")
    saldo = SaldoCompraERP(
        tenant_id=tenant_id,
        usuario_id=datos.usuario_id,
        periodo_mes=datos.periodo_mes,
        moneda=datos.moneda,
        monto=datos.monto,
        detalle=datos.detalle.strip(),
        creado_por_cuenta_id=auth.cuenta_id,
    )
    session.add(saldo)
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "SALDO_COMPRAS_AGREGADO",
        "saldo_compra",
        saldo.id,
        {
            "usuario_id": str(datos.usuario_id),
            "periodo": datos.periodo_mes.isoformat(),
            "monto": str(datos.monto),
            "detalle": datos.detalle.strip(),
            "actor": auth.codigo,
        },
    )
    session.commit()
    return {"id": str(saldo.id), "estado": "PENDIENTE"}


@router.get("/pagos/adelantos")
def listar_adelantos_pendientes(
    usuario_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[dict[str, str]]:
    _autorizar_pago(session, tenant_id, auth, usuario_id)
    adelantos = session.scalars(
        select(AdelantoERP)
        .where(
            AdelantoERP.tenant_id == tenant_id,
            AdelantoERP.usuario_id == usuario_id,
            AdelantoERP.aplicado.is_(False),
        )
        .order_by(AdelantoERP.fecha)
    )
    return [
        {
            "id": str(a.id),
            "fecha": a.fecha.isoformat(),
            "moneda": a.moneda,
            "monto": str(a.monto),
            "descripcion": a.descripcion or "",
        }
        for a in adelantos
    ]


@router.post("/pagos/cotizar")
def cotizar_pago_usuario(
    datos: ProgramarUsuarioIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str | int]:
    _autorizar_pago(session, tenant_id, auth, datos.usuario_id)
    produccion, tasa, bruto_produccion, _ = _base_pago_usuario(session, tenant_id, datos)
    saldos, adelantos, total_pendientes = _componentes_pendientes(session, tenant_id, datos)
    if set(datos.porcentajes_saldos) != set(datos.saldo_ids):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Indique el porcentaje histórico de cada saldo seleccionado",
        )
    if any(
        not tasa.is_finite() or tasa < 0 or tasa > 100
        for tasa in datos.porcentajes_saldos.values()
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Porcentaje histórico inválido"
        )
    saldos_total = sum((Decimal(s.monto) for s in saldos), Decimal("0"))
    adelantos_total = sum((Decimal(a.monto) for a in adelantos), Decimal("0"))
    base = produccion + saldos_total
    bruto = bruto_produccion + sum(
        (
            (Decimal(s.monto) * datos.porcentajes_saldos[s.id] / Decimal("100")).quantize(
                Decimal("0.01")
            )
            for s in saldos
        ),
        Decimal("0"),
    )
    neto = bruto - adelantos_total
    return {
        "produccion": str(produccion),
        "saldos_agregados": str(saldos_total),
        "base_global": str(base),
        "porcentaje": str(tasa),
        "bruto": str(bruto),
        "adelantos": str(adelantos_total),
        "neto": str(neto),
        "adelantos_pendientes": total_pendientes,
        "moneda": datos.moneda,
    }


@router.post("/pagos/programar", status_code=status.HTTP_201_CREATED)
def programar_pago_usuario(
    datos: ProgramarUsuarioIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    _autorizar_pago(session, tenant_id, auth, datos.usuario_id)
    anterior = session.scalar(
        select(PagoERP.id).where(
            PagoERP.tenant_id == tenant_id,
            PagoERP.usuario_id == datos.usuario_id,
            PagoERP.moneda == datos.moneda,
            PagoERP.periodo_desde <= datos.hasta,
            PagoERP.periodo_hasta >= datos.desde,
        )
    )
    if anterior is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Existe una liquidación que se solapa")
    produccion, tasa, bruto_produccion, plan_id = _base_pago_usuario(session, tenant_id, datos)
    saldos, adelantos, total_pendientes = _componentes_pendientes(session, tenant_id, datos)
    omitidos = total_pendientes - len(adelantos)
    if omitidos > 0 and (
        not datos.observacion_adelantos or len(datos.observacion_adelantos.strip()) < 8
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Explique en observaciones por qué no se descuentan todos los adelantos",
        )
    if set(datos.porcentajes_saldos) != set(datos.saldo_ids):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Indique el porcentaje histórico de cada saldo seleccionado",
        )
    if any(
        not tasa.is_finite() or tasa < 0 or tasa > 100
        for tasa in datos.porcentajes_saldos.values()
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Porcentaje histórico inválido"
        )
    saldos_total = sum((Decimal(s.monto) for s in saldos), Decimal("0"))
    adelantos_total = sum((Decimal(a.monto) for a in adelantos), Decimal("0"))
    base = produccion + saldos_total
    bruto = bruto_produccion + sum(
        (
            (Decimal(s.monto) * datos.porcentajes_saldos[s.id] / Decimal("100")).quantize(
                Decimal("0.01")
            )
            for s in saldos
        ),
        Decimal("0"),
    )
    neto = bruto - adelantos_total
    if neto < 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Los adelantos seleccionados superan el importe de esta liquidación",
        )
    pago = PagoERP(
        tenant_id=tenant_id,
        usuario_id=datos.usuario_id,
        plan_id=plan_id,
        periodo_desde=datos.desde,
        periodo_hasta=datos.hasta,
        moneda=datos.moneda,
        produccion_total=base,
        porcentaje=tasa,
        bruto=bruto,
        adelantos=adelantos_total,
        ajustes=Decimal("0"),
        saldo=neto,
        estado="PROGRAMADO",
        conciliado=False,
        creado_por_cuenta_id=auth.cuenta_id,
        observacion_adelantos=datos.observacion_adelantos,
    )
    session.add(pago)
    try:
        session.flush()
        for saldo in saldos:
            saldo.pago_id = pago.id
        for adelanto in adelantos:
            session.add(
                AplicacionAdelantoERP(
                    tenant_id=tenant_id,
                    pago_id=pago.id,
                    adelanto_id=adelanto.id,
                    usuario_id=datos.usuario_id,
                    monto=adelanto.monto,
                    creado_por_cuenta_id=auth.cuenta_id,
                )
            )
            adelanto.aplicado = True
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Liquidación o adelanto ya utilizado"
        ) from exc
    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_USUARIO_PROGRAMADO",
        "pago_erp",
        pago.id,
        {
            "usuario_id": str(datos.usuario_id),
            "produccion_periodo": str(produccion),
            "saldos_adicionados": [
                {"id": str(s.id), "mes": s.periodo_mes.isoformat(), "monto": str(s.monto)}
                for s in saldos
            ],
            "tasas_saldos_historicos": {
                str(s.id): str(datos.porcentajes_saldos[s.id]) for s in saldos
            },
            "adelantos_descontados": [{"id": str(a.id), "monto": str(a.monto)} for a in adelantos],
            "adelantos_omitidos": omitidos,
            "observacion_adelantos": datos.observacion_adelantos,
            "porcentaje": str(tasa),
            "bruto": str(bruto),
            "neto": str(neto),
            "actor": auth.codigo,
        },
    )
    session.commit()
    return {"id": str(pago.id), "saldo": str(neto)}


@router.post("/pagos/{pago_id}/confirmar")
def confirmar_pago_usuario(
    pago_id: uuid.UUID,
    datos: ConfirmarLiquidacionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    pago = session.get(PagoERP, pago_id)
    if pago is None or pago.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    _autorizar_pago(session, tenant_id, auth, pago.usuario_id)
    if pago.estado != "PROGRAMADO":
        raise HTTPException(status.HTTP_409_CONFLICT, "Liquidación ya pagada o anulada")
    pago.estado = "PAGADO"
    pago.fecha_pago = datos.fecha_pago
    pago.referencia_pago = datos.referencia_pago.strip()
    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_USUARIO_CONFIRMADO",
        "pago_erp",
        pago.id,
        {
            "fecha_pago": datos.fecha_pago.isoformat(),
            "referencia": datos.referencia_pago.strip(),
            "saldo": str(pago.saldo),
            "actor": auth.codigo,
        },
    )
    session.commit()
    return {"id": str(pago.id), "estado": pago.estado}


@router.delete("/pagos/{pago_id}", status_code=status.HTTP_204_NO_CONTENT)
def anular_pago_usuario(
    pago_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> None:
    pago = session.get(PagoERP, pago_id)
    if pago is None or pago.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    _autorizar_pago(session, tenant_id, auth, pago.usuario_id)
    if (
        pago.estado != "PROGRAMADO"
        or pago.conciliado
        or pago.fecha_pago is not None
        or pago.voucher_documento_id is not None
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Liquidación ya pagada")
    saldos = list(
        session.scalars(
            select(SaldoCompraERP)
            .where(
                SaldoCompraERP.tenant_id == tenant_id,
                SaldoCompraERP.pago_id == pago.id,
            )
            .with_for_update()
        )
    )
    aplicaciones = list(
        session.scalars(
            select(AplicacionAdelantoERP)
            .where(
                AplicacionAdelantoERP.tenant_id == tenant_id,
                AplicacionAdelantoERP.pago_id == pago.id,
            )
            .with_for_update()
        )
    )
    for s in saldos:
        s.pago_id = None
    for a in aplicaciones:
        adelanto = session.get(AdelantoERP, a.adelanto_id)
        if adelanto is not None and adelanto.tenant_id == tenant_id:
            adelanto.aplicado = False
        session.delete(a)
    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_USUARIO_PROGRAMACION_ANULADA",
        "pago_erp",
        pago.id,
        {
            "usuario_id": str(pago.usuario_id),
            "saldo": str(pago.saldo),
            "saldos_liberados": [str(s.id) for s in saldos],
            "adelantos_liberados": [str(a.adelanto_id) for a in aplicaciones],
            "actor": auth.codigo,
        },
    )
    session.delete(pago)
    session.commit()


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
    if pedido is None or pedido.tenant_id != tenant_id or pedido.responsable_id != auth.miembro_id:
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
        a
        for a in asignaciones
        if a.usuario_id == usuario.id and a.gestor_id is None and a.proveedor_id is None
    ]
    if any(a.usuario_id == usuario.id for a in asignaciones) and not existentes:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El usuario ya tiene asignaciones específicas"
        )
    nuevo_total = (
        sum(
            (Decimal(a.monto_asignado) for a in asignaciones if a not in existentes),
            Decimal("0"),
        )
        + datos.monto
    )
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
            "id": str(p.id),
            "usuario_id": str(p.usuario_id),
            "porcentaje": str(p.porcentaje),
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
