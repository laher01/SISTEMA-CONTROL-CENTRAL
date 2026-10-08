import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import (
    AdelantoERP,
    CuentaPagoERP,
    Expediente,
    Miembro,
    PagoERP,
    PlanLiquidacion,
)
from app.schemas import (
    AdelantoERPIn,
    AdelantoERPOut,
    CuentaPagoERPIn,
    CuentaPagoERPOut,
    FiltroOpcion,
    PagoERPActualizarIn,
    PagoERPOut,
    PagoERPProgramarIn,
    PlanLiquidacionIn,
    PlanLiquidacionOut,
)
from app.services import auditoria

router = APIRouter(prefix="/pagos", tags=["pagos"])


def _validar_acceso(rol: str) -> None:
    if rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR, RolMiembro.GERENTE):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Pagos ERP está disponible solo para Administración y Gerencia",
        )


def _usuario_valido(
    session: SessionDep,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> Miembro:
    usuario = session.get(Miembro, usuario_id)
    if (
        usuario is None
        or usuario.tenant_id != tenant_id
        or usuario.deleted_at is not None
        or usuario.rol != RolMiembro.USUARIO
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Usuario inválido")
    return usuario


@router.get("/usuarios", response_model=list[FiltroOpcion])
def usuarios_pago(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[FiltroOpcion]:
    _validar_acceso(auth.rol)
    return [
        FiltroOpcion(id=u.id, codigo=u.codigo, nombre=u.nombre)
        for u in session.scalars(
            select(Miembro)
            .where(
                Miembro.tenant_id == tenant_id,
                Miembro.rol == RolMiembro.USUARIO,
                Miembro.activo.is_(True),
                Miembro.deleted_at.is_(None),
            )
            .order_by(Miembro.codigo)
        )
    ]


@router.post("/planes", response_model=PlanLiquidacionOut, status_code=status.HTTP_201_CREATED)
def crear_plan(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: PlanLiquidacionIn,
) -> PlanLiquidacion:
    _validar_acceso(auth.rol)
    _usuario_valido(session, tenant_id, datos.usuario_id)
    plan = PlanLiquidacion(
        tenant_id=tenant_id,
        usuario_id=datos.usuario_id,
        nombre=datos.nombre.strip(),
        porcentaje=datos.porcentaje,
        vigencia_desde=datos.vigencia_desde,
        vigencia_hasta=datos.vigencia_hasta,
        activo=True,
    )
    session.add(plan)
    session.commit()
    return plan


@router.get("/planes", response_model=list[PlanLiquidacionOut])
def listar_planes(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[PlanLiquidacion]:
    _validar_acceso(auth.rol)
    return list(
        session.scalars(
            select(PlanLiquidacion)
            .where(PlanLiquidacion.tenant_id == tenant_id)
            .order_by(PlanLiquidacion.vigencia_desde.desc())
        )
    )


@router.post("/cuentas", response_model=CuentaPagoERPOut, status_code=status.HTTP_201_CREATED)
def crear_cuenta(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: CuentaPagoERPIn,
) -> CuentaPagoERP:
    _validar_acceso(auth.rol)
    _usuario_valido(session, tenant_id, datos.usuario_id)
    cuenta = CuentaPagoERP(
        tenant_id=tenant_id,
        usuario_id=datos.usuario_id,
        titular=datos.titular.strip(),
        banco=datos.banco.strip(),
        tipo_cuenta=datos.tipo_cuenta.strip(),
        moneda=datos.moneda,
        numero_cuenta=datos.numero_cuenta,
        cci=datos.cci,
        porcentaje_distribucion=datos.porcentaje_distribucion,
        activa=True,
    )
    session.add(cuenta)
    session.commit()
    return cuenta


@router.get("/cuentas", response_model=list[CuentaPagoERPOut])
def listar_cuentas(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[CuentaPagoERP]:
    _validar_acceso(auth.rol)
    return list(
        session.scalars(
            select(CuentaPagoERP)
            .where(CuentaPagoERP.tenant_id == tenant_id)
            .order_by(CuentaPagoERP.created_at.desc())
        )
    )


@router.post("/adelantos", response_model=AdelantoERPOut, status_code=status.HTTP_201_CREATED)
def crear_adelanto(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: AdelantoERPIn,
) -> AdelantoERP:
    _validar_acceso(auth.rol)
    _usuario_valido(session, tenant_id, datos.usuario_id)
    adelanto = AdelantoERP(
        tenant_id=tenant_id,
        usuario_id=datos.usuario_id,
        fecha=datos.fecha,
        moneda=datos.moneda,
        monto=datos.monto,
        descripcion=datos.descripcion,
        aplicado=False,
    )
    session.add(adelanto)
    session.commit()
    return adelanto


@router.get("/adelantos", response_model=list[AdelantoERPOut])
def listar_adelantos(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[AdelantoERP]:
    _validar_acceso(auth.rol)
    return list(
        session.scalars(
            select(AdelantoERP)
            .where(AdelantoERP.tenant_id == tenant_id)
            .order_by(AdelantoERP.fecha.desc())
        )
    )


@router.post("", response_model=PagoERPOut, status_code=status.HTTP_201_CREATED)
def programar_pago(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: PagoERPProgramarIn,
) -> PagoERP:
    _validar_acceso(auth.rol)
    _usuario_valido(session, tenant_id, datos.usuario_id)
    if datos.periodo_hasta < datos.periodo_desde:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El periodo final no puede ser anterior al inicial",
        )

    existente = session.scalar(
        select(PagoERP).where(
            PagoERP.tenant_id == tenant_id,
            PagoERP.usuario_id == datos.usuario_id,
            PagoERP.periodo_desde == datos.periodo_desde,
            PagoERP.periodo_hasta == datos.periodo_hasta,
            PagoERP.moneda == datos.moneda,
        )
    )
    if existente is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un pago para ese periodo")

    plan = session.scalar(
        select(PlanLiquidacion)
        .where(
            PlanLiquidacion.tenant_id == tenant_id,
            PlanLiquidacion.usuario_id == datos.usuario_id,
            PlanLiquidacion.activo.is_(True),
            PlanLiquidacion.vigencia_desde <= datos.periodo_hasta,
            (
                (PlanLiquidacion.vigencia_hasta.is_(None))
                | (PlanLiquidacion.vigencia_hasta >= datos.periodo_desde)
            ),
        )
        .order_by(PlanLiquidacion.vigencia_desde.desc())
        .limit(1)
    )
    if plan is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El Usuario no tiene un Plan de Liquidación vigente",
        )

    produccion = session.scalar(
        select(func.coalesce(func.sum(Expediente.importe_total), 0)).where(
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
            Expediente.usuario_id == datos.usuario_id,
            Expediente.moneda == datos.moneda,
            Expediente.fecha_emision >= datos.periodo_desde,
            Expediente.fecha_emision <= datos.periodo_hasta,
        )
    )
    produccion_total = Decimal(produccion or 0)
    bruto = (produccion_total * Decimal(plan.porcentaje) / Decimal("100")).quantize(Decimal("0.01"))

    adelantos = list(
        session.scalars(
            select(AdelantoERP).where(
                AdelantoERP.tenant_id == tenant_id,
                AdelantoERP.usuario_id == datos.usuario_id,
                AdelantoERP.moneda == datos.moneda,
                AdelantoERP.fecha <= datos.periodo_hasta,
                AdelantoERP.aplicado.is_(False),
            )
        )
    )
    total_adelantos = sum((Decimal(a.monto) for a in adelantos), Decimal("0"))
    saldo = bruto - total_adelantos + Decimal(datos.ajustes)

    pago = PagoERP(
        tenant_id=tenant_id,
        usuario_id=datos.usuario_id,
        plan_id=plan.id,
        periodo_desde=datos.periodo_desde,
        periodo_hasta=datos.periodo_hasta,
        moneda=datos.moneda,
        produccion_total=produccion_total,
        porcentaje=plan.porcentaje,
        bruto=bruto,
        adelantos=total_adelantos,
        ajustes=datos.ajustes,
        saldo=saldo,
        estado="PROGRAMADO",
        fecha_programada=datos.fecha_programada,
        conciliado=False,
    )
    session.add(pago)
    for adelanto in adelantos:
        adelanto.aplicado = True
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_ERP_PROGRAMADO",
        "pago_erp",
        pago.id,
        {
            "usuario_id": str(datos.usuario_id),
            "produccion_total": str(produccion_total),
            "saldo": str(saldo),
        },
    )
    session.commit()
    return pago


@router.get("", response_model=list[PagoERPOut])
def listar_pagos(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[PagoERP]:
    _validar_acceso(auth.rol)
    return list(
        session.scalars(
            select(PagoERP)
            .where(PagoERP.tenant_id == tenant_id)
            .order_by(PagoERP.created_at.desc())
        )
    )


@router.patch("/{pago_id}", response_model=PagoERPOut)
def actualizar_pago(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    pago_id: uuid.UUID,
    datos: PagoERPActualizarIn,
) -> PagoERP:
    _validar_acceso(auth.rol)
    pago = session.get(PagoERP, pago_id)
    if pago is None or pago.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")

    if datos.estado is not None:
        estado = datos.estado.upper()
        permitidos = {"PROGRAMADO", "APROBADO", "PAGADO", "CONCILIADO"}
        if estado not in permitidos:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Estado inválido")
        if estado in {"PAGADO", "CONCILIADO"} and auth.rol != RolMiembro.GERENTE:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Solo Gerencia puede confirmar pago o conciliación",
            )
        pago.estado = estado
    if datos.fecha_pago is not None:
        pago.fecha_pago = datos.fecha_pago
    if datos.voucher_documento_id is not None:
        pago.voucher_documento_id = datos.voucher_documento_id
    if datos.conciliado is not None:
        if datos.conciliado and auth.rol != RolMiembro.GERENTE:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Solo Gerencia puede conciliar pagos",
            )
        pago.conciliado = datos.conciliado
        if datos.conciliado:
            pago.estado = "CONCILIADO"

    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_ERP_ACTUALIZADO",
        "pago_erp",
        pago.id,
        {"estado": pago.estado, "conciliado": pago.conciliado},
    )
    session.commit()
    return pago


@router.delete("/{pago_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_programacion(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    pago_id: uuid.UUID,
) -> None:
    if auth.rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo SUPERADMIN o Administración pueden eliminar programaciones",
        )

    pago = session.get(PagoERP, pago_id)
    if pago is None or pago.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")

    if pago.estado in {"PAGADO", "CONCILIADO"} or pago.conciliado:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede eliminar una programación pagada o conciliada",
        )

    if Decimal(pago.adelantos) != Decimal("0"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede eliminar automáticamente una programación que ya aplicó adelantos",
        )

    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_ERP_PROGRAMACION_ELIMINADA",
        "pago_erp",
        pago.id,
        {
            "usuario_id": str(pago.usuario_id),
            "periodo_desde": pago.periodo_desde.isoformat(),
            "periodo_hasta": pago.periodo_hasta.isoformat(),
            "moneda": str(pago.moneda),
            "produccion_total": str(pago.produccion_total),
            "saldo": str(pago.saldo),
            "estado": pago.estado,
        },
    )
    session.delete(pago)
    session.commit()
