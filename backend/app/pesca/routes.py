import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import AlmacenDep, HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.models import CuentaAcceso, Gestor, Miembro
from app.pesca.models import (
    AbonoMovimientoPesca,
    ActividadCuadrillaPesca,
    AsignacionCuadrillaPesca,
    AsignacionRolPesca,
    AuditoriaRolPesca,
    CargaEmbarcacionVehiculo,
    DescargaEmbarcacion,
    DocumentoPesca,
    EmbarcacionPesca,
    HistorialPesca,
    OperacionPesca,
    MovimientoPesca,
    RegistroPlanta,
    VehiculoPesca,
    VinculoDocumentoEmbarcacion,
    VinculoDocumentoVehiculo,
)
from app.pesca.schemas import (
    AbonoMovimientoOut,
    ActividadCuadrillaIn,
    ActividadCuadrillaOut,
    AsignacionCuadrillaIn,
    AsignacionCuadrillaOut,
    CargaIn,
    CierreOut,
    ConfirmarPrecioIn,
    ConfirmarAcuerdoEmbarcacionIn,
    CuentaResponsablePesaje,
    SolicitarAjustePrecioIn,
    PagoCuadrillaIn,
    ResponsablePesajeMuelleIn,
    CuentaPescaCandidata,
    DescargaOut,
    DocumentoOut,
    EmbarcacionIn,
    OperacionIn,
    OperacionOut,
    MovimientoIn,
    MovimientoOut,
    RegistrarFacturaIn,
    RevisionDocumentoIn,
    RolPescaAsignacionIn,
    RolPescaAsignacionOut,
    RolesPescaActuales,
    RegistroPlantaIn,
    RegistroPlantaOut,
    TiemposDescargaIn,
    TiemposPlantaIn,
    VehiculoIn,
    VehiculoOut,
)
from app.storage import AlmacenLocal

router = APIRouter(prefix="/pesca", tags=["operaciones de pesca"])
ROLES_PESCA = (
    "JEFE_BAHIA", "GERENTE", "ENCARGADO_MUELLE", "ARMADOR", "PATRON",
    "APUNTADOR_MUELLE", "APUNTADOR_PLANTA", "JEFE_CUADRILLA",
    "SECRETARIA", "TRAMITADORA", "TRANSPORTISTA",
)
ROLES_CONTROL_OPERACION = ("JEFE_BAHIA", "ENCARGADO_MUELLE")
ROLES_CONTROL_PLANTA = ("APUNTADOR_PLANTA",)
ROLES_CAPTURA_PLANTA = ("APUNTADOR_PLANTA",)
ROLES_DOCUMENTACION = (
    "JEFE_BAHIA", "ENCARGADO_MUELLE", "ARMADOR", "PATRON", "APUNTADOR_MUELLE",
    "APUNTADOR_PLANTA", "SECRETARIA", "TRAMITADORA",
)
ROL_POR_ACTIVIDAD = {
}
TIPOS_DOCUMENTO = {
    "certificado_matricula",
    "permiso_pesca",
    "certificado_sanipes",
    "reporte_satelital",
    "visto_bueno_produce",
    "guia_remitente",
    "guia_transportista",
    "acta_fiscalizacion",
    "formato_descarga",
    "certificado_procedencia",
    "certificado_captura",
    "factura",
    "boleta",
    "recibo_honorarios",
    "voucher_pago",
    "comprobante_gasto",
    "peso_planta",
    "otro",
}
ETAPAS_DOCUMENTO = {"EMBARCACION", "MUELLE", "TRANSPORTE", "PLANTA", "TRAMITADORA", "FACTURACION", "GENERAL"}
ETAPA_POR_TIPO = {
    "certificado_matricula": "EMBARCACION",
    "permiso_pesca": "EMBARCACION",
    "certificado_sanipes": "EMBARCACION",
    "reporte_satelital": "EMBARCACION",
    "visto_bueno_produce": "EMBARCACION",
    "acta_fiscalizacion": "MUELLE",
    "formato_descarga": "MUELLE",
    "guia_remitente": "TRANSPORTE",
    "guia_transportista": "TRANSPORTE",
    "peso_planta": "PLANTA",
    "certificado_procedencia": "TRAMITADORA",
    "factura": "FACTURACION",
    "boleta": "FACTURACION",
    "recibo_honorarios": "FACTURACION",
}
MIME_PERMITIDOS = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
FACTOR_KG = {
    "kg": Decimal("1"),
    "ton": Decimal("1000"),
    "lb": Decimal("0.45359237"),
    "oz": Decimal("0.028349523125"),
}


def obtener_actor(auth: OperativeAuthDep) -> str:
    """La auditoría usa la identidad validada por la sesión de la plataforma."""
    return auth.codigo[:200]


ActorDep = Annotated[str, Depends(obtener_actor)]


def _requiere_rol_pesca(*roles: str):
    def verificar(session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep) -> None:
        if auth.rol in {"ADMINISTRADOR", "SUPERADMIN"} and {"JEFE_BAHIA", "GERENTE"}.intersection(roles):
            raise HTTPException(403, "La decisión y consulta de precios corresponde al Jefe de Bahía o al Gerente")
        asignacion = session.scalar(
            select(AsignacionRolPesca.id).where(
                AsignacionRolPesca.tenant_id == tenant_id,
                AsignacionRolPesca.cuenta_id == auth.cuenta_id,
                AsignacionRolPesca.rol.in_(roles),
                AsignacionRolPesca.activa.is_(True),
            )
        )
        if asignacion is None:
            raise HTTPException(403, "La cuenta no tiene el rol pesquero requerido para esta acción")

    return Depends(verificar)


def _etiqueta_cuenta_pesca(session: Session, cuenta: CuentaAcceso) -> tuple[str, str]:
    if cuenta.miembro_id is not None:
        miembro = session.get(Miembro, cuenta.miembro_id)
        if miembro is not None:
            return miembro.codigo, miembro.nombre
    if cuenta.gestor_id is not None:
        gestor = session.get(Gestor, cuenta.gestor_id)
        if gestor is not None:
            return gestor.codigo, gestor.nombre
    return cuenta.login, cuenta.login


def _validar_administrador_tenant(auth: OperativeAuthDep) -> None:
    if auth.rol != "ADMINISTRADOR":
        raise HTTPException(403, "Solo el Administrador general del tenant puede asignar roles pesqueros")


def _puede_ver_precios(session: Session, tenant_id: uuid.UUID, cuenta_id: uuid.UUID) -> bool:
    cuenta = session.get(CuentaAcceso, cuenta_id)
    miembro = session.get(Miembro, cuenta.miembro_id) if cuenta and cuenta.miembro_id else None
    if miembro is not None and miembro.rol in {"ADMINISTRADOR", "SUPERADMIN"}:
        return False
    return session.scalar(
        select(AsignacionRolPesca.id).where(
            AsignacionRolPesca.tenant_id == tenant_id,
            AsignacionRolPesca.cuenta_id == cuenta_id,
            AsignacionRolPesca.rol.in_(("JEFE_BAHIA", "GERENTE")),
            AsignacionRolPesca.activa.is_(True),
        )
    ) is not None


def _operacion_para_actor(op: OperacionPesca, puede_ver_precios: bool) -> OperacionPesca | OperacionOut:
    if puede_ver_precios:
        return op
    return OperacionOut.model_validate(op).model_copy(
        update={
            "precio_propuesto": None,
            "precio_confirmado": None,
            "precio_confirmado_por": None,
            "precio_confirmado_at": None,
        }
    )


def _exigir_embarcacion_reportante(op: OperacionPesca, actor: str) -> None:
    if op.responsable_id.casefold().strip() != actor.casefold().strip():
        raise HTTPException(403, "Solo la cuenta que reportó esta embarcación puede confirmar o solicitar cambios de su precio")


