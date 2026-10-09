import calendar
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
    AbonoClienteERP,
    AdelantoERP,
    AsignacionPedidoGerencia,
    CuentaPagoERP,
    Empresa,
    Expediente,
    Gestor,
    Miembro,
    PagoERP,
    PedidoGerencia,
    PlanLiquidacion,
    Tenant,
)
from app.schemas import (
    AbonoClienteERPIn,
    AbonoClienteERPOut,
    AdelantoERPIn,
    AdelantoERPOut,
    AgenteRetencionIn,
    AsignacionPedidoGerenciaIn,
    AsignacionPedidoGerenciaOut,
    CarteraClienteFila,
    CarteraClientesResumen,
    CuentaPagoERPIn,
    CuentaPagoERPOut,
    FiltroOpcion,
    PagoERPActualizarIn,
    PagoERPOut,
    PagoERPProgramarIn,
    PedidoGerenciaActualizarIn,
    PedidoGerenciaIn,
    PedidoGerenciaOut,
    PlanLiquidacionIn,
    PlanLiquidacionOut,
)
from app.security import cuenta_administradora_responsable
from app.services import auditoria
from app.services.distribucion_jonatan import calcular_distribucion_jonatan

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


class SimulacionJonatanIn(BaseModel):
    total_emitido: Decimal = Field(ge=0)
    base_autorizada: Decimal | None = Field(default=None, gt=0)
    usar_total_emitido: bool = False


class SimulacionJonatanOut(BaseModel):
    base: Decimal
    bruto_referencial: Decimal
    neto_pagable: Decimal
    gente_lima: Decimal
    javier: Decimal
    jonatan: Decimal
    porcentaje_excluido_alex: Decimal
    modo_base: str