@router.get("/roles/mios", response_model=RolesPescaActuales)
def roles_pesca_actuales(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> RolesPescaActuales:
    roles = list(
        session.scalars(
            select(AsignacionRolPesca.rol).where(
                AsignacionRolPesca.tenant_id == tenant_id,
                AsignacionRolPesca.cuenta_id == auth.cuenta_id,
                AsignacionRolPesca.activa.is_(True),
            )
        )
    )
    return RolesPescaActuales(cuenta_id=auth.cuenta_id, roles=roles)


@router.get("/roles/candidatos", response_model=list[CuentaPescaCandidata])
def listar_candidatos_rol_pesca(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[CuentaPescaCandidata]:
    _validar_administrador_tenant(auth)
    cuentas: dict[uuid.UUID, CuentaPescaCandidata] = {}
    activas = session.scalars(
        select(CuentaAcceso).where(
            CuentaAcceso.tenant_id == tenant_id,
            CuentaAcceso.activo.is_(True),
            CuentaAcceso.deleted_at.is_(None),
        )
    )
    for cuenta in activas:
        miembro = session.get(Miembro, cuenta.miembro_id) if cuenta.miembro_id else None
        if miembro is not None and miembro.rol in {"ADMINISTRADOR", "SUPERADMIN"}:
            continue
        codigo, nombre = _etiqueta_cuenta_pesca(session, cuenta)
        cuentas[cuenta.id] = CuentaPescaCandidata(cuenta_id=cuenta.id, codigo=codigo, nombre=nombre)
    return sorted(cuentas.values(), key=lambda item: (item.nombre.casefold(), item.codigo.casefold()))


@router.get("/roles/asignaciones", response_model=list[RolPescaAsignacionOut])
def listar_asignaciones_rol_pesca(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[RolPescaAsignacionOut]:
    _validar_administrador_tenant(auth)
    rows = session.scalars(
        select(AsignacionRolPesca)
        .where(AsignacionRolPesca.tenant_id == tenant_id)
        .order_by(AsignacionRolPesca.rol, AsignacionRolPesca.created_at)
    )
    salida = []
    for row in rows:
        cuenta = session.get(CuentaAcceso, row.cuenta_id)
        if cuenta is None:
            continue
        codigo, nombre = _etiqueta_cuenta_pesca(session, cuenta)
        salida.append(
            RolPescaAsignacionOut(
                id=row.id,
                cuenta_id=row.cuenta_id,
                rol=row.rol,
                activa=row.activa,
                codigo=codigo,
                nombre=nombre,
            )
        )
    return salida


@router.put("/roles/asignaciones", response_model=RolPescaAsignacionOut)
def guardar_asignacion_rol_pesca(
    datos: RolPescaAsignacionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> RolPescaAsignacionOut:
    _validar_administrador_tenant(auth)
    cuenta = session.scalar(
        select(CuentaAcceso).where(
            CuentaAcceso.id == datos.cuenta_id,
            CuentaAcceso.tenant_id == tenant_id,
            CuentaAcceso.activo.is_(True),
            CuentaAcceso.deleted_at.is_(None),
        )
    )
    if cuenta is None:
        raise HTTPException(404, "La cuenta no existe en este tenant o está inactiva")
    miembro = session.get(Miembro, cuenta.miembro_id) if cuenta.miembro_id else None
    if miembro is not None and miembro.rol in {"ADMINISTRADOR", "SUPERADMIN"}:
        raise HTTPException(422, "La cuenta Administrador de plataforma/tenant no puede recibir actores operativos de pesca")
    asignacion = session.scalar(
        select(AsignacionRolPesca).where(
            AsignacionRolPesca.tenant_id == tenant_id,
            AsignacionRolPesca.cuenta_id == cuenta.id,
            AsignacionRolPesca.rol == datos.rol,
        )
    )
    accion = "activada" if datos.activa else "desactivada"
    if asignacion is None:
        asignacion = AsignacionRolPesca(
            tenant_id=tenant_id,
            cuenta_id=cuenta.id,
            rol=datos.rol,
            activa=datos.activa,
            asignado_por_cuenta_id=auth.cuenta_id,
        )
        session.add(asignacion)
        accion = "asignada" if datos.activa else "desactivada"
    else:
        asignacion.activa = datos.activa
        asignacion.asignado_por_cuenta_id = auth.cuenta_id
        asignacion.updated_at = datetime.now(UTC)
    session.add(
        AuditoriaRolPesca(
            tenant_id=tenant_id,
            actor_cuenta_id=auth.cuenta_id,
            cuenta_objetivo_id=cuenta.id,
            rol=datos.rol,
            accion=accion,
        )
    )
    session.commit()
    session.refresh(asignacion)
    codigo, nombre = _etiqueta_cuenta_pesca(session, cuenta)
    return RolPescaAsignacionOut(
        id=asignacion.id,
        cuenta_id=asignacion.cuenta_id,
        rol=asignacion.rol,
        activa=asignacion.activa,
        codigo=codigo,
        nombre=nombre,
    )


@router.get("/operaciones/{op_id}/cuadrilla", response_model=list[AsignacionCuadrillaOut], dependencies=[_requiere_rol_pesca("JEFE_CUADRILLA")])
def listar_asignaciones_cuadrilla(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> list[AsignacionCuadrillaOut]:
    _operacion(session, tenant_id, op_id)
    filas = session.scalars(
        select(AsignacionCuadrillaPesca)
        .where(AsignacionCuadrillaPesca.tenant_id == tenant_id, AsignacionCuadrillaPesca.operacion_id == op_id)
        .order_by(AsignacionCuadrillaPesca.actividad, AsignacionCuadrillaPesca.created_at)
    )
    return list(filas)


@router.put("/operaciones/{op_id}/cuadrilla", response_model=AsignacionCuadrillaOut, dependencies=[_requiere_rol_pesca("JEFE_CUADRILLA")])
def guardar_asignacion_cuadrilla(
    op_id: uuid.UUID,
    datos: AsignacionCuadrillaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> AsignacionCuadrillaPesca:
    op = _operacion(session, tenant_id, op_id)
    if op.estado == "cerrada":
        raise HTTPException(409, "No se pueden modificar asignaciones de una operación cerrada")
    if op.modalidad_pago_cuadrilla == "DESGLOSE" and datos.activa and datos.monto_pago is None:
        raise HTTPException(422, "La modalidad por desglose requiere el monto en efectivo de cada integrante activo")
    nombre = datos.nombre_integrante.strip()
    asignacion = session.scalar(
        select(AsignacionCuadrillaPesca).where(
            AsignacionCuadrillaPesca.tenant_id == tenant_id,
            AsignacionCuadrillaPesca.operacion_id == op_id,
            AsignacionCuadrillaPesca.actividad == datos.actividad,
            AsignacionCuadrillaPesca.nombre_integrante == nombre,
        )
    )
    if asignacion is None:
        asignacion = AsignacionCuadrillaPesca(
            tenant_id=tenant_id, operacion_id=op_id, actividad=datos.actividad,
            nombre_integrante=nombre, activa=datos.activa, monto_pago=datos.monto_pago,
            asignado_por_cuenta_id=auth.cuenta_id,
        )
        session.add(asignacion)
        accion = "cuadrilla_integrante_registrado"
    else:
        asignacion.activa = datos.activa
        asignacion.monto_pago = datos.monto_pago
        asignacion.asignado_por_cuenta_id = auth.cuenta_id
        asignacion.updated_at = datetime.now(UTC)
        accion = "cuadrilla_integrante_actualizado"
    _historial(session, tenant_id, op.id, auth.codigo, accion,
               f"Actividad {datos.actividad}; integrante {nombre}; pago asignado {datos.monto_pago or '—'}; estado {'activo' if datos.activa else 'inactivo'}")
    session.commit()
    session.refresh(asignacion)
    return asignacion


@router.put("/operaciones/{op_id}/cuadrilla/pago", dependencies=[_requiere_rol_pesca("JEFE_CUADRILLA")])
def configurar_pago_cuadrilla(
    op_id: uuid.UUID, datos: PagoCuadrillaIn, session: SessionDep,
    tenant_id: TenantDep, auth: OperativeAuthDep,
) -> dict[str, str | None]:
    op = _operacion(session, tenant_id, op_id)
    if op.estado == "cerrada":
        raise HTTPException(409, "No se puede cambiar el pago de una operación cerrada")
    if datos.modalidad == "DESGLOSE":
        integrantes = list(session.scalars(select(AsignacionCuadrillaPesca).where(
            AsignacionCuadrillaPesca.tenant_id == tenant_id,
            AsignacionCuadrillaPesca.operacion_id == op.id,
            AsignacionCuadrillaPesca.activa.is_(True),
        )))
        if not integrantes:
            raise HTTPException(409, "Registra a los integrantes y su monto antes de activar el pago por desglose")
        incompletos = [f"{fila.actividad}: {fila.nombre_integrante}" for fila in integrantes if not fila.monto_pago or fila.monto_pago <= 0]
        if incompletos:
            raise HTTPException(409, {"mensaje": "Completa el pago en efectivo de cada integrante activo", "integrantes": incompletos})
    else:
        filas = session.scalars(select(AsignacionCuadrillaPesca).where(
            AsignacionCuadrillaPesca.tenant_id == tenant_id,
            AsignacionCuadrillaPesca.operacion_id == op.id,
        ))
        for fila in filas:
            fila.monto_pago = None
    op.modalidad_pago_cuadrilla = datos.modalidad
    op.monto_pago_cuadrilla = datos.monto_unico if datos.modalidad == "UNICO" else None
    _historial(session, tenant_id, op.id, auth.codigo, "modalidad_pago_cuadrilla",
               f"Modalidad {datos.modalidad}; canal de entrega: efectivo por el Jefe de Cuadrilla; monto único {datos.monto_unico or '—'}")
    session.commit()
    return {"modalidad": op.modalidad_pago_cuadrilla, "monto_unico": str(op.monto_pago_cuadrilla) if op.monto_pago_cuadrilla is not None else None}


@router.get("/operaciones/{op_id}/responsables-pesaje-muelle/candidatos", response_model=list[CuentaResponsablePesaje], dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
def candidatos_responsable_pesaje_muelle(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep,
) -> list[CuentaResponsablePesaje]:
    _operacion(session, tenant_id, op_id)
    rows = session.execute(
        select(CuentaAcceso, AsignacionRolPesca.rol)
        .join(AsignacionRolPesca, AsignacionRolPesca.cuenta_id == CuentaAcceso.id)
        .where(
            CuentaAcceso.tenant_id == tenant_id,
            CuentaAcceso.activo.is_(True),
            CuentaAcceso.deleted_at.is_(None),
            AsignacionRolPesca.tenant_id == tenant_id,
            AsignacionRolPesca.activa.is_(True),
            AsignacionRolPesca.rol.in_(("APUNTADOR_MUELLE", "ENCARGADO_MUELLE")),
        )
        .order_by(CuentaAcceso.login)
    ).all()
    salida = []
    for cuenta, rol in rows:
        codigo, nombre = _etiqueta_cuenta_pesca(session, cuenta)
        salida.append(CuentaResponsablePesaje(cuenta_id=cuenta.id, rol=rol, codigo=codigo, nombre=nombre))
    return salida


@router.put("/operaciones/{op_id}/responsable-pesaje-muelle", response_model=OperacionOut, dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
def asignar_responsable_pesaje_muelle(
    op_id: uuid.UUID, datos: ResponsablePesajeMuelleIn, session: SessionDep,
    tenant_id: TenantDep, auth: OperativeAuthDep,
) -> OperacionOut:
    op = _operacion(session, tenant_id, op_id)
    if op.estado not in {"preparacion", "en_descarga"}:
        raise HTTPException(409, "El responsable del pesaje de muelle solo se puede asignar antes del despacho a planta")
    cuenta = session.scalar(select(CuentaAcceso).where(
        CuentaAcceso.id == datos.cuenta_id,
        CuentaAcceso.tenant_id == tenant_id,
        CuentaAcceso.activo.is_(True),
        CuentaAcceso.deleted_at.is_(None),
    ))
    if cuenta is None:
        raise HTTPException(404, "La cuenta responsable no existe o está inactiva en este tenant")
    rol_asignado = session.scalar(select(AsignacionRolPesca.id).where(
        AsignacionRolPesca.tenant_id == tenant_id,
        AsignacionRolPesca.cuenta_id == cuenta.id,
        AsignacionRolPesca.rol == datos.rol,
        AsignacionRolPesca.activa.is_(True),
    ))
    if rol_asignado is None:
        raise HTTPException(422, "La persona seleccionada no tiene activo el rol correspondiente")
    if op.responsable_pesaje_muelle_cuenta_id != datos.cuenta_id:
        ya_hay_cargas = session.scalar(select(CargaEmbarcacionVehiculo.id).where(
            CargaEmbarcacionVehiculo.tenant_id == tenant_id,
            CargaEmbarcacionVehiculo.descarga_id.in_(
                select(DescargaEmbarcacion.id).where(DescargaEmbarcacion.operacion_id == op.id)
            ),
        ))
        if ya_hay_cargas is not None:
            raise HTTPException(409, "No se puede cambiar al responsable después de registrar cargas o pesos")
    op.responsable_pesaje_muelle = datos.rol
    op.responsable_pesaje_muelle_cuenta_id = cuenta.id
    _historial(session, tenant_id, op.id, auth.codigo, "responsable_pesaje_muelle_asignado",
               f"Jefe de Bahía asignó el registro del peso de muelle a {cuenta.login} como {datos.rol}")
    session.commit()
    session.refresh(op)
    return _operacion_para_actor(op, True)


def _operacion(session: Session, tenant_id: uuid.UUID, op_id: uuid.UUID) -> OperacionPesca:
    obj = session.scalar(
        select(OperacionPesca).where(
            OperacionPesca.id == op_id, OperacionPesca.tenant_id == tenant_id
        )
    )
    if obj is None:
        raise HTTPException(404, "Operación no encontrada")
    return obj


def _vehiculo(session: Session, tenant_id: uuid.UUID, vehiculo_id: uuid.UUID) -> VehiculoPesca:
    obj = session.scalar(
        select(VehiculoPesca).where(
            VehiculoPesca.id == vehiculo_id, VehiculoPesca.tenant_id == tenant_id
        )
    )
    if obj is None:
        raise HTTPException(404, "Vehículo no encontrado")
    return obj


@router.get("/vehiculos/{vehiculo_id}/actividades", response_model=list[ActividadCuadrillaOut], dependencies=[_requiere_rol_pesca("JEFE_CUADRILLA")])
def listar_actividades_cuadrilla(
    vehiculo_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> list[ActividadCuadrillaPesca]:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    return list(session.scalars(select(ActividadCuadrillaPesca).where(
        ActividadCuadrillaPesca.tenant_id == tenant_id,
        ActividadCuadrillaPesca.vehiculo_id == vehicle.id,
    ).order_by(ActividadCuadrillaPesca.actividad)))


@router.put("/vehiculos/{vehiculo_id}/actividades", response_model=ActividadCuadrillaOut, dependencies=[_requiere_rol_pesca("JEFE_CUADRILLA")])
def guardar_actividad_cuadrilla(
    vehiculo_id: uuid.UUID, datos: ActividadCuadrillaIn, session: SessionDep,
    tenant_id: TenantDep, auth: OperativeAuthDep,
) -> ActividadCuadrillaPesca:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    op = _operacion(session, tenant_id, vehicle.operacion_id)
    if op.estado == "cerrada":
        raise HTTPException(409, "La operación está cerrada")
    registro = session.scalar(select(ActividadCuadrillaPesca).where(
        ActividadCuadrillaPesca.tenant_id == tenant_id,
        ActividadCuadrillaPesca.vehiculo_id == vehicle.id,
        ActividadCuadrillaPesca.actividad == datos.actividad,
    ))
    antes = "registro creado"
    if registro is None:
        registro = ActividadCuadrillaPesca(
            tenant_id=tenant_id, operacion_id=op.id, vehiculo_id=vehicle.id,
            actividad=datos.actividad, actor_cuenta_id=auth.cuenta_id,
        )
        session.add(registro)
    else:
        if not datos.observacion:
            raise HTTPException(422, "Indica el motivo para actualizar una tarea registrada")
        antes = f"estado={registro.estado}; cajas={registro.cajas}; hielo_kg={registro.hielo_kg}"
        registro.actor_cuenta_id = auth.cuenta_id
    registro.estado = datos.estado
    registro.cajas = datos.cajas
    registro.hielo_kg = datos.hielo_kg
    registro.verificacion_visual = datos.verificacion_visual
    registro.contaminacion_detectada = datos.contaminacion_detectada
    registro.revision_final = datos.revision_final
    registro.observacion = datos.observacion
    registro.updated_at = datetime.now(UTC)
    session.flush()
    _historial(session, tenant_id, op.id, auth.codigo, f"cuadrilla_{datos.actividad.casefold()}",
        f"Jefe de Cuadrilla registra control del vehículo {vehicle.placa}; antes: {antes}; estado={datos.estado}, cajas={datos.cajas}, hielo_kg={datos.hielo_kg}, visual={datos.verificacion_visual}, contaminación={datos.contaminacion_detectada}, revisión_final={datos.revision_final}; nota={datos.observacion or '—'}", vehicle.id)
    session.commit()
    session.refresh(registro)
    return registro


def _tipos_documento_vehiculo(
    session: Session, tenant_id: uuid.UUID, op_id: uuid.UUID, vehicle_id: uuid.UUID
) -> set[str]:
    base = (
        DocumentoPesca.tenant_id == tenant_id,
        DocumentoPesca.operacion_id == op_id,
        DocumentoPesca.vigente.is_(True),
        DocumentoPesca.estado_revision == "VERIFICADO",
    )
    ids_documentos_embarcacion = select(VinculoDocumentoEmbarcacion.documento_id).join(
        DocumentoPesca, DocumentoPesca.id == VinculoDocumentoEmbarcacion.documento_id
    ).where(*base)
    tipos = set(session.scalars(select(DocumentoPesca.tipo).where(
        *base,
        DocumentoPesca.vehiculo_id.is_(None),
        ~DocumentoPesca.id.in_(ids_documentos_embarcacion),
    )))
    tipos.update(session.scalars(select(DocumentoPesca.tipo).where(
        *base, DocumentoPesca.vehiculo_id == vehicle_id,
    )))
    linked = set(
        session.scalars(
            select(VinculoDocumentoVehiculo.documento_id).where(
                VinculoDocumentoVehiculo.vehiculo_id == vehicle_id
            )
        )
    )
    if linked:
        tipos.update(
            session.scalars(
                select(DocumentoPesca.tipo).where(
                    DocumentoPesca.tenant_id == tenant_id,
                    DocumentoPesca.operacion_id == op_id,
                    DocumentoPesca.id.in_(linked),
                    DocumentoPesca.vigente.is_(True),
                    DocumentoPesca.estado_revision == "VERIFICADO",
                )
            )
        )
    vessel_ids = select(DescargaEmbarcacion.embarcacion_id).join(
        CargaEmbarcacionVehiculo,
        CargaEmbarcacionVehiculo.descarga_id == DescargaEmbarcacion.id,
    ).where(
        DescargaEmbarcacion.tenant_id == tenant_id,
        CargaEmbarcacionVehiculo.tenant_id == tenant_id,
        CargaEmbarcacionVehiculo.vehiculo_id == vehicle_id,
    )
    tipos.update(session.scalars(
        select(DocumentoPesca.tipo)
        .join(VinculoDocumentoEmbarcacion, VinculoDocumentoEmbarcacion.documento_id == DocumentoPesca.id)
        .where(*base, VinculoDocumentoEmbarcacion.embarcacion_id.in_(vessel_ids))
    ))
    return tipos


def _historial(
    session: Session,
    tenant_id: uuid.UUID,
    operacion_id: uuid.UUID,
    actor: str,
    accion: str,
    detalle: str,
    vehiculo_id: uuid.UUID | None = None,
) -> None:
    session.add(
        HistorialPesca(
            tenant_id=tenant_id,
            operacion_id=operacion_id,
            vehiculo_id=vehiculo_id,
            actor=actor,
            accion=accion,
            detalle=detalle,
        )
    )


@router.post("/operaciones", response_model=OperacionOut, status_code=201, dependencies=[_requiere_rol_pesca("ARMADOR", "PATRON")])
def crear_operacion(
    datos: OperacionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    hoy: HoyDep,
    actor: ActorDep,
    auth: OperativeAuthDep,
) -> OperacionOut:
    op = OperacionPesca(
        tenant_id=tenant_id,
        fecha_reporte=datos.fecha_reporte or hoy,
        puerto=datos.puerto,
        muelle=datos.muelle,
        planta=datos.planta,
        armador_reportante=datos.armador_reportante,
        comprador=datos.comprador,
        remitente=datos.remitente,
        destinatario=datos.destinatario,
        facturador=datos.facturador,
        toneladas_declaradas=datos.toneladas_declaradas,
        precio_propuesto=datos.precio_propuesto,
        descarga_prevista=datos.descarga_prevista,
        llegada_planta_prevista=datos.llegada_planta_prevista,
        jefe_bahia=datos.jefe_bahia,
        encargado_muelle=datos.encargado_muelle,
        apuntador=datos.apuntador,
        responsable_pesaje_muelle=None,
        responsable_id=actor[:200],
        estado="preparacion",
        observacion=datos.observacion,
    )
    session.add(op)
    session.flush()
    _historial(session, tenant_id, op.id, actor, "operacion_creada", "Operación iniciada")
    session.commit()
    session.refresh(op)
    return _operacion_para_actor(op, _puede_ver_precios(session, tenant_id, auth.cuenta_id))


@router.post("/operaciones/{op_id}/iniciar-descarga", response_model=OperacionOut, dependencies=[_requiere_rol_pesca("JEFE_BAHIA", "ENCARGADO_MUELLE")])
def iniciar_descarga_operacion(
    op_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
    auth: OperativeAuthDep,
) -> OperacionOut:
    op = _operacion(session, tenant_id, op_id)
    if op.estado != "preparacion":
        raise HTTPException(409, "La operación no está en etapa de preparación")
    if not op.responsable_pesaje_muelle:
        raise HTTPException(409, "El Jefe de Bahía debe designar al Apuntador de Muelle o Encargado de Muelle para el pesaje")
    if op.precio_confirmado is None:
        raise HTTPException(409, "Falta la aceptación del precio acordado por Jefe de Bahía o Gerente")
    if op.precio_ajuste_pendiente:
        raise HTTPException(409, "Hay un ajuste de precio pendiente de aceptación; resuélvelo antes de iniciar la descarga")
    if not op.responsable_pesaje_muelle or not op.responsable_pesaje_muelle_cuenta_id:
        raise HTTPException(409, "El Jefe de Bahía debe asignar a una persona responsable del pesaje de muelle")
    responsable_activo = session.scalar(select(AsignacionRolPesca.id).where(
        AsignacionRolPesca.tenant_id == tenant_id,
        AsignacionRolPesca.cuenta_id == op.responsable_pesaje_muelle_cuenta_id,
        AsignacionRolPesca.rol == op.responsable_pesaje_muelle,
        AsignacionRolPesca.activa.is_(True),
    ))
    if responsable_activo is None:
        raise HTTPException(409, "El responsable de pesaje ya no tiene el rol activo; reasígnalo antes de iniciar")
    embarcaciones = list(
        session.scalars(
            select(DescargaEmbarcacion).where(
                DescargaEmbarcacion.operacion_id == op.id,
                DescargaEmbarcacion.tenant_id == tenant_id,
            )
        )
    )
    if not embarcaciones:
        raise HTTPException(409, "Registra al menos una embarcación antes de iniciar la descarga")
    if op.toneladas_declaradas is None and any(item.peso_declarado_kg is None for item in embarcaciones):
        raise HTTPException(409, "Registra el peso declarado de la operación o de cada embarcación")
    vehiculo_preparado = session.scalar(
        select(VehiculoPesca.id).where(
            VehiculoPesca.operacion_id == op.id,
            VehiculoPesca.tenant_id == tenant_id,
        ).limit(1)
    )
    if vehiculo_preparado is None:
        raise HTTPException(409, "Prepara y registra al menos un vehículo antes de iniciar la descarga")
    vinculos_nave = select(VinculoDocumentoEmbarcacion.documento_id)
    documentos_globales = list(
        session.scalars(
            select(DocumentoPesca).where(
                DocumentoPesca.operacion_id == op.id,
                DocumentoPesca.tenant_id == tenant_id,
                DocumentoPesca.vigente.is_(True),
                DocumentoPesca.estado_revision == "VERIFICADO",
                DocumentoPesca.vehiculo_id.is_(None),
                ~DocumentoPesca.id.in_(vinculos_nave),
            )
        )
    )
    tipos_globales = {doc.tipo for doc in documentos_globales}
    requeridos = {
        "certificado_matricula",
        "permiso_pesca",
        "certificado_sanipes",
        "reporte_satelital",
        "visto_bueno_produce",
        "guia_remitente",
    }
    faltantes_por_nave: list[str] = []
    for descarga in embarcaciones:
        tipos_nave = set(tipos_globales)
        tipos_nave.update(
            session.scalars(
                select(DocumentoPesca.tipo)
                .join(VinculoDocumentoEmbarcacion, VinculoDocumentoEmbarcacion.documento_id == DocumentoPesca.id)
                .where(
                    DocumentoPesca.tenant_id == tenant_id,
                    DocumentoPesca.operacion_id == op.id,
                    DocumentoPesca.vigente.is_(True),
                    DocumentoPesca.estado_revision == "VERIFICADO",
                    VinculoDocumentoEmbarcacion.embarcacion_id == descarga.embarcacion_id,
                )
            )
        )
        missing = sorted(requeridos - tipos_nave)
        if missing:
            embarcacion = session.get(EmbarcacionPesca, descarga.embarcacion_id)
            nombre_nave = embarcacion.matricula if embarcacion else str(descarga.embarcacion_id)
            faltantes_por_nave.append(f"{nombre_nave}: {', '.join(missing)}")
    faltantes = faltantes_por_nave
    if faltantes:
        raise HTTPException(409, f"Faltan documentos previos a descarga por embarcación: {'; '.join(faltantes)}")
    op.estado = "en_descarga"
    _historial(session, tenant_id, op.id, actor, "descarga_iniciada", "Documentos y precio verificados; descarga autorizada")
    session.commit()
    session.refresh(op)
    return _operacion_para_actor(op, _puede_ver_precios(session, tenant_id, auth.cuenta_id))


@router.post("/operaciones/{op_id}/confirmar-precio", response_model=OperacionOut, dependencies=[_requiere_rol_pesca("JEFE_BAHIA", "GERENTE")])
def confirmar_precio(
    op_id: uuid.UUID,
    datos: ConfirmarPrecioIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> OperacionPesca:
    op = _operacion(session, tenant_id, op_id)
    if op.estado != "preparacion":
        raise HTTPException(409, "El precio inicial solo se acepta durante la preparación")
    if op.precio_confirmado is not None:
        raise HTTPException(409, "El precio ya fue confirmado y no se puede cambiar")
    if op.precio_propuesto is None or op.precio_propuesto <= 0:
        raise HTTPException(409, "La embarcación aún no ha ingresado un precio acordado")
    if not op.precio_acuerdo_embarcacion_confirmado:
        raise HTTPException(409, "Primero el Patrón o Armador debe confirmar el precio acordado")
    op.precio_confirmado = op.precio_propuesto
    op.precio_confirmado_por = actor[:200]
    op.precio_confirmado_at = datetime.now(UTC)
    _historial(
        session,
        tenant_id,
        op.id,
        actor,
        "precio_confirmado",
        f"Jefe de Bahía/Gerente aceptó el precio acordado por la embarcación: S/ {op.precio_confirmado}",
    )
    session.commit()
    session.refresh(op)
    return op


@router.post("/operaciones/{op_id}/confirmar-acuerdo-embarcacion", response_model=OperacionOut, dependencies=[_requiere_rol_pesca("ARMADOR", "PATRON")])
def confirmar_acuerdo_embarcacion(
    op_id: uuid.UUID, datos: ConfirmarAcuerdoEmbarcacionIn,
    session: SessionDep, tenant_id: TenantDep, actor: ActorDep, auth: OperativeAuthDep,
) -> OperacionOut:
    op = _operacion(session, tenant_id, op_id)
    _exigir_embarcacion_reportante(op, actor)
    if op.estado != "preparacion":
        raise HTTPException(409, "La confirmación de la embarcación debe hacerse durante la preparación")
    if op.precio_confirmado is not None:
        raise HTTPException(409, "El precio ya fue aceptado por Jefe de Bahía o Gerente")
    if op.precio_propuesto is None or op.precio_propuesto <= 0:
        raise HTTPException(409, "Ingresa primero el precio acordado con Jefe de Bahía o Gerente")
    if op.precio_acuerdo_embarcacion_confirmado:
        raise HTTPException(409, "La embarcación ya confirmó el precio acordado")
    op.precio_acuerdo_embarcacion_confirmado = True
    op.precio_acuerdo_embarcacion_confirmado_por = actor[:200]
    op.precio_acuerdo_embarcacion_confirmado_at = datetime.now(UTC)
    _historial(session, tenant_id, op.id, actor, "precio_acuerdo_embarcacion_confirmado",
               "Patrón/Armador confirmó que el precio ingresado corresponde al acuerdo realizado con Jefe de Bahía o Gerente")
    session.commit()
    session.refresh(op)
    return _operacion_para_actor(op, _puede_ver_precios(session, tenant_id, auth.cuenta_id))


@router.post("/operaciones/{op_id}/solicitar-ajuste-precio", response_model=OperacionOut, dependencies=[_requiere_rol_pesca("ARMADOR", "PATRON")])
def solicitar_ajuste_precio(
    op_id: uuid.UUID, datos: SolicitarAjustePrecioIn,
    session: SessionDep, tenant_id: TenantDep, actor: ActorDep, auth: OperativeAuthDep,
) -> OperacionOut:
    op = _operacion(session, tenant_id, op_id)
    _exigir_embarcacion_reportante(op, actor)
    if op.estado != "preparacion":
        raise HTTPException(409, "El precio solo se puede ajustar durante la preparación y antes de iniciar la descarga")
    if op.precio_confirmado is None:
        raise HTTPException(409, "El precio inicial aún no ha sido aceptado; completa primero la confirmación inicial")
    if op.precio_ajuste_pendiente:
        raise HTTPException(409, "Ya hay un ajuste de precio pendiente de aceptación")
    if op.precio_propuesto == datos.precio_acordado:
        raise HTTPException(422, "El nuevo precio debe ser distinto al precio aceptado actualmente")
    anterior = op.precio_confirmado
    op.precio_propuesto = datos.precio_acordado
    op.precio_acuerdo_embarcacion_confirmado = True
    op.precio_acuerdo_embarcacion_confirmado_por = actor[:200]
    op.precio_acuerdo_embarcacion_confirmado_at = datetime.now(UTC)
    _historial(session, tenant_id, op.id, actor, "ajuste_precio_solicitado",
        f"Patrón/Armador solicita cambio del precio aceptado S/ {anterior} a S/ {datos.precio_acordado}. Motivo: {datos.motivo.strip()}")
    session.commit()
    session.refresh(op)
    return _operacion_para_actor(op, _puede_ver_precios(session, tenant_id, auth.cuenta_id))


@router.post("/operaciones/{op_id}/aceptar-ajuste-precio", response_model=OperacionOut, dependencies=[_requiere_rol_pesca("JEFE_BAHIA", "GERENTE")])
def aceptar_ajuste_precio(
    op_id: uuid.UUID, datos: ConfirmarPrecioIn,
    session: SessionDep, tenant_id: TenantDep, actor: ActorDep,
) -> OperacionPesca:
    op = _operacion(session, tenant_id, op_id)
    if op.estado != "preparacion":
        raise HTTPException(409, "El ajuste de precio debe aceptarse antes de iniciar la descarga")
    if not op.precio_ajuste_pendiente or not op.precio_acuerdo_embarcacion_confirmado:
        raise HTTPException(409, "No hay un ajuste confirmado por la embarcación pendiente de aceptación")
    anterior = op.precio_confirmado
    op.precio_confirmado = op.precio_propuesto
    op.precio_confirmado_por = actor[:200]
    op.precio_confirmado_at = datetime.now(UTC)
    _historial(session, tenant_id, op.id, actor, "ajuste_precio_aceptado",
        f"Jefe de Bahía/Gerente aceptó el ajuste solicitado por la embarcación: anterior S/ {anterior}; nuevo S/ {op.precio_confirmado}")
    session.commit()
    session.refresh(op)
    return op


@router.post("/operaciones/{op_id}/factura", response_model=OperacionOut, dependencies=[_requiere_rol_pesca("SECRETARIA")])
def registrar_factura(
    op_id: uuid.UUID,
    datos: RegistrarFacturaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
    auth: OperativeAuthDep,
) -> OperacionOut:
    op = _operacion(session, tenant_id, op_id)
    if op.estado != "cerrada":
        raise HTTPException(409, "Registra la factura después de cerrar la recepción de todos los vehículos")
    certificado = session.scalar(
        select(DocumentoPesca.id).where(
            DocumentoPesca.operacion_id == op.id,
            DocumentoPesca.tenant_id == tenant_id,
            DocumentoPesca.tipo == "certificado_procedencia",
            DocumentoPesca.vehiculo_id.is_(None),
            DocumentoPesca.vigente.is_(True),
            DocumentoPesca.estado_revision == "VERIFICADO",
        )
    )
    if certificado is None:
        raise HTTPException(409, "Falta adjuntar el certificado de procedencia")
    if op.factura_serie is not None:
        raise HTTPException(409, "La factura ya fue registrada para esta operación")
    op.factura_serie = datos.serie.strip().upper()
    op.factura_correlativo = datos.correlativo.strip()
    op.factura_emitida_at = datetime.now(UTC)
    op.factura_emitida_por = actor[:200]
    op.estado_facturacion = "pendiente_documento"
    _historial(session, tenant_id, op.id, actor, "factura_registrada", f"Factura {op.factura_serie}-{op.factura_correlativo}; pendiente adjuntar comprobante")
    session.commit()
    session.refresh(op)
    return _operacion_para_actor(op, _puede_ver_precios(session, tenant_id, auth.cuenta_id))


@router.get("/operaciones", response_model=list[OperacionOut], dependencies=[_requiere_rol_pesca(*ROLES_PESCA)])
def listar_operaciones(session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep) -> list[OperacionOut]:
    visible = _puede_ver_precios(session, tenant_id, auth.cuenta_id)
    operaciones = session.scalars(
        select(OperacionPesca)
        .where(OperacionPesca.tenant_id == tenant_id)
        .order_by(OperacionPesca.created_at.desc())
    )
    return [_operacion_para_actor(op, visible) for op in operaciones]


def _movimiento_out(session: Session, item: MovimientoPesca) -> MovimientoOut:
    abonado = session.scalar(
        select(func.coalesce(func.sum(AbonoMovimientoPesca.importe), 0)).where(
            AbonoMovimientoPesca.tenant_id == item.tenant_id,
            AbonoMovimientoPesca.movimiento_id == item.id,
        )
    ) or Decimal("0")
    saldo = max(Decimal("0"), item.importe - Decimal(abonado))
    if item.clase in {"gasto_empresa", "gasto_bahia_reembolsable"} and item.comprobante_documento_id is None:
        estado = "pendiente_cpe"
    elif item.clase in {"gasto_empresa", "gasto_bahia_reembolsable"} and item.voucher_documento_id is None:
        estado = "pendiente_voucher"
    elif item.clase == "gasto_empresa":
        estado = "pagado_empresa"
    elif saldo == 0:
        estado = "saldado"
    elif item.clase == "gasto_bahia_reembolsable":
        estado = "pendiente_reembolso"
    elif item.clase == "adelanto_armador_empresa":
        estado = "pendiente_devolucion"
    else:
        estado = "prestamo_personal_pendiente"
    return MovimientoOut.model_validate(item).model_copy(update={"abonado": abonado, "saldo": saldo, "estado": estado})


@router.post("/movimientos", response_model=MovimientoOut, status_code=201, dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
def crear_movimiento(
    datos: MovimientoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> MovimientoOut:
    if datos.operacion_id is not None:
        _operacion(session, tenant_id, datos.operacion_id)
    item = MovimientoPesca(
        tenant_id=tenant_id,
        operacion_id=datos.operacion_id,
        clase=datos.clase,
        pagador=datos.pagador,
        beneficiario=datos.beneficiario,
        concepto=datos.concepto,
        tipo_gasto=datos.tipo_gasto,
        tipo_comprobante=datos.tipo_comprobante,
        motivo_boleta_muelle=datos.motivo_boleta_muelle,
        importe=datos.importe,
        moneda=datos.moneda,
        cantidad=datos.cantidad,
        tarifa_unitaria=datos.tarifa_unitaria,
        registrado_por=actor[:200],
    )
    session.add(item)
    session.flush()
    if item.operacion_id:
        _historial(session, tenant_id, item.operacion_id, actor, "movimiento_financiero_registrado", f"{item.clase}: {item.concepto}; importe {item.moneda} {item.importe}")
    session.commit()
    session.refresh(item)
    return _movimiento_out(session, item)


@router.get("/operaciones/{op_id}/movimientos", response_model=list[MovimientoOut], dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
def listar_movimientos_operacion(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> list[MovimientoOut]:
    _operacion(session, tenant_id, op_id)
    items = session.scalars(
        select(MovimientoPesca)
        .where(MovimientoPesca.tenant_id == tenant_id, MovimientoPesca.operacion_id == op_id)
        .order_by(MovimientoPesca.created_at)
    )
    return [_movimiento_out(session, item) for item in items]


@router.get("/movimientos-personales", response_model=list[MovimientoOut], dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
def listar_prestamos_personales(session: SessionDep, tenant_id: TenantDep, actor: ActorDep) -> list[MovimientoOut]:
    items = session.scalars(
        select(MovimientoPesca)
        .where(
            MovimientoPesca.tenant_id == tenant_id,
            MovimientoPesca.clase == "prestamo_personal_bahia",
            MovimientoPesca.registrado_por == actor,
        )
        .order_by(MovimientoPesca.created_at.desc())
    )
    return [_movimiento_out(session, item) for item in items]


@router.post("/movimientos/{movimiento_id}/abonos", response_model=AbonoMovimientoOut, status_code=201, dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
async def registrar_abono_movimiento(
    movimiento_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    actor: ActorDep,
    importe: Decimal = Form(..., gt=0),
    observacion: str | None = Form(default=None, max_length=1000),
    archivo_voucher: UploadFile | None = File(default=None),
) -> AbonoMovimientoPesca:
    item = session.scalar(
        select(MovimientoPesca).where(
            MovimientoPesca.id == movimiento_id, MovimientoPesca.tenant_id == tenant_id
        )
    )
    if item is None:
        raise HTTPException(404, "Movimiento no encontrado")
    if item.clase == "prestamo_personal_bahia" and item.registrado_por != actor:
        raise HTTPException(404, "Movimiento no encontrado")
    if item.clase == "gasto_empresa":
        raise HTTPException(409, "Un gasto pagado directamente por la empresa no tiene saldo por cobrar")
    if item.clase in {"gasto_bahia_reembolsable", "gasto_empresa"} and item.comprobante_documento_id is None:
        raise HTTPException(409, "Adjunta primero el CPE requerido para registrar un reembolso o abono")
    if item.clase != "prestamo_personal_bahia" and archivo_voucher is None:
        raise HTTPException(422, "Adjunta el voucher que sustenta este pago")
    current = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(AbonoMovimientoPesca.importe), 0)).where(
                AbonoMovimientoPesca.tenant_id == tenant_id,
                AbonoMovimientoPesca.movimiento_id == item.id,
            )
        ) or 0
    )
    if current + importe > item.importe:
        raise HTTPException(422, "El abono supera el saldo pendiente")
    tipo = {
        "gasto_bahia_reembolsable": "reembolso_bahia",
        "adelanto_armador_empresa": "devolucion_armador",
        "prestamo_personal_bahia": "abono_prestamo_personal",
    }[item.clase]
    voucher_doc = None
    if archivo_voucher is not None:
        mime = archivo_voucher.content_type or "application/octet-stream"
        if mime not in MIME_PERMITIDOS:
            raise HTTPException(415, "Solo se permiten PDF, JPG, PNG o WEBP")
        raw = await archivo_voucher.read(settings.max_upload_mb * 1024 * 1024 + 1)
        if len(raw) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, "Archivo demasiado grande")
        if not raw:
            raise HTTPException(422, "Archivo vacío")
        digest = hashlib.sha256(raw).hexdigest()
        voucher_doc = DocumentoPesca(
            tenant_id=tenant_id, operacion_id=item.operacion_id, tipo="voucher_pago",
            nombre=archivo_voucher.filename or "voucher-pago", mime_type=mime,
            sha256=digest, ruta_storage=almacen.guardar(tenant_id, digest, raw),
            subido_por=actor[:200],
        )
        session.add(voucher_doc)
        session.flush()
    abono = AbonoMovimientoPesca(
        tenant_id=tenant_id,
        movimiento_id=item.id,
        importe=importe,
        tipo=tipo,
        registrado_por=actor[:200],
        observacion=observacion,
        voucher_documento_id=voucher_doc.id if voucher_doc else None,
    )
    session.add(abono)
    if item.operacion_id:
        _historial(session, tenant_id, item.operacion_id, actor, tipo, f"Abono {item.moneda} {importe} al movimiento {item.id}; voucher {voucher_doc.id if voucher_doc else 'no requerido para préstamo personal'}")
    session.commit()
    session.refresh(abono)
    return abono


@router.post("/movimientos/{movimiento_id}/comprobante", response_model=DocumentoOut, status_code=201, dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
async def adjuntar_comprobante_movimiento(
    movimiento_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    actor: ActorDep,
    archivo: UploadFile = File(...),
) -> DocumentoPesca:
    item = session.scalar(
        select(MovimientoPesca).where(
            MovimientoPesca.id == movimiento_id, MovimientoPesca.tenant_id == tenant_id
        )
    )
    if item is None or (item.clase == "prestamo_personal_bahia" and item.registrado_por != actor):
        raise HTTPException(404, "Movimiento no encontrado")
    if item.comprobante_documento_id is not None:
        raise HTTPException(409, "Este movimiento ya tiene un comprobante adjunto")
    mime = archivo.content_type or "application/octet-stream"
    if mime not in MIME_PERMITIDOS:
        raise HTTPException(415, "Solo se permiten PDF, JPG, PNG o WEBP")
    raw = await archivo.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Archivo demasiado grande")
    if not raw:
        raise HTTPException(422, "Archivo vacío")
    digest = hashlib.sha256(raw).hexdigest()
    path = almacen.guardar(tenant_id, digest, raw)
    doc = DocumentoPesca(
        tenant_id=tenant_id,
        operacion_id=item.operacion_id,
        tipo=item.tipo_comprobante or "comprobante_gasto",
        nombre=archivo.filename or "comprobante",
        mime_type=mime,
        sha256=digest,
        ruta_storage=path,
        subido_por=actor[:200],
    )
    session.add(doc)
    session.flush()
    item.comprobante_documento_id = doc.id
    if item.operacion_id:
        _historial(session, tenant_id, item.operacion_id, actor, "comprobante_financiero_cargado", f"Comprobante {doc.nombre} para {item.clase}")
    session.commit()
    session.refresh(doc)
    return doc


@router.post("/movimientos/{movimiento_id}/voucher", response_model=DocumentoOut, status_code=201, dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
async def adjuntar_voucher_movimiento(
    movimiento_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    actor: ActorDep,
    archivo: UploadFile = File(...),
) -> DocumentoPesca:
    item = session.scalar(select(MovimientoPesca).where(
        MovimientoPesca.id == movimiento_id, MovimientoPesca.tenant_id == tenant_id,
    ))
    if item is None or (item.clase == "prestamo_personal_bahia" and item.registrado_por != actor):
        raise HTTPException(404, "Movimiento no encontrado")
    if item.voucher_documento_id is not None:
        raise HTTPException(409, "Este movimiento ya tiene voucher adjunto")
    mime = archivo.content_type or "application/octet-stream"
    if mime not in MIME_PERMITIDOS:
        raise HTTPException(415, "Solo se permiten PDF, JPG, PNG o WEBP")
    raw = await archivo.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Archivo demasiado grande")
    if not raw:
        raise HTTPException(422, "Archivo vacío")
    digest = hashlib.sha256(raw).hexdigest()
    doc = DocumentoPesca(
        tenant_id=tenant_id, operacion_id=item.operacion_id, tipo="voucher_pago",
        nombre=archivo.filename or "voucher-pago", mime_type=mime, sha256=digest,
        ruta_storage=almacen.guardar(tenant_id, digest, raw), subido_por=actor[:200],
    )
    session.add(doc)
    session.flush()
    item.voucher_documento_id = doc.id
    if item.operacion_id:
        _historial(session, tenant_id, item.operacion_id, actor, "voucher_pago_cargado", f"Voucher {doc.nombre} para {item.clase}")
    session.commit()
    session.refresh(doc)
    return doc


@router.post("/operaciones/{op_id}/embarcaciones", response_model=DescargaOut, status_code=201, dependencies=[_requiere_rol_pesca("ARMADOR", "PATRON")])
def agregar_embarcacion(
    op_id: uuid.UUID,
    datos: EmbarcacionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> DescargaOut:
    op = _operacion(session, tenant_id, op_id)
    if op.estado != "preparacion":
        raise HTTPException(409, "Las embarcaciones deben quedar vinculadas antes de iniciar la descarga")
    embarcacion = session.scalar(
        select(EmbarcacionPesca).where(
            EmbarcacionPesca.tenant_id == tenant_id,
            EmbarcacionPesca.matricula == datos.matricula,
        )
    )
    if embarcacion is None:
        embarcacion = EmbarcacionPesca(
            tenant_id=tenant_id,
            matricula=datos.matricula,
            nombre=datos.nombre,
            patron_armador=f"Armador: {datos.armador}; patrón: {datos.patron}",
            armador=datos.armador,
            patron=datos.patron,
            intermediario=datos.intermediario,
        )
        session.add(embarcacion)
        session.flush()
    else:
        embarcacion.nombre = datos.nombre
        embarcacion.patron_armador = f"Armador: {datos.armador}; patrón: {datos.patron}"
        embarcacion.armador = datos.armador
        embarcacion.patron = datos.patron
        embarcacion.intermediario = datos.intermediario
    descarga = DescargaEmbarcacion(
        tenant_id=tenant_id,
        operacion_id=op.id,
        embarcacion_id=embarcacion.id,
        matricula_snapshot=embarcacion.matricula,
        nombre_snapshot=embarcacion.nombre,
        armador_snapshot=datos.armador.strip(),
        patron_snapshot=datos.patron.strip(),
        inicio_descarga=datos.inicio_descarga,
        fin_descarga=datos.fin_descarga,
        peso_declarado_kg=datos.peso_declarado_kg,
    )
    session.add(descarga)
    _historial(session, tenant_id, op.id, actor, "embarcacion_agregada", f"Embarcación {datos.matricula}")
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "La embarcación ya está vinculada a esta operación") from exc
    return DescargaOut(
        descarga_id=descarga.id,
        embarcacion_id=embarcacion.id,
        matricula=descarga.matricula_snapshot,
        nombre=descarga.nombre_snapshot,
        armador=descarga.armador_snapshot,
        patron=descarga.patron_snapshot,
        peso_declarado_kg=descarga.peso_declarado_kg,
        inicio_descarga=descarga.inicio_descarga,
        fin_descarga=descarga.fin_descarga,
    )


@router.get("/operaciones/{op_id}/embarcaciones", response_model=list[DescargaOut], dependencies=[_requiere_rol_pesca(*ROLES_PESCA)])
def listar_embarcaciones(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> list[DescargaOut]:
    _operacion(session, tenant_id, op_id)
    rows = session.execute(
        select(DescargaEmbarcacion, EmbarcacionPesca)
        .join(EmbarcacionPesca, EmbarcacionPesca.id == DescargaEmbarcacion.embarcacion_id)
        .where(
            DescargaEmbarcacion.operacion_id == op_id,
            DescargaEmbarcacion.tenant_id == tenant_id,
        )
        .order_by(DescargaEmbarcacion.created_at)
    )
    return [
        DescargaOut(
            descarga_id=descarga.id,
            embarcacion_id=vessel.id,
            matricula=descarga.matricula_snapshot,
            nombre=descarga.nombre_snapshot,
            armador=descarga.armador_snapshot,
            patron=descarga.patron_snapshot,
            peso_declarado_kg=descarga.peso_declarado_kg,
            inicio_descarga=descarga.inicio_descarga,
            fin_descarga=descarga.fin_descarga,
        )
        for descarga, vessel in rows
    ]


@router.patch("/descargas/{descarga_id}/fechas", response_model=DescargaOut, dependencies=[_requiere_rol_pesca("ENCARGADO_MUELLE", "APUNTADOR_MUELLE")])
def actualizar_tiempos_descarga(
    descarga_id: uuid.UUID,
    datos: TiemposDescargaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> DescargaOut:
    descarga = session.scalar(
        select(DescargaEmbarcacion).where(
            DescargaEmbarcacion.id == descarga_id,
            DescargaEmbarcacion.tenant_id == tenant_id,
        )
    )
    if descarga is None:
        raise HTTPException(404, "Descarga no encontrada")
    op = _operacion(session, tenant_id, descarga.operacion_id)
    if op.estado == "cerrada":
        raise HTTPException(409, "La operación está cerrada")
    antes = f"inicio={descarga.inicio_descarga}; fin={descarga.fin_descarga}"
    if "inicio_descarga" in datos.model_fields_set:
        descarga.inicio_descarga = datos.inicio_descarga
    if "fin_descarga" in datos.model_fields_set:
        descarga.fin_descarga = datos.fin_descarga
    _historial(
        session,
        tenant_id,
        op.id,
        actor,
        "horas_descarga_actualizadas",
        f"Matrícula de descarga {descarga.embarcacion_id}; antes: {antes}; ahora: inicio={descarga.inicio_descarga}; fin={descarga.fin_descarga}. Motivo: {datos.observacion}",
    )
    session.commit()
    vessel = session.get(EmbarcacionPesca, descarga.embarcacion_id)
    if vessel is None:
        raise HTTPException(404, "Embarcación no encontrada")
    return DescargaOut(
        descarga_id=descarga.id,
        embarcacion_id=vessel.id,
        matricula=descarga.matricula_snapshot,
        nombre=descarga.nombre_snapshot,
        armador=descarga.armador_snapshot,
        patron=descarga.patron_snapshot,
        peso_declarado_kg=descarga.peso_declarado_kg,
        inicio_descarga=descarga.inicio_descarga,
        fin_descarga=descarga.fin_descarga,
    )


@router.post("/operaciones/{op_id}/vehiculos", response_model=VehiculoOut, status_code=201, dependencies=[_requiere_rol_pesca(*ROLES_CONTROL_OPERACION)])
def agregar_vehiculo(
    op_id: uuid.UUID,
    datos: VehiculoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> VehiculoPesca:
    op = _operacion(session, tenant_id, op_id)
    if op.estado not in {"preparacion", "en_descarga"}:
        raise HTTPException(409, "No se pueden agregar vehículos después del despacho a planta")
    vehicle = VehiculoPesca(
        tenant_id=tenant_id,
        operacion_id=op_id,
        placa=datos.placa,
        tipo=datos.tipo,
        chofer=datos.chofer,
        turno=datos.turno,
        estado="pendiente_muelle",
    )
    session.add(vehicle)
    session.flush()
    _historial(session, tenant_id, op_id, actor, "vehiculo_agregado", f"Vehículo {datos.placa}", vehicle.id)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.post("/vehiculos/{vehiculo_id}/traslado/iniciar", response_model=VehiculoOut, dependencies=[_requiere_rol_pesca(*ROLES_CONTROL_OPERACION)])
def iniciar_traslado_planta(
    vehiculo_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> VehiculoPesca:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    op = _operacion(session, tenant_id, vehicle.operacion_id)
    if op.estado != "en_descarga":
        raise HTTPException(409, "La operación debe estar en descarga antes de despachar el vehículo")
    if vehicle.estado != "pendiente_muelle":
        raise HTTPException(409, "El vehículo no está esperando despacho desde el muelle")
    tiene_carga = session.scalar(
        select(CargaEmbarcacionVehiculo.id).where(
            CargaEmbarcacionVehiculo.tenant_id == tenant_id,
            CargaEmbarcacionVehiculo.vehiculo_id == vehicle.id,
        ).limit(1)
    )
    if tiene_carga is None:
        raise HTTPException(409, "Asigna el peso y la embarcación de origen antes de despachar")
    tipos = _tipos_documento_vehiculo(session, tenant_id, op.id, vehicle.id)
    requeridos = {"guia_remitente", "guia_transportista", "acta_fiscalizacion", "formato_descarga"}
    faltantes = sorted(requeridos - tipos)
    if faltantes:
        raise HTTPException(409, f"Faltan documentos para el traslado: {', '.join(faltantes)}")
    vehicle.salida_muelle = datetime.now(UTC)
    vehicle.estado = "en_traslado"
    _historial(session, tenant_id, op.id, actor, "vehiculo_despachado", f"Traslado a planta iniciado a las {vehicle.salida_muelle.isoformat()}", vehicle.id)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.post("/vehiculos/{vehiculo_id}/planta/iniciar", response_model=VehiculoOut, dependencies=[_requiere_rol_pesca(*ROLES_CONTROL_PLANTA)])
def iniciar_descarga_planta(
    vehiculo_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    hoy: HoyDep,
    actor: ActorDep,
) -> VehiculoPesca:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado != "en_traslado":
        raise HTTPException(409, "Registra la salida del muelle con carga y documentos antes del ingreso a planta")
    if vehicle.estado == "cerrado":
        raise HTTPException(409, "El registro del vehículo ya está cerrado")
    vehicle.fecha_reporte_planta = vehicle.fecha_reporte_planta or hoy
    vehicle.llegada_planta = vehicle.llegada_planta or datetime.now(UTC)
    vehicle.estado = "en_planta"
    _historial(session, tenant_id, vehicle.operacion_id, actor, "llegada_planta_registrada", f"Llegada real a planta: {vehicle.llegada_planta.isoformat()}", vehicle.id)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.post("/vehiculos/{vehiculo_id}/planta/descarga/iniciar", response_model=VehiculoOut, dependencies=[_requiere_rol_pesca(*ROLES_CONTROL_PLANTA)])
def iniciar_descarga_en_planta(
    vehiculo_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> VehiculoPesca:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado != "en_planta" or vehicle.llegada_planta is None:
        raise HTTPException(409, "Registra primero la llegada real del vehículo a planta")
    if vehicle.inicio_planta is not None:
        raise HTTPException(409, "El inicio de descarga en planta ya está registrado")
    vehicle.inicio_planta = datetime.now(UTC)
    _historial(session, tenant_id, vehicle.operacion_id, actor, "descarga_planta_iniciada", f"Inicio real de descarga en planta: {vehicle.inicio_planta.isoformat()}", vehicle.id)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.patch("/vehiculos/{vehiculo_id}/planta/fechas", response_model=VehiculoOut, dependencies=[_requiere_rol_pesca(*ROLES_CONTROL_PLANTA)])
def actualizar_tiempos_planta(
    vehiculo_id: uuid.UUID,
    datos: TiemposPlantaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> VehiculoPesca:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado not in {"en_traslado", "en_planta", "pendiente_evidencia"}:
        raise HTTPException(409, "Los horarios de planta se editan después del despacho y antes del cierre")
    antes = {
        "fecha_reporte_planta": str(vehicle.fecha_reporte_planta) if vehicle.fecha_reporte_planta else None,
        "llegada_planta": vehicle.llegada_planta.isoformat() if vehicle.llegada_planta else None,
        "inicio_planta": vehicle.inicio_planta.isoformat() if vehicle.inicio_planta else None,
        "fin_planta": vehicle.fin_planta.isoformat() if vehicle.fin_planta else None,
    }
    if "fecha_reporte_planta" in datos.model_fields_set:
        vehicle.fecha_reporte_planta = datos.fecha_reporte_planta
    if "llegada_planta" in datos.model_fields_set:
        vehicle.llegada_planta = datos.llegada_planta
    if "inicio_planta" in datos.model_fields_set:
        vehicle.inicio_planta = datos.inicio_planta
    if "fin_planta" in datos.model_fields_set:
        vehicle.fin_planta = datos.fin_planta
    if vehicle.salida_muelle and vehicle.llegada_planta and vehicle.llegada_planta < vehicle.salida_muelle:
        raise HTTPException(422, "La llegada a planta no puede ser anterior a la salida del muelle")
    if vehicle.inicio_planta and vehicle.llegada_planta is None:
        raise HTTPException(422, "Registra la llegada a planta antes del inicio de descarga")
    if vehicle.llegada_planta and vehicle.inicio_planta and vehicle.inicio_planta < vehicle.llegada_planta:
        raise HTTPException(422, "El inicio de descarga en planta no puede ser anterior a la llegada")
    if vehicle.inicio_planta and vehicle.fin_planta and vehicle.fin_planta < vehicle.inicio_planta:
        raise HTTPException(422, "El fin de descarga en planta no puede ser anterior al inicio")
    _historial(
        session,
        tenant_id,
        vehicle.operacion_id,
        actor,
        "fechas_planta_editadas",
        f"Antes: {antes}; ahora: fecha={vehicle.fecha_reporte_planta}, llegada={vehicle.llegada_planta}, inicio={vehicle.inicio_planta}, fin={vehicle.fin_planta}. Motivo: {datos.observacion}",
        vehicle.id,
    )
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.post("/vehiculos/{vehiculo_id}/cargas", status_code=201)
def agregar_carga(
    vehiculo_id: uuid.UUID,
    datos: CargaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    op = _operacion(session, tenant_id, vehicle.operacion_id)
    asignado = session.scalar(select(AsignacionRolPesca.id).where(
        AsignacionRolPesca.tenant_id == tenant_id,
        AsignacionRolPesca.cuenta_id == auth.cuenta_id,
        AsignacionRolPesca.rol == op.responsable_pesaje_muelle,
        AsignacionRolPesca.activa.is_(True),
    ))
    if asignado is None or auth.cuenta_id != op.responsable_pesaje_muelle_cuenta_id:
        raise HTTPException(403, "El Jefe de Bahía debe asignarte a ti como responsable del pesaje de muelle para esta operación")
    if op.estado != "en_descarga":
        raise HTTPException(409, "Primero completa la preparación y autoriza el inicio de descarga")
    if vehicle.estado != "pendiente_muelle":
        raise HTTPException(409, "La carga solo se puede modificar mientras el vehículo está en el muelle")
    descarga = session.scalar(
        select(DescargaEmbarcacion).where(
            DescargaEmbarcacion.id == datos.descarga_id,
            DescargaEmbarcacion.tenant_id == tenant_id,
            DescargaEmbarcacion.operacion_id == vehicle.operacion_id,
        )
    )
    if descarga is None:
        raise HTTPException(404, "La embarcación no pertenece a esta operación")
    session.add(
        CargaEmbarcacionVehiculo(
            tenant_id=tenant_id,
            descarga_id=descarga.id,
            vehiculo_id=vehicle.id,
            peso_muelle_kg=datos.peso_muelle_kg,
            cajas=datos.cajas,
            observacion=datos.observacion,
        )
    )
    _historial(session, tenant_id, vehicle.operacion_id, actor, "carga_asignada", "Carga de embarcación asignada al vehículo", vehicle.id)
    session.commit()
    return {"estado": "registrado", "vehiculo_id": str(vehicle.id)}


@router.post("/operaciones/{op_id}/documentos", response_model=DocumentoOut, status_code=201, dependencies=[_requiere_rol_pesca(*ROLES_DOCUMENTACION)])
async def subir_documento(
    op_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    actor: ActorDep,
    archivo: UploadFile = File(...),
    tipo: str = Form(...),
    etapa: str | None = Form(default=None),
    vehiculo_ids: list[uuid.UUID] = Form(default=[]),
    embarcacion_ids: list[uuid.UUID] = Form(default=[]),
    reemplaza_documento_id: uuid.UUID | None = Form(default=None),
) -> DocumentoPesca:
    op = _operacion(session, tenant_id, op_id)
    if tipo not in TIPOS_DOCUMENTO:
        raise HTTPException(422, "Tipo de documento no reconocido")
    etapa_final = etapa or ETAPA_POR_TIPO.get(tipo, "GENERAL")
    if etapa_final not in ETAPAS_DOCUMENTO:
        raise HTTPException(422, "Etapa documental no reconocida")
    etapa_fija = ETAPA_POR_TIPO.get(tipo)
    if etapa_fija is not None and etapa_final != etapa_fija:
        raise HTTPException(422, f"El tipo {tipo} corresponde a la etapa {etapa_fija}")
    if tipo == "factura" and (op.factura_serie is None or op.factura_correlativo is None):
        raise HTTPException(409, "Primero registra serie y correlativo de la factura después del cierre y del certificado de procedencia")
    mime = archivo.content_type or "application/octet-stream"
    if mime not in MIME_PERMITIDOS:
        raise HTTPException(415, "Solo se permiten PDF, JPG, PNG o WEBP")
    raw = await archivo.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Archivo demasiado grande")
    if not raw:
        raise HTTPException(422, "Archivo vacío")
    vehicles: list[VehiculoPesca] = []
    for vehicle_id in vehiculo_ids:
        vehicle = _vehiculo(session, tenant_id, vehicle_id)
        if vehicle.operacion_id != op.id:
            raise HTTPException(422, "Todos los vehículos deben pertenecer a la operación")
        vehicles.append(vehicle)
    vessels: list[EmbarcacionPesca] = []
    for vessel_id in embarcacion_ids:
        vessel = session.scalar(
            select(EmbarcacionPesca)
            .join(DescargaEmbarcacion, DescargaEmbarcacion.embarcacion_id == EmbarcacionPesca.id)
            .where(
                EmbarcacionPesca.id == vessel_id,
                EmbarcacionPesca.tenant_id == tenant_id,
                DescargaEmbarcacion.operacion_id == op.id,
                DescargaEmbarcacion.tenant_id == tenant_id,
            )
        )
        if vessel is None:
            raise HTTPException(422, "Todas las embarcaciones deben pertenecer a la operación")
        vessels.append(vessel)
    if tipo == "certificado_procedencia" and (vehicles or vessels):
        raise HTTPException(422, "El certificado de procedencia debe adjuntarse a toda la operación")
    documento_anterior = None
    if reemplaza_documento_id is not None:
        documento_anterior = session.scalar(select(DocumentoPesca).where(
            DocumentoPesca.id == reemplaza_documento_id,
            DocumentoPesca.tenant_id == tenant_id,
            DocumentoPesca.operacion_id == op.id,
            DocumentoPesca.tipo == tipo,
            DocumentoPesca.vigente.is_(True),
        ))
        if documento_anterior is None:
            raise HTTPException(404, "El documento que se quiere reemplazar no está vigente en esta operación")
        if etapa_final != documento_anterior.etapa:
            raise HTTPException(422, "La nueva versión debe conservar la etapa del documento anterior")
        vehiculos_previos = set(session.scalars(select(VinculoDocumentoVehiculo.vehiculo_id).where(
            VinculoDocumentoVehiculo.documento_id == documento_anterior.id,
        )))
        if documento_anterior.vehiculo_id is not None:
            vehiculos_previos.add(documento_anterior.vehiculo_id)
        embarcaciones_previas = set(session.scalars(select(VinculoDocumentoEmbarcacion.embarcacion_id).where(
            VinculoDocumentoEmbarcacion.documento_id == documento_anterior.id,
        )))
        if not {item.id for item in vehicles}.issubset(vehiculos_previos) or not {item.id for item in vessels}.issubset(embarcaciones_previas):
            raise HTTPException(422, "La nueva versión no puede ampliar el alcance del documento anterior")
    digest = hashlib.sha256(raw).hexdigest()
    existente = session.scalar(
        select(DocumentoPesca).where(
            DocumentoPesca.tenant_id == tenant_id,
            DocumentoPesca.operacion_id == op.id,
            DocumentoPesca.tipo == tipo,
            DocumentoPesca.sha256 == digest,
            DocumentoPesca.vigente.is_(True),
        )
    )
    if existente is not None:
        for vehicle in vehicles:
            vinculo = session.get(VinculoDocumentoVehiculo, (existente.id, vehicle.id))
            if vinculo is None:
                session.add(VinculoDocumentoVehiculo(documento_id=existente.id, vehiculo_id=vehicle.id))
        for vessel in vessels:
            vinculo = session.get(VinculoDocumentoEmbarcacion, (existente.id, vessel.id))
            if vinculo is None:
                session.add(VinculoDocumentoEmbarcacion(documento_id=existente.id, embarcacion_id=vessel.id))
        _historial(session, tenant_id, op.id, actor, "documento_reutilizado", f"{tipo}: {existente.nombre}")
        session.commit()
        session.refresh(existente)
        return existente
    path = almacen.guardar(tenant_id, digest, raw)
    doc = DocumentoPesca(
        tenant_id=tenant_id,
        operacion_id=op.id,
        vehiculo_id=vehicles[0].id if len(vehicles) == 1 else None,
        tipo=tipo,
        etapa=etapa_final,
        nombre=archivo.filename or "archivo",
        mime_type=mime,
        sha256=digest,
        ruta_storage=path,
        subido_por=actor[:200],
        estado_revision="PENDIENTE",
        observacion_revision=None,
        revisado_por=None,
        revisado_at=None,
        version=(documento_anterior.version + 1) if documento_anterior else 1,
        vigente=True,
        documento_anterior_id=documento_anterior.id if documento_anterior else None,
    )
    session.add(doc)
    session.flush()
    for vehicle in vehicles:
        session.add(VinculoDocumentoVehiculo(documento_id=doc.id, vehiculo_id=vehicle.id))
    for vessel in vessels:
        session.add(VinculoDocumentoEmbarcacion(documento_id=doc.id, embarcacion_id=vessel.id))
    if documento_anterior is not None:
        doc.vehiculo_id = doc.vehiculo_id or documento_anterior.vehiculo_id
        documento_anterior.vigente = False
        for link in session.scalars(select(VinculoDocumentoVehiculo).where(VinculoDocumentoVehiculo.documento_id == documento_anterior.id)):
            if session.get(VinculoDocumentoVehiculo, (doc.id, link.vehiculo_id)) is None:
                session.add(VinculoDocumentoVehiculo(documento_id=doc.id, vehiculo_id=link.vehiculo_id))
        for link in session.scalars(select(VinculoDocumentoEmbarcacion).where(VinculoDocumentoEmbarcacion.documento_id == documento_anterior.id)):
            if session.get(VinculoDocumentoEmbarcacion, (doc.id, link.embarcacion_id)) is None:
                session.add(VinculoDocumentoEmbarcacion(documento_id=doc.id, embarcacion_id=link.embarcacion_id))
        _historial(session, tenant_id, op.id, actor, "documento_versionado", f"{tipo}: versión {doc.version} reemplaza documento {documento_anterior.id}")
    _historial(session, tenant_id, op.id, actor, "documento_cargado", f"{tipo}: {doc.nombre}")
    session.commit()
    session.refresh(doc)
    return doc


@router.get("/operaciones/{op_id}/documentos", response_model=list[DocumentoOut], dependencies=[_requiere_rol_pesca(*ROLES_PESCA)])
def listar_documentos_pesca(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> list[DocumentoPesca]:
    _operacion(session, tenant_id, op_id)
    return list(
        session.scalars(
            select(DocumentoPesca)
            .where(DocumentoPesca.operacion_id == op_id, DocumentoPesca.tenant_id == tenant_id)
            .order_by(DocumentoPesca.created_at)
        )
    )


@router.put("/documentos/{doc_id}/revision", response_model=DocumentoOut, dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
def revisar_documento_pesca(
    doc_id: uuid.UUID,
    datos: RevisionDocumentoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> DocumentoPesca:
    doc = session.scalar(select(DocumentoPesca).where(
        DocumentoPesca.id == doc_id,
        DocumentoPesca.tenant_id == tenant_id,
        DocumentoPesca.vigente.is_(True),
        DocumentoPesca.operacion_id.is_not(None),
    ))
    if doc is None:
        raise HTTPException(404, "Documento vigente de operación no encontrado")
    doc.estado_revision = datos.estado
    doc.observacion_revision = datos.observacion.strip() if datos.observacion else None
    doc.revisado_por = actor[:200]
    doc.revisado_at = datetime.now(UTC)
    if doc.tipo == "factura":
        op = _operacion(session, tenant_id, doc.operacion_id)
        op.estado_facturacion = "lista_para_pago" if datos.estado == "VERIFICADO" else "pendiente_documento"
    _historial(
        session, tenant_id, doc.operacion_id, actor,
        "documento_revision_actualizada",
        f"{doc.tipo} versión {doc.version}: {datos.estado}; observación={doc.observacion_revision or 'ninguna'}",
        doc.vehiculo_id,
    )
    session.commit()
    session.refresh(doc)
    return doc


@router.get("/operaciones/{op_id}/documentacion", dependencies=[_requiere_rol_pesca(*ROLES_PESCA)])
def revisar_documentacion(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> dict[str, object]:
    op = _operacion(session, tenant_id, op_id)
    vehicles = list(
        session.scalars(
            select(VehiculoPesca).where(
                VehiculoPesca.operacion_id == op.id, VehiculoPesca.tenant_id == tenant_id
            )
        )
    )
    docs = list(
        session.scalars(
            select(DocumentoPesca).where(
                DocumentoPesca.operacion_id == op.id,
                DocumentoPesca.tenant_id == tenant_id,
                DocumentoPesca.vigente.is_(True),
                DocumentoPesca.estado_revision == "VERIFICADO",
            )
        )
    )
    vinculos_naves = set(
        session.scalars(
            select(VinculoDocumentoEmbarcacion.documento_id)
            .join(DocumentoPesca, DocumentoPesca.id == VinculoDocumentoEmbarcacion.documento_id)
            .where(DocumentoPesca.tenant_id == tenant_id, DocumentoPesca.operacion_id == op.id)
        )
    )
    documentos_globales = {doc.id for doc in docs if doc.vehiculo_id is None and doc.id not in vinculos_naves}
    requeridos = (
        "certificado_matricula",
        "permiso_pesca",
        "certificado_sanipes",
        "reporte_satelital",
        "visto_bueno_produce",
        "guia_remitente",
        "guia_transportista",
        "acta_fiscalizacion",
        "formato_descarga",
        "certificado_procedencia",
        "factura",
        "peso_planta",
    )
    salida = []
    for vehicle in vehicles:
        vinculados = set(
            session.scalars(
                select(VinculoDocumentoVehiculo.documento_id).where(
                    VinculoDocumentoVehiculo.vehiculo_id == vehicle.id
                )
            )
        )
        ids_embarcaciones = set(
            session.scalars(
                select(DescargaEmbarcacion.embarcacion_id)
                .join(CargaEmbarcacionVehiculo, CargaEmbarcacionVehiculo.descarga_id == DescargaEmbarcacion.id)
                .where(
                    DescargaEmbarcacion.tenant_id == tenant_id,
                    CargaEmbarcacionVehiculo.tenant_id == tenant_id,
                    CargaEmbarcacionVehiculo.vehiculo_id == vehicle.id,
                )
            )
        )
        documentos_nave = set(
            session.scalars(
                select(VinculoDocumentoEmbarcacion.documento_id).where(
                    VinculoDocumentoEmbarcacion.embarcacion_id.in_(ids_embarcaciones)
                )
            )
        ) if ids_embarcaciones else set()
        documentos_validos = documentos_globales | vinculados | documentos_nave | {
            doc.id for doc in docs if doc.vehiculo_id == vehicle.id
        }
        tipos_disponibles = {doc.tipo for doc in docs if doc.id in documentos_validos}
        faltantes = [tipo for tipo in requeridos if tipo not in tipos_disponibles]
        salida.append(
            {
                "vehiculo_id": vehicle.id,
                "placa": vehicle.placa,
                "documentacion_lista": not faltantes,
                "faltantes": faltantes,
                "estado_entrega": vehicle.estado,
            }
        )
    return {"operacion_id": op.id, "planta": op.planta, "vehiculos": salida}


@router.get("/documentos/{doc_id}/archivo", dependencies=[_requiere_rol_pesca(*ROLES_PESCA)])
def descargar_documento_pesca(
    doc_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep, almacen: AlmacenDep, actor: ActorDep
) -> FileResponse:
    doc = session.scalar(
        select(DocumentoPesca).where(
            DocumentoPesca.id == doc_id, DocumentoPesca.tenant_id == tenant_id
        )
    )
    if doc is None:
        raise HTTPException(404, "Documento no encontrado")
    if doc.operacion_id is None:
        movement = session.scalar(
            select(MovimientoPesca).where(
                MovimientoPesca.tenant_id == tenant_id,
                MovimientoPesca.comprobante_documento_id == doc.id,
                MovimientoPesca.clase == "prestamo_personal_bahia",
                MovimientoPesca.registrado_por == actor,
            )
        )
        if movement is None:
            raise HTTPException(404, "Documento no encontrado")
    return FileResponse(
        almacen.ruta_absoluta(doc.ruta_storage),
        media_type=doc.mime_type,
        filename=doc.nombre,
        content_disposition_type="inline" if doc.mime_type.startswith("image/") else "attachment",
        headers={"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/vehiculos/{vehiculo_id}/planta", response_model=RegistroPlantaOut, dependencies=[_requiere_rol_pesca(*ROLES_CAPTURA_PLANTA)])
def registrar_peso_planta(
    vehiculo_id: uuid.UUID,
    datos: RegistroPlantaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> RegistroPlanta:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado == "cerrado":
        raise HTTPException(409, "El registro de planta está cerrado")
    if vehicle.estado not in {"en_planta", "pendiente_evidencia"}:
        raise HTTPException(409, "Registra primero la llegada y el inicio de recepción en planta")
    if vehicle.inicio_planta is None:
        raise HTTPException(409, "Registra el inicio real de descarga en planta antes del pesaje")
    if datos.resultado in {"completo", "parcial"} and datos.peso_aceptado <= 0:
        raise HTTPException(422, "El peso aceptado debe ser mayor que cero para un resultado completo o parcial")
    record = session.scalar(
        select(RegistroPlanta).where(
            RegistroPlanta.tenant_id == tenant_id,
            RegistroPlanta.vehiculo_id == vehicle.id,
        )
    )
    antes = "registro creado"
    if record is None:
        record = RegistroPlanta(tenant_id=tenant_id, vehiculo_id=vehicle.id)
        session.add(record)
    else:
        if not datos.observacion:
            raise HTTPException(422, "Explique en observaciones el cambio del registro de planta")
        antes = f"resultado={record.resultado}, peso={record.peso_aceptado} {record.unidad}"
    record.resultado = datos.resultado
    record.peso_aceptado = datos.peso_aceptado
    record.unidad = datos.unidad
    record.cajas_rechazadas = datos.cajas_rechazadas
    record.motivo_rechazo = datos.motivo_rechazo
    record.fecha_finalizacion = (
        None
        if datos.no_registrar_fecha_finalizacion
        else datos.fecha_finalizacion or datetime.now(UTC)
    )
    record.observacion = datos.observacion
    vehicle.fin_planta = record.fecha_finalizacion
    vehicle.estado = "pendiente_evidencia"
    session.flush()
    _historial(
        session,
        tenant_id,
        vehicle.operacion_id,
        actor,
        "peso_planta_registrado",
        f"Antes: {antes}; ahora: {datos.resultado}, {datos.peso_aceptado} {datos.unidad}",
        vehicle.id,
    )
    session.commit()
    session.refresh(record)
    return record


@router.get("/vehiculos/{vehiculo_id}/comparacion-planta", dependencies=[_requiere_rol_pesca(*ROLES_PESCA)])
def comparar_pesos(
    vehiculo_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> dict[str, object]:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    record = session.scalar(select(RegistroPlanta).where(RegistroPlanta.vehiculo_id == vehicle.id))
    muelle = session.scalar(
        select(func.coalesce(func.sum(CargaEmbarcacionVehiculo.peso_muelle_kg), 0)).where(
            CargaEmbarcacionVehiculo.tenant_id == tenant_id,
            CargaEmbarcacionVehiculo.vehiculo_id == vehicle.id,
        )
    )
    if record is None:
        raise HTTPException(404, "Aún no hay peso de planta")
    aceptado_kg = record.peso_aceptado * FACTOR_KG[record.unidad]
    muelle_decimal = Decimal(muelle)
    diferencia = aceptado_kg - muelle_decimal
    color = "sin_comparacion" if muelle_decimal == 0 else "verde" if diferencia > 0 else "naranja" if diferencia == 0 else "rojo"
    return {
        "vehiculo_id": vehicle.id,
        "estado": color,
        "peso_aceptado_kg": aceptado_kg,
        "peso_muelle_kg": muelle_decimal if muelle_decimal else None,
        "diferencia_kg": diferencia if muelle_decimal else None,
    }


@router.post("/vehiculos/{vehiculo_id}/planta/cerrar", response_model=CierreOut, dependencies=[_requiere_rol_pesca(*ROLES_CAPTURA_PLANTA)])
def cerrar_registro_planta(
    vehiculo_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> CierreOut:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado == "cerrado":
        raise HTTPException(409, "El registro de planta ya está cerrado")
    if vehicle.estado != "pendiente_evidencia":
        raise HTTPException(409, "Registra el peso de planta antes de cerrar el vehículo")
    record = session.scalar(
        select(RegistroPlanta).where(RegistroPlanta.tenant_id == tenant_id, RegistroPlanta.vehiculo_id == vehicle.id)
    )
    if record is None:
        raise HTTPException(409, "Registre el resultado y peso de planta antes de cerrar")
    evidence = session.scalar(
        select(DocumentoPesca.id)
        .outerjoin(VinculoDocumentoVehiculo, VinculoDocumentoVehiculo.documento_id == DocumentoPesca.id)
        .where(
            DocumentoPesca.tenant_id == tenant_id,
            DocumentoPesca.operacion_id == vehicle.operacion_id,
            DocumentoPesca.tipo == "peso_planta",
            DocumentoPesca.vigente.is_(True),
            DocumentoPesca.estado_revision == "VERIFICADO",
            ((DocumentoPesca.vehiculo_id == vehicle.id) | (VinculoDocumentoVehiculo.vehiculo_id == vehicle.id)),
        )
        .limit(1)
    )
    if evidence is None:
        raise HTTPException(409, "Suba la foto o archivo del peso de planta antes de cerrar")
    if record.resultado in {"completo", "parcial"} and record.peso_aceptado <= 0:
        raise HTTPException(409, "El peso aceptado debe ser mayor que cero")
    vehicle.estado = "cerrado"
    _historial(session, tenant_id, vehicle.operacion_id, actor, "vehiculo_planta_cerrado", "Registro de planta cerrado con evidencia", vehicle.id)
    session.commit()
    return CierreOut(estado="cerrado", mensaje="Registro del vehículo cerrado")


@router.post("/operaciones/{op_id}/cerrar", response_model=CierreOut, dependencies=[_requiere_rol_pesca("JEFE_BAHIA")])
def cerrar_operacion(
    op_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> CierreOut:
    op = _operacion(session, tenant_id, op_id)
    if op.estado == "cerrada":
        raise HTTPException(409, "La operación ya está cerrada")
    vehicles = list(session.scalars(select(VehiculoPesca).where(VehiculoPesca.operacion_id == op.id)))
    if not vehicles:
        raise HTTPException(409, "La operación aún no tiene vehículos")
    pendientes = [vehicle.placa for vehicle in vehicles if vehicle.estado != "cerrado"]
    if pendientes:
        raise HTTPException(409, {"mensaje": "Hay registros de planta pendientes", "vehiculos": pendientes})
    asignaciones_cuadrilla = list(
        session.scalars(
            select(AsignacionCuadrillaPesca).where(
                AsignacionCuadrillaPesca.tenant_id == tenant_id,
                AsignacionCuadrillaPesca.operacion_id == op.id,
                AsignacionCuadrillaPesca.activa.is_(True),
                AsignacionCuadrillaPesca.actividad.in_(("LAVADO", "CAJEO", "ESTIBA")),
            )
        )
    )
    tareas_pendientes = []
    for vehicle in vehicles:
        for asignacion in asignaciones_cuadrilla:
            tarea = session.scalar(
                select(ActividadCuadrillaPesca).where(
                    ActividadCuadrillaPesca.tenant_id == tenant_id,
                    ActividadCuadrillaPesca.vehiculo_id == vehicle.id,
                    ActividadCuadrillaPesca.actividad == asignacion.actividad,
                )
            )
            if tarea is None or tarea.estado != "COMPLETA":
                tareas_pendientes.append(f"{vehicle.placa}: {asignacion.actividad}")
    if tareas_pendientes:
        raise HTTPException(409, {"mensaje": "Completa las tareas de cuadrilla asignadas antes de cerrar", "tareas": tareas_pendientes})
    gastos_sin_cpe = list(session.scalars(select(MovimientoPesca).where(
        MovimientoPesca.tenant_id == tenant_id,
        MovimientoPesca.operacion_id == op.id,
        MovimientoPesca.clase.in_(("gasto_empresa", "gasto_bahia_reembolsable")),
        MovimientoPesca.comprobante_documento_id.is_(None),
    )))
    if gastos_sin_cpe:
        raise HTTPException(409, {
            "mensaje": "Adjunta el CPE correspondiente a cada salida de gasto antes de cerrar la operación",
            "gastos": [f"{item.tipo_gasto or 'SIN CLASIFICAR'}: {item.concepto} · S/ {item.importe}" for item in gastos_sin_cpe],
        })
    gastos_sin_voucher = list(session.scalars(select(MovimientoPesca).where(
        MovimientoPesca.tenant_id == tenant_id,
        MovimientoPesca.operacion_id == op.id,
        MovimientoPesca.clase.in_(("gasto_empresa", "gasto_bahia_reembolsable")),
        MovimientoPesca.voucher_documento_id.is_(None),
    )))
    if gastos_sin_voucher:
        raise HTTPException(409, {
            "mensaje": "Adjunta la evidencia del pago de cada gasto antes de cerrar la operación",
            "gastos": [f"{item.tipo_gasto or 'SIN CLASIFICAR'}: {item.concepto} · S/ {item.importe}" for item in gastos_sin_voucher],
        })
    op.estado = "cerrada"
    op.updated_at = datetime.now(UTC)
    _historial(session, tenant_id, op.id, actor, "operacion_cerrada", "Todos los vehículos tienen peso de planta y evidencia")
    session.commit()
    return CierreOut(estado="cerrada", mensaje="Operación cerrada")


@router.get("/operaciones/{op_id}/vehiculos", response_model=list[VehiculoOut], dependencies=[_requiere_rol_pesca(*ROLES_PESCA)])
def listar_vehiculos(op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep) -> list[VehiculoPesca]:
    _operacion(session, tenant_id, op_id)
    return list(session.scalars(select(VehiculoPesca).where(VehiculoPesca.operacion_id == op_id).order_by(VehiculoPesca.created_at)))


@router.get("/operaciones/{op_id}/historial", dependencies=[_requiere_rol_pesca("JEFE_BAHIA", "GERENTE")])
def historial_operacion(op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep) -> list[dict[str, object]]:
    _operacion(session, tenant_id, op_id)
    rows = session.scalars(
        select(HistorialPesca).where(HistorialPesca.operacion_id == op_id, HistorialPesca.tenant_id == tenant_id).order_by(HistorialPesca.created_at)
    )
    return [
        {"id": row.id, "vehiculo_id": row.vehiculo_id, "accion": row.accion, "actor": row.actor, "detalle": row.detalle, "fecha": row.created_at}
        for row in rows
    ]


@router.get("/operaciones/{op_id}/resumen", dependencies=[_requiere_rol_pesca(*ROLES_PESCA)])
def resumen_operacion(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> dict[str, object]:
    op = _operacion(session, tenant_id, op_id)
    vehicles = list(
        session.scalars(
            select(VehiculoPesca).where(
                VehiculoPesca.operacion_id == op.id, VehiculoPesca.tenant_id == tenant_id
            )
        )
    )
    total_aceptado_kg = Decimal(0)
    total_muelle_kg = Decimal(0)
    resumen_embarcaciones = []
    descargas = list(session.scalars(select(DescargaEmbarcacion).where(
        DescargaEmbarcacion.tenant_id == tenant_id,
        DescargaEmbarcacion.operacion_id == op.id,
    ).order_by(DescargaEmbarcacion.nombre_snapshot)))
    for descarga in descargas:
        peso_total = session.scalar(select(func.coalesce(func.sum(CargaEmbarcacionVehiculo.peso_muelle_kg), 0)).where(
            CargaEmbarcacionVehiculo.tenant_id == tenant_id,
            CargaEmbarcacionVehiculo.descarga_id == descarga.id,
        ))
        cajas_total = session.scalar(select(func.coalesce(func.sum(CargaEmbarcacionVehiculo.cajas), 0)).where(
            CargaEmbarcacionVehiculo.tenant_id == tenant_id,
            CargaEmbarcacionVehiculo.descarga_id == descarga.id,
        ))
        resumen_embarcaciones.append({
            "descarga_id": descarga.id,
            "nombre": descarga.nombre_snapshot,
            "matricula": descarga.matricula_snapshot,
            "peso_declarado_kg": descarga.peso_declarado_kg,
            "peso_muelle_total_kg": Decimal(peso_total),
            "cajas_total": int(cajas_total),
        })
    detalle = []
    for vehicle in vehicles:
        plant = session.scalar(
            select(RegistroPlanta).where(
                RegistroPlanta.tenant_id == tenant_id,
                RegistroPlanta.vehiculo_id == vehicle.id,
            )
        )
        muelle_value = session.scalar(
            select(func.coalesce(func.sum(CargaEmbarcacionVehiculo.peso_muelle_kg), 0)).where(
                CargaEmbarcacionVehiculo.tenant_id == tenant_id,
                CargaEmbarcacionVehiculo.vehiculo_id == vehicle.id,
            )
        )
        muelle_kg = Decimal(muelle_value)
        accepted_kg = plant.peso_aceptado * FACTOR_KG[plant.unidad] if plant else Decimal(0)
        total_muelle_kg += muelle_kg
        total_aceptado_kg += accepted_kg
        detalle.append(
            {
                "vehiculo_id": vehicle.id,
                "placa": vehicle.placa,
                "chofer": vehicle.chofer,
                "estado": vehicle.estado,
                "resultado_planta": plant.resultado if plant else "pendiente",
                "peso_aceptado": plant.peso_aceptado if plant else None,
                "unidad": plant.unidad if plant else None,
                "peso_aceptado_kg": accepted_kg if plant else None,
                "peso_muelle_kg": muelle_kg if muelle_kg else None,
            }
        )
    return {
        "operacion_id": op.id,
        "fecha_reporte": op.fecha_reporte,
        "puerto": op.puerto,
        "muelle": op.muelle,
        "planta": op.planta,
        "estado": op.estado,
        "embarcaciones": resumen_embarcaciones,
        "vehiculos": detalle,
        "total_peso_muelle_kg": total_muelle_kg,
        "total_peso_aceptado_planta_kg": total_aceptado_kg,
    }