@router.post("/simular-jonatan", response_model=SimulacionJonatanOut)
def simular_jonatan(
    datos: SimulacionJonatanIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> SimulacionJonatanOut:
    # Regla privada de la Administración Luis Arévalo Herrera; no forma parte
    # del comportamiento SaaS estándar de otros tenants.
    if auth.rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permiso de simulación")
    tenant = session.get(Tenant, tenant_id)
    if tenant is None or tenant.codigo != "LAH-001-AD":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Regla especial no habilitada")
    try:
        resultado = calcular_distribucion_jonatan(
            total_emitido=datos.total_emitido,
            base_autorizada=datos.base_autorizada,
            usar_total_emitido=datos.usar_total_emitido,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return SimulacionJonatanOut(
        base=resultado.base,
        bruto_referencial=resultado.bruto,
        neto_pagable=resultado.neto,
        gente_lima=resultado.gente_lima,
        javier=resultado.javier,
        jonatan=resultado.jonatan,
        porcentaje_excluido_alex=resultado.excluido_alex,
        modo_base=resultado.modo_base,
    )


@router.get("/responsables", response_model=list[FiltroOpcion])
def responsables_pedido(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[FiltroOpcion]:
    _validar_acceso(auth.rol)
    return [
        FiltroOpcion(id=r.id, codigo=r.codigo, nombre=r.nombre)
        for r in session.scalars(
            select(Miembro).where(
                Miembro.tenant_id == tenant_id,
                Miembro.rol == RolMiembro.RESPONSABLE,
                Miembro.activo.is_(True),
                Miembro.deleted_at.is_(None),
            ).order_by(Miembro.codigo)
        )
    ]


@router.get("/usuarios", response_model=list[FiltroOpcion])
def usuarios_pago(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[FiltroOpcion]:
    _validar_acceso(auth.rol)
    return [
        FiltroOpcion(
            id=u.id,
            codigo=u.codigo,
            nombre=u.nombre,
            porcentaje_produccion=u.porcentaje_produccion,
        )
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


@router.get("/clientes", response_model=list[FiltroOpcion])
def clientes_pago(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[FiltroOpcion]:
    _validar_acceso(auth.rol)
    return [
        FiltroOpcion(id=e.id, codigo=e.ruc, nombre=e.razon_social)
        for e in session.scalars(
            select(Empresa)
            .where(
                Empresa.tenant_id == tenant_id,
                Empresa.deleted_at.is_(None),
                Empresa.tipo_relacion.in_(["CLIENTE", "AMBOS"]),
            )
            .order_by(Empresa.razon_social)
        )
    ]


@router.get("/proveedores", response_model=list[FiltroOpcion])
def proveedores_pago(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[FiltroOpcion]:
    _validar_acceso(auth.rol)
    return [
        FiltroOpcion(id=e.id, codigo=e.ruc, nombre=e.razon_social)
        for e in session.scalars(
            select(Empresa)
            .where(
                Empresa.tenant_id == tenant_id,
                Empresa.deleted_at.is_(None),
                Empresa.tipo_relacion.in_(["PROVEEDOR", "AMBOS"]),
            )
            .order_by(Empresa.razon_social)
        )
    ]


@router.get("/gestores", response_model=list[FiltroOpcion])
def gestores_pago(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[FiltroOpcion]:
    _validar_acceso(auth.rol)
    return [
        FiltroOpcion(
            id=g.id,
            codigo=g.codigo,
            nombre=g.nombre,
            usuario_id=g.usuario_id,
        )
        for g in session.scalars(
            select(Gestor)
            .where(
                Gestor.tenant_id == tenant_id,
                Gestor.deleted_at.is_(None),
            )
            .order_by(Gestor.codigo)
        )
    ]


def _rango_mes(mes: str) -> tuple[date, date]:
    try:
        anio_texto, mes_texto = mes.split("-", 1)
        anio = int(anio_texto)
        numero_mes = int(mes_texto)
        ultimo = calendar.monthrange(anio, numero_mes)[1]
        return date(anio, numero_mes, 1), date(anio, numero_mes, ultimo)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Mes inválido. Use formato AAAA-MM",
        ) from exc


def _cliente_valido(
    session: SessionDep,
    tenant_id: uuid.UUID,
    cliente_id: uuid.UUID,
) -> Empresa:
    cliente = session.get(Empresa, cliente_id)
    if (
        cliente is None
        or cliente.tenant_id != tenant_id
        or cliente.deleted_at is not None
        or cliente.tipo_relacion not in {"CLIENTE", "AMBOS"}
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La empresa seleccionada no es un Cliente activo",
        )
    return cliente


@router.get("/clientes/resumen", response_model=CarteraClientesResumen)
def resumen_clientes(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    mes: str,
    moneda: str = "PEN",
) -> CarteraClientesResumen:
    _validar_acceso(auth.rol)
    if moneda not in {"PEN", "USD"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Moneda inválida")
    desde, hasta = _rango_mes(mes)

    clientes = list(
        session.scalars(
            select(Empresa)
            .where(
                Empresa.tenant_id == tenant_id,
                Empresa.deleted_at.is_(None),
                Empresa.tipo_relacion.in_(["CLIENTE", "AMBOS"]),
            )
            .order_by(Empresa.razon_social)
        )
    )

    filas: list[CarteraClienteFila] = []
    total_compras = Decimal("0")
    total_anterior = Decimal("0")
    total_abonos = Decimal("0")
    total_saldo = Decimal("0")

    for cliente in clientes:
        compras_mes = Decimal(
            session.scalar(
                select(func.coalesce(func.sum(Expediente.importe_total), 0)).where(
                    Expediente.tenant_id == tenant_id,
                    Expediente.deleted_at.is_(None),
                    Expediente.receptor_id == cliente.id,
                    Expediente.moneda == moneda,
                    Expediente.fecha_emision >= desde,
                    Expediente.fecha_emision <= hasta,
                )
            )
            or 0
        )
        compras_previas = Decimal(
            session.scalar(
                select(func.coalesce(func.sum(Expediente.importe_total), 0)).where(
                    Expediente.tenant_id == tenant_id,
                    Expediente.deleted_at.is_(None),
                    Expediente.receptor_id == cliente.id,
                    Expediente.moneda == moneda,
                    Expediente.fecha_emision < desde,
                )
            )
            or 0
        )
        abonos_previos = Decimal(
            session.scalar(
                select(func.coalesce(func.sum(AbonoClienteERP.monto), 0)).where(
                    AbonoClienteERP.tenant_id == tenant_id,
                    AbonoClienteERP.cliente_id == cliente.id,
                    AbonoClienteERP.moneda == moneda,
                    AbonoClienteERP.fecha < desde,
                )
            )
            or 0
        )
        abonos_mes = Decimal(
            session.scalar(
                select(func.coalesce(func.sum(AbonoClienteERP.monto), 0)).where(
                    AbonoClienteERP.tenant_id == tenant_id,
                    AbonoClienteERP.cliente_id == cliente.id,
                    AbonoClienteERP.moneda == moneda,
                    AbonoClienteERP.fecha >= desde,
                    AbonoClienteERP.fecha <= hasta,
                )
            )
            or 0
        )

        saldo_anterior = compras_previas - abonos_previos
        saldo_total = saldo_anterior + compras_mes - abonos_mes
        if compras_mes == 0 and saldo_anterior == 0 and abonos_mes == 0:
            continue

        filas.append(
            CarteraClienteFila(
                cliente_id=cliente.id,
                ruc=cliente.ruc,
                razon_social=cliente.razon_social,
                agente_retencion=cliente.agente_retencion,
                moneda=moneda,
                compras_mes=compras_mes,
                saldo_anterior=saldo_anterior,
                abonos_mes=abonos_mes,
                saldo_total=saldo_total,
            )
        )
        total_compras += compras_mes
        total_anterior += saldo_anterior
        total_abonos += abonos_mes
        total_saldo += saldo_total

    return CarteraClientesResumen(
        mes=mes,
        moneda=moneda,
        filas=filas,
        total_compras_mes=total_compras,
        total_saldo_anterior=total_anterior,
        total_abonos_mes=total_abonos,
        total_saldo=total_saldo,
    )


@router.post(
    "/clientes/abonos",
    response_model=AbonoClienteERPOut,
    status_code=status.HTTP_201_CREATED,
)
def registrar_abono_cliente(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: AbonoClienteERPIn,
) -> AbonoClienteERP:
    _validar_acceso(auth.rol)
    cliente = _cliente_valido(session, tenant_id, datos.cliente_id)
    abono = AbonoClienteERP(
        tenant_id=tenant_id,
        cliente_id=cliente.id,
        fecha=datos.fecha,
        moneda=datos.moneda,
        monto=datos.monto,
        descripcion=datos.descripcion.strip() if datos.descripcion else None,
        referencia=datos.referencia.strip() if datos.referencia else None,
        creado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
    )
    session.add(abono)
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "ABONO_CLIENTE_REGISTRADO",
        "abono_cliente_erp",
        abono.id,
        {
            "cliente_id": str(cliente.id),
            "ruc": cliente.ruc,
            "moneda": datos.moneda,
            "monto": str(datos.monto),
            "fecha": datos.fecha.isoformat(),
        },
    )
    session.commit()
    return abono


@router.get("/clientes/abonos", response_model=list[AbonoClienteERPOut])
def listar_abonos_cliente(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    cliente_id: uuid.UUID | None = None,
) -> list[AbonoClienteERP]:
    _validar_acceso(auth.rol)
    consulta = select(AbonoClienteERP).where(AbonoClienteERP.tenant_id == tenant_id)
    if cliente_id is not None:
        consulta = consulta.where(AbonoClienteERP.cliente_id == cliente_id)
    return list(session.scalars(consulta.order_by(AbonoClienteERP.fecha.desc())))


@router.patch("/clientes/{cliente_id}/agente-retencion", response_model=bool)
def actualizar_agente_retencion(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    cliente_id: uuid.UUID,
    datos: AgenteRetencionIn,
) -> bool:
    _validar_acceso(auth.rol)
    cliente = _cliente_valido(session, tenant_id, cliente_id)
    anterior = cliente.agente_retencion
    cliente.agente_retencion = datos.agente_retencion
    auditoria.registrar(
        session,
        tenant_id,
        "CLIENTE_AGENTE_RETENCION_ACTUALIZADO",
        "empresa",
        cliente.id,
        {
            "ruc": cliente.ruc,
            "anterior": anterior,
            "nuevo": datos.agente_retencion,
            "actor": auth.codigo,
        },
    )
    session.commit()
    return cliente.agente_retencion


def _pedido_valido(
    session: SessionDep,
    tenant_id: uuid.UUID,
    pedido_id: uuid.UUID,
) -> PedidoGerencia:
    pedido = session.get(PedidoGerencia, pedido_id)
    if pedido is None or pedido.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido de Gerencia no encontrado")
    return pedido


def _generar_distribucion_usuario(
    session: SessionDep,
    tenant_id: uuid.UUID,
    auth: OperativeAuthDep,
    pedido: PedidoGerencia,
) -> None:
    usuarios = list(
        session.scalars(
            select(Miembro)
            .where(
                Miembro.tenant_id == tenant_id,
                Miembro.rol == RolMiembro.USUARIO,
                Miembro.activo.is_(True),
                Miembro.deleted_at.is_(None),
            )
            .order_by(Miembro.codigo)
        )
    )
    if not usuarios:
        return

    existentes = list(
        session.scalars(
            select(AsignacionPedidoGerencia).where(
                AsignacionPedidoGerencia.tenant_id == tenant_id,
                AsignacionPedidoGerencia.pedido_id == pedido.id,
            )
        )
    )
    for asignacion in existentes:
        session.delete(asignacion)

    total = Decimal(pedido.monto_solicitado).quantize(Decimal("0.01"))
    base = (total / Decimal(len(usuarios))).quantize(Decimal("0.01"))
    acumulado = Decimal("0")
    for indice, usuario in enumerate(usuarios):
        monto = total - acumulado if indice == len(usuarios) - 1 else base
        acumulado += monto
        session.add(
            AsignacionPedidoGerencia(
                tenant_id=tenant_id,
                pedido_id=pedido.id,
                usuario_id=usuario.id,
                gestor_id=None,
                proveedor_id=None,
                monto_asignado=monto,
                creado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
            )
        )


def _resumen_pedido(
    session: SessionDep,
    tenant_id: uuid.UUID,
    pedido: PedidoGerencia,
) -> PedidoGerenciaOut:
    cliente = session.get(Empresa, pedido.cliente_id)
    if cliente is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El Cliente del pedido ya no existe")

    desde, hasta = _rango_mes(pedido.periodo_mes.strftime("%Y-%m"))
    base_filtros = (
        Expediente.tenant_id == tenant_id,
        Expediente.deleted_at.is_(None),
        Expediente.receptor_id == pedido.cliente_id,
        Expediente.moneda == pedido.moneda,
        Expediente.fecha_emision >= desde,
        Expediente.fecha_emision <= hasta,
    )
    ejecutado = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(Expediente.importe_total), 0)).where(*base_filtros)
        )
        or 0
    )

    asignaciones_db = list(
        session.scalars(
            select(AsignacionPedidoGerencia)
            .where(
                AsignacionPedidoGerencia.tenant_id == tenant_id,
                AsignacionPedidoGerencia.pedido_id == pedido.id,
            )
            .order_by(AsignacionPedidoGerencia.created_at, AsignacionPedidoGerencia.id)
        )
    )
    asignaciones: list[AsignacionPedidoGerenciaOut] = []
    asignado = Decimal("0")
    for asignacion in asignaciones_db:
        usuario = session.get(Miembro, asignacion.usuario_id)
        gestor = session.get(Gestor, asignacion.gestor_id) if asignacion.gestor_id else None
        proveedor = (
            session.get(Empresa, asignacion.proveedor_id) if asignacion.proveedor_id else None
        )
        consulta = select(func.coalesce(func.sum(Expediente.importe_total), 0)).where(
            *base_filtros,
            Expediente.usuario_id == asignacion.usuario_id,
        )
        if asignacion.gestor_id is not None:
            consulta = consulta.where(Expediente.gestor_id == asignacion.gestor_id)
        if asignacion.proveedor_id is not None:
            consulta = consulta.where(Expediente.emisor_id == asignacion.proveedor_id)
        ejecutado_asignacion = Decimal(session.scalar(consulta) or 0)
        monto_asignado = Decimal(asignacion.monto_asignado)
        asignado += monto_asignado
        asignaciones.append(
            AsignacionPedidoGerenciaOut(
                id=asignacion.id,
                usuario_id=asignacion.usuario_id,
                usuario_codigo=usuario.codigo if usuario else "—",
                usuario_nombre=usuario.nombre if usuario else "Usuario no disponible",
                gestor_id=asignacion.gestor_id,
                gestor_codigo=gestor.codigo if gestor else None,
                gestor_nombre=gestor.nombre if gestor else None,
                proveedor_id=asignacion.proveedor_id,
                proveedor_ruc=proveedor.ruc if proveedor else None,
                proveedor_razon_social=proveedor.razon_social if proveedor else None,
                monto_asignado=monto_asignado,
                ejecutado=ejecutado_asignacion,
                saldo=monto_asignado - ejecutado_asignacion,
            )
        )

    concentraciones = list(
        session.execute(
            select(
                Expediente.emisor_id,
                func.coalesce(func.sum(Expediente.importe_total), 0),
            )
            .where(*base_filtros)
            .group_by(Expediente.emisor_id)
        )
    )
    proveedor_mayor = None
    concentracion = Decimal("0")
    if ejecutado > 0 and concentraciones:
        proveedor_id, mayor = max(concentraciones, key=lambda fila: Decimal(fila[1] or 0))
        mayor_decimal = Decimal(mayor or 0)
        concentracion = (mayor_decimal * Decimal("100") / ejecutado).quantize(Decimal("0.01"))
        proveedor_obj = session.get(Empresa, proveedor_id) if proveedor_id else None
        if proveedor_obj is not None:
            proveedor_mayor = f"{proveedor_obj.ruc} · {proveedor_obj.razon_social}"

    solicitado = Decimal(pedido.monto_solicitado)
    diferencia = solicitado - ejecutado
    pendiente = max(diferencia, Decimal("0"))
    exceso = max(-diferencia, Decimal("0"))
    avance = (
        (ejecutado * Decimal("100") / solicitado).quantize(Decimal("0.01"))
        if solicitado > 0
        else Decimal("0")
    )

    return PedidoGerenciaOut(
        id=pedido.id,
        responsable_id=pedido.responsable_id,
        cliente_id=pedido.cliente_id,
        cliente_ruc=cliente.ruc,
        cliente_razon_social=cliente.razon_social,
        periodo_mes=pedido.periodo_mes,
        moneda=pedido.moneda,
        monto_solicitado=solicitado,
        monto_asignado=asignado,
        monto_ejecutado=ejecutado,
        saldo_pendiente=pendiente,
        exceso=exceso,
        avance_porcentaje=avance,
        modalidad=pedido.modalidad,
        modo_distribucion=pedido.modo_distribucion,
        estado=pedido.estado,
        observacion=pedido.observacion,
        concentracion_maxima_proveedor=concentracion,
        proveedor_mayor_concentracion=proveedor_mayor,
        asignaciones=asignaciones,
    )


@router.post(
    "/pedidos",
    response_model=PedidoGerenciaOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_pedido_gerencia(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: PedidoGerenciaIn,
) -> PedidoGerenciaOut:
    _validar_acceso(auth.rol)
    cliente = _cliente_valido(session, tenant_id, datos.cliente_id)
    if datos.responsable_id is not None:
        responsable = session.get(Miembro, datos.responsable_id)
        if (
            responsable is None
            or responsable.tenant_id != tenant_id
            or responsable.rol != RolMiembro.RESPONSABLE
            or not responsable.activo
            or responsable.deleted_at is not None
        ):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Responsable inválido")
        if datos.modo_distribucion != "MANUAL":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El Responsable distribuye el pedido manualmente")
    periodo = datos.periodo_mes.replace(day=1)
    pedido = PedidoGerencia(
        tenant_id=tenant_id,
        cliente_id=cliente.id,
        responsable_id=datos.responsable_id,
        periodo_mes=periodo,
        moneda=datos.moneda,
        monto_solicitado=datos.monto_solicitado,
        modalidad=datos.modalidad,
        modo_distribucion=datos.modo_distribucion,
        estado="ACTIVO",
        observacion=datos.observacion.strip() if datos.observacion else None,
        creado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
    )
    session.add(pedido)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe un Pedido de Gerencia para ese Cliente, mes y moneda",
        ) from exc

    if pedido.responsable_id is None and pedido.modo_distribucion in {"SEMIASISTIDA", "AUTOMATICA"}:
        _generar_distribucion_usuario(session, tenant_id, auth, pedido)

    auditoria.registrar(
        session,
        tenant_id,
        "PEDIDO_GERENCIA_CREADO",
        "pedido_gerencia",
        pedido.id,
        {
            "cliente_id": str(cliente.id),
            "ruc": cliente.ruc,
            "periodo": periodo.isoformat(),
            "moneda": pedido.moneda,
            "monto_solicitado": str(pedido.monto_solicitado),
            "modalidad": pedido.modalidad,
            "modo_distribucion": pedido.modo_distribucion,
        },
    )
    session.commit()
    return _resumen_pedido(session, tenant_id, pedido)


@router.get("/pedidos", response_model=list[PedidoGerenciaOut])
def listar_pedidos_gerencia(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    mes: str | None = None,
    moneda: str | None = None,
) -> list[PedidoGerenciaOut]:
    _validar_acceso(auth.rol)
    consulta = select(PedidoGerencia).where(PedidoGerencia.tenant_id == tenant_id)
    if mes:
        desde, _ = _rango_mes(mes)
        consulta = consulta.where(PedidoGerencia.periodo_mes == desde)
    if moneda:
        if moneda not in {"PEN", "USD"}:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Moneda inválida")
        consulta = consulta.where(PedidoGerencia.moneda == moneda)
    pedidos = list(
        session.scalars(
            consulta.order_by(PedidoGerencia.periodo_mes.desc(), PedidoGerencia.created_at.desc())
        )
    )
    return [_resumen_pedido(session, tenant_id, pedido) for pedido in pedidos]


@router.patch("/pedidos/{pedido_id}", response_model=PedidoGerenciaOut)
def actualizar_pedido_gerencia(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    pedido_id: uuid.UUID,
    datos: PedidoGerenciaActualizarIn,
) -> PedidoGerenciaOut:
    _validar_acceso(auth.rol)
    pedido = _pedido_valido(session, tenant_id, pedido_id)
    if "responsable_id" in datos.model_fields_set:
        nuevo = session.get(Miembro, datos.responsable_id) if datos.responsable_id else None
        if datos.responsable_id is not None and (
            nuevo is None or nuevo.tenant_id != tenant_id
            or nuevo.rol != RolMiembro.RESPONSABLE or not nuevo.activo
            or nuevo.deleted_at is not None
        ):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Responsable inválido")
        if pedido.responsable_id != datos.responsable_id:
            tiene_asignaciones = session.scalar(select(AsignacionPedidoGerencia.id).where(
                AsignacionPedidoGerencia.tenant_id == tenant_id,
                AsignacionPedidoGerencia.pedido_id == pedido.id,
            ))
            if tiene_asignaciones is not None:
                raise HTTPException(status.HTTP_409_CONFLICT, "Quite asignaciones anteriores antes de transferir")
        pedido.responsable_id = datos.responsable_id
    if pedido.responsable_id is not None and datos.modo_distribucion in {"SEMIASISTIDA", "AUTOMATICA"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Distribución reservada al Responsable")
    anterior = {
        "monto_solicitado": str(pedido.monto_solicitado),
        "modalidad": pedido.modalidad,
        "modo_distribucion": pedido.modo_distribucion,
        "estado": pedido.estado,
        "observacion": pedido.observacion,
    }
    if datos.monto_solicitado is not None:
        pedido.monto_solicitado = datos.monto_solicitado
    if datos.modalidad is not None:
        pedido.modalidad = datos.modalidad
    if datos.modo_distribucion is not None:
        pedido.modo_distribucion = datos.modo_distribucion
    if datos.estado is not None:
        pedido.estado = datos.estado
    if "observacion" in datos.model_fields_set:
        pedido.observacion = datos.observacion.strip() if datos.observacion else None

    if pedido.responsable_id is None and (
        datos.modo_distribucion in {"SEMIASISTIDA", "AUTOMATICA"} or (
            datos.monto_solicitado is not None
            and pedido.modo_distribucion in {"SEMIASISTIDA", "AUTOMATICA"}
        )
    ):
        _generar_distribucion_usuario(session, tenant_id, auth, pedido)

    auditoria.registrar(
        session,
        tenant_id,
        "PEDIDO_GERENCIA_ACTUALIZADO",
        "pedido_gerencia",
        pedido.id,
        {
            "anterior": anterior,
            "nuevo": datos.model_dump(exclude_unset=True),
            "actor": auth.codigo,
        },
    )
    session.commit()
    return _resumen_pedido(session, tenant_id, pedido)


@router.post(
    "/pedidos/{pedido_id}/asignaciones",
    response_model=PedidoGerenciaOut,
)
def agregar_asignacion_pedido(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    pedido_id: uuid.UUID,
    datos: AsignacionPedidoGerenciaIn,
) -> PedidoGerenciaOut:
    _validar_acceso(auth.rol)
    pedido = _pedido_valido(session, tenant_id, pedido_id)
    if pedido.responsable_id is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El pedido corresponde al Responsable asignado")
    usuario = _usuario_valido(session, tenant_id, datos.usuario_id)

    gestor = None
    if datos.gestor_id is not None:
        gestor = session.get(Gestor, datos.gestor_id)
        if (
            gestor is None
            or gestor.tenant_id != tenant_id
            or gestor.deleted_at is not None
            or gestor.usuario_id != usuario.id
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "El Gestor no pertenece al Usuario seleccionado",
            )

    proveedor = None
    if datos.proveedor_id is not None:
        proveedor = session.get(Empresa, datos.proveedor_id)
        if (
            proveedor is None
            or proveedor.tenant_id != tenant_id
            or proveedor.deleted_at is not None
            or proveedor.tipo_relacion not in {"PROVEEDOR", "AMBOS"}
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "La empresa seleccionada no es un Proveedor activo",
            )

    duplicada = session.scalar(
        select(AsignacionPedidoGerencia).where(
            AsignacionPedidoGerencia.tenant_id == tenant_id,
            AsignacionPedidoGerencia.pedido_id == pedido.id,
            AsignacionPedidoGerencia.usuario_id == usuario.id,
            AsignacionPedidoGerencia.gestor_id == datos.gestor_id,
            AsignacionPedidoGerencia.proveedor_id == datos.proveedor_id,
        )
    )
    if duplicada is not None:
        duplicada.monto_asignado = datos.monto_asignado
        asignacion = duplicada
    else:
        asignacion = AsignacionPedidoGerencia(
            tenant_id=tenant_id,
            pedido_id=pedido.id,
            usuario_id=usuario.id,
            gestor_id=gestor.id if gestor else None,
            proveedor_id=proveedor.id if proveedor else None,
            monto_asignado=datos.monto_asignado,
            creado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
        )
        session.add(asignacion)

    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "PEDIDO_GERENCIA_ASIGNACION",
        "asignacion_pedido_gerencia",
        asignacion.id,
        {
            "pedido_id": str(pedido.id),
            "usuario_id": str(usuario.id),
            "gestor_id": str(gestor.id) if gestor else None,
            "proveedor_id": str(proveedor.id) if proveedor else None,
            "monto": str(datos.monto_asignado),
        },
    )
    session.commit()
    return _resumen_pedido(session, tenant_id, pedido)


@router.delete(
    "/pedidos/{pedido_id}/asignaciones/{asignacion_id}",
    response_model=PedidoGerenciaOut,
)
def eliminar_asignacion_pedido(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    pedido_id: uuid.UUID,
    asignacion_id: uuid.UUID,
) -> PedidoGerenciaOut:
    _validar_acceso(auth.rol)
    pedido = _pedido_valido(session, tenant_id, pedido_id)
    asignacion = session.get(AsignacionPedidoGerencia, asignacion_id)
    if asignacion is None or asignacion.tenant_id != tenant_id or asignacion.pedido_id != pedido.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asignación no encontrada")
    session.delete(asignacion)
    auditoria.registrar(
        session,
        tenant_id,
        "PEDIDO_GERENCIA_ASIGNACION_ELIMINADA",
        "asignacion_pedido_gerencia",
        asignacion.id,
        {"pedido_id": str(pedido.id), "actor": auth.codigo},
    )
    session.commit()
    return _resumen_pedido(session, tenant_id, pedido)


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
        creado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
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
        creado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
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
        creado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
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
        creado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
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
