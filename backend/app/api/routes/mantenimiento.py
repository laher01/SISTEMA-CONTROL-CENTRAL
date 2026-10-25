import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select, update

from app.api.deps import AlmacenDep, OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import (
    AdelantoERP,
    Alerta,
    AlertaManual,
    CorreccionIA,
    CuentaAcceso,
    CuentaPagoERP,
    Documento,
    EliminacionArchivoPendiente,
    Expediente,
    Miembro,
    PagoERP,
    PlanLiquidacion,
    SolicitudRetiroMISD,
)
from app.schemas import (
    MantenimientoAdministradorOut,
    MantenimientoEjecutarIn,
    MantenimientoResultadoOut,
    MantenimientoSeleccionIn,
    MantenimientoVistaPreviaOut,
)
from app.services import auditoria

router = APIRouter(prefix="/configuracion/mantenimiento", tags=["mantenimiento"])

TIPOS = {
    "documentos": Documento,
    "expedientes": Expediente,
    "pagos": PagoERP,
    "adelantos": AdelantoERP,
    "planes": PlanLiquidacion,
    "cuentas_pago": CuentaPagoERP,
}


def _solo_administrador(rol: str) -> None:
    if rol != RolMiembro.ADMINISTRADOR:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el ADMINISTRADOR del tenant puede ejecutar mantenimiento crítico",
        )


def _validar_seleccion(datos: MantenimientoSeleccionIn) -> None:
    desconocidos = sorted(set(datos.tipos) - set(TIPOS))
    if desconocidos:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Tipos no permitidos: {', '.join(desconocidos)}",
        )
    if not datos.cuenta_ids and not datos.incluir_sin_trazabilidad:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Seleccione al menos un administrador o los registros sin trazabilidad",
        )
    if datos.fecha_desde and datos.fecha_hasta and datos.fecha_hasta < datos.fecha_desde:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La fecha final no puede ser anterior a la inicial",
        )


def _filtros(
    modelo: Any,
    tenant_id: uuid.UUID,
    datos: MantenimientoSeleccionIn,
) -> list[Any]:
    filtros: list[Any] = [modelo.tenant_id == tenant_id]
    creadores: list[Any] = []
    if datos.cuenta_ids:
        creadores.append(modelo.creado_por_cuenta_id.in_(datos.cuenta_ids))
    if datos.incluir_sin_trazabilidad:
        creadores.append(modelo.creado_por_cuenta_id.is_(None))
    if len(creadores) == 1:
        filtros.append(creadores[0])
    else:
        from sqlalchemy import or_

        filtros.append(or_(*creadores))
    if datos.fecha_desde is not None:
        filtros.append(func.date(modelo.created_at) >= datos.fecha_desde)
    if datos.fecha_hasta is not None:
        filtros.append(func.date(modelo.created_at) <= datos.fecha_hasta)
    return filtros


def _contar(session: SessionDep, modelo: Any, filtros: list[Any]) -> int:
    return int(session.scalar(select(func.count()).select_from(modelo).where(*filtros)) or 0)


def _filtros_creador(
    modelo: Any,
    tenant_id: uuid.UUID,
    cuenta_id: uuid.UUID | None,
) -> list[Any]:
    creador = (
        modelo.creado_por_cuenta_id.is_(None)
        if cuenta_id is None
        else modelo.creado_por_cuenta_id == cuenta_id
    )
    return [modelo.tenant_id == tenant_id, creador]


def _rol_cuenta(session: SessionDep, cuenta: CuentaAcceso) -> str:
    if cuenta.miembro_id is None:
        return "SIN_MIEMBRO"
    miembro = session.get(Miembro, cuenta.miembro_id)
    return miembro.rol if miembro is not None else "SIN_MIEMBRO"


@router.get("/diagnostico-documental")
def diagnostico_documental(
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    limit: int = Query(default=500, ge=1, le=2000),
) -> dict[str, object]:
    """Detecta originales ausentes y trabajos de limpieza sin modificar nada."""
    _solo_administrador(auth.rol)
    documentos = list(
        session.scalars(
            select(Documento)
            .where(Documento.tenant_id == tenant_id)
            .order_by(Documento.created_at.desc(), Documento.id)
            .limit(limit)
        )
    )
    faltantes: list[str] = []
    for documento in documentos:
        try:
            existe = almacen.ruta_absoluta(documento.ruta_storage).is_file()
        except (OSError, ValueError):
            existe = False
        if not existe:
            faltantes.append(str(documento.id))
    pendientes = int(
        session.scalar(
            select(func.count())
            .select_from(EliminacionArchivoPendiente)
            .where(
                EliminacionArchivoPendiente.tenant_id == tenant_id,
                EliminacionArchivoPendiente.estado == "PENDIENTE",
            )
        )
        or 0
    )
    bloqueados = int(
        session.scalar(
            select(func.count())
            .select_from(EliminacionArchivoPendiente)
            .where(
                EliminacionArchivoPendiente.tenant_id == tenant_id,
                EliminacionArchivoPendiente.estado == "BLOQUEADO",
            )
        )
        or 0
    )
    return {
        "solo_diagnostico": True,
        "documentos_revisados": len(documentos),
        "documentos_sin_original": len(faltantes),
        "documentos_sin_original_ids": faltantes[:100],
        "archivos_pendientes": pendientes,
        "archivos_bloqueados": bloqueados,
        "limite_revision": limit,
    }


@router.get("/administradores", response_model=list[MantenimientoAdministradorOut])
def administradores(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[MantenimientoAdministradorOut]:
    _solo_administrador(auth.rol)
    cuentas = list(
        session.scalars(
            select(CuentaAcceso).where(
                CuentaAcceso.tenant_id == tenant_id,
                CuentaAcceso.deleted_at.is_(None),
            )
        )
    )
    salida: list[MantenimientoAdministradorOut] = []
    for cuenta in cuentas:
        rol = _rol_cuenta(session, cuenta)
        if rol != RolMiembro.ADMINISTRADOR:
            continue
        registros = {
            nombre: _contar(
                session,
                modelo,
                _filtros_creador(modelo, tenant_id, cuenta.id),
            )
            for nombre, modelo in TIPOS.items()
        }
        salida.append(
            MantenimientoAdministradorOut(
                cuenta_id=cuenta.id,
                login=cuenta.login,
                rol=rol,
                registros=registros,
            )
        )

    historicos = {
        nombre: _contar(
            session,
            modelo,
            _filtros_creador(modelo, tenant_id, None),
        )
        for nombre, modelo in TIPOS.items()
    }
    if any(historicos.values()):
        salida.append(
            MantenimientoAdministradorOut(
                cuenta_id=None,
                login="SIN TRAZABILIDAD HISTÓRICA",
                rol="HISTORICO",
                registros=historicos,
            )
        )
    return salida


@router.post("/vista-previa", response_model=MantenimientoVistaPreviaOut)
def vista_previa(
    datos: MantenimientoSeleccionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> MantenimientoVistaPreviaOut:
    _solo_administrador(auth.rol)
    _validar_seleccion(datos)
    totales = {
        nombre: _contar(session, TIPOS[nombre], _filtros(TIPOS[nombre], tenant_id, datos))
        for nombre in datos.tipos
    }
    seleccionados = [
        item
        for item in administradores(session, tenant_id, auth)
        if (item.cuenta_id in datos.cuenta_ids)
        or (item.cuenta_id is None and datos.incluir_sin_trazabilidad)
    ]
    return MantenimientoVistaPreviaOut(administradores=seleccionados, totales=totales)


@router.post("/limpiar", response_model=MantenimientoResultadoOut)
def limpiar(
    datos: MantenimientoEjecutarIn,
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> MantenimientoResultadoOut:
    _solo_administrador(auth.rol)
    _validar_seleccion(datos)
    if datos.confirmacion != "ELIMINAR-DATOS-OPERATIVOS":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La frase de confirmación no coincide",
        )

    # La limpieza histórica no debe destruir solicitudes MISD ni generar
    # un fallo de clave foránea a mitad de la operación.
    if "expedientes" in datos.tipos:
        filtros_expedientes = _filtros(Expediente, tenant_id, datos)
        expedientes_solicitados = select(Expediente.id).where(*filtros_expedientes)
        solicitud_existente = session.scalar(
            select(SolicitudRetiroMISD.id)
            .where(
                SolicitudRetiroMISD.tenant_id == tenant_id,
                SolicitudRetiroMISD.expediente_id.in_(expedientes_solicitados),
            )
            .limit(1)
        )
        if solicitud_existente is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Hay expedientes con solicitudes MISD; la limpieza no puede eliminarlos",
            )

    eliminados = {nombre: 0 for nombre in datos.tipos}
    rutas_archivo: list[str] = []

    if "pagos" in datos.tipos:
        filtros = _filtros(PagoERP, tenant_id, datos)
        ids = list(session.scalars(select(PagoERP.id).where(*filtros)))
        if ids:
            session.execute(delete(PagoERP).where(PagoERP.id.in_(ids)))
        eliminados["pagos"] = len(ids)

    if "adelantos" in datos.tipos:
        filtros = _filtros(AdelantoERP, tenant_id, datos)
        ids = list(session.scalars(select(AdelantoERP.id).where(*filtros)))
        if ids:
            session.execute(delete(AdelantoERP).where(AdelantoERP.id.in_(ids)))
        eliminados["adelantos"] = len(ids)

    if "planes" in datos.tipos:
        filtros = _filtros(PlanLiquidacion, tenant_id, datos)
        ids = list(session.scalars(select(PlanLiquidacion.id).where(*filtros)))
        usados = 0
        if ids:
            usados = int(
                session.scalar(
                    select(func.count()).select_from(PagoERP).where(PagoERP.plan_id.in_(ids))
                )
                or 0
            )
        if usados:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Hay planes seleccionados vinculados a pagos no eliminados",
            )
        if ids:
            session.execute(delete(PlanLiquidacion).where(PlanLiquidacion.id.in_(ids)))
        eliminados["planes"] = len(ids)

    if "cuentas_pago" in datos.tipos:
        filtros = _filtros(CuentaPagoERP, tenant_id, datos)
        ids = list(session.scalars(select(CuentaPagoERP.id).where(*filtros)))
        if ids:
            session.execute(delete(CuentaPagoERP).where(CuentaPagoERP.id.in_(ids)))
        eliminados["cuentas_pago"] = len(ids)

    if "documentos" in datos.tipos:
        filtros = _filtros(Documento, tenant_id, datos)
        documentos = list(session.scalars(select(Documento).where(*filtros)))
        # Las operaciones de mantenimiento no pueden purgar originales ligados
        # a expedientes ni evidencias fiscales: requieren autorización y
        # comprobación de obligaciones en un flujo MISD específico.
        protegidos = [
            item
            for item in documentos
            if item.expediente_id is not None
            or item.tipo_documento is not None
            or item.huella_comercial is not None
        ]
        if protegidos:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Existen documentos fiscales o vinculados a expedientes; "
                "su purga física requiere el procedimiento MISD protegido",
            )
        ids = [item.id for item in documentos]
        rutas_archivo = [item.ruta_storage for item in documentos]
        if ids:
            session.execute(
                update(PagoERP)
                .where(PagoERP.voucher_documento_id.in_(ids))
                .values(voucher_documento_id=None)
            )
            session.execute(delete(CorreccionIA).where(CorreccionIA.documento_id.in_(ids)))
            session.execute(delete(Documento).where(Documento.id.in_(ids)))
        eliminados["documentos"] = len(ids)

    if "expedientes" in datos.tipos:
        filtros = _filtros(Expediente, tenant_id, datos)
        ids = list(session.scalars(select(Expediente.id).where(*filtros)))
        restantes = 0
        if ids:
            restantes = int(
                session.scalar(
                    select(func.count())
                    .select_from(Documento)
                    .where(Documento.expediente_id.in_(ids))
                )
                or 0
            )
        if restantes:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                (
                    "Hay expedientes seleccionados con documentos que no fueron "
                    "incluidos en la limpieza"
                ),
            )
        if ids:
            session.execute(delete(Alerta).where(Alerta.expediente_id.in_(ids)))
            session.execute(delete(AlertaManual).where(AlertaManual.expediente_id.in_(ids)))
            session.execute(delete(Expediente).where(Expediente.id.in_(ids)))
        eliminados["expedientes"] = len(ids)

    auditoria.registrar(
        session,
        tenant_id,
        "MANTENIMIENTO_SELECTIVO_EJECUTADO",
        "tenant",
        tenant_id,
        {
            "actor": auth.codigo,
            "cuenta_ids": [str(item) for item in datos.cuenta_ids],
            "incluye_sin_trazabilidad": datos.incluir_sin_trazabilidad,
            "tipos": datos.tipos,
            "fecha_desde": datos.fecha_desde.isoformat() if datos.fecha_desde else None,
            "fecha_hasta": datos.fecha_hasta.isoformat() if datos.fecha_hasta else None,
            "eliminados": eliminados,
            "ejecutado_at": datetime.now(UTC).isoformat(),
        },
    )
    pendientes = [
        EliminacionArchivoPendiente(tenant_id=tenant_id, ruta_storage=ruta)
        for ruta in rutas_archivo
    ]
    session.add_all(pendientes)
    session.commit()

    archivos_eliminados = 0
    for pendiente in pendientes:
        if _intentar_eliminar_archivo(session, almacen, pendiente):
            archivos_eliminados += 1
    session.commit()

    return MantenimientoResultadoOut(
        eliminados=eliminados,
        archivos_eliminados=archivos_eliminados,
    )


def _intentar_eliminar_archivo(
    session: SessionDep, almacen: AlmacenDep, pendiente: EliminacionArchivoPendiente
) -> bool:
    """Reintento idempotente: si el archivo ya no existe se marca completado."""
    pendiente.intentos += 1
    # Una retirada por SHA puede compartir archivo con otro documento; ni siquiera
    # un registro retirado lógicamente debe perder su original restaurable.
    referencias = session.scalar(
        select(Documento.id).where(Documento.ruta_storage == pendiente.ruta_storage).limit(1)
    )
    if referencias is not None:
        pendiente.estado = "BLOQUEADO"
        pendiente.ultimo_error = "Archivo todavía referenciado por un documento"
        return False
    try:
        archivo = almacen.ruta_absoluta(pendiente.ruta_storage)
        encontrado = archivo.exists()
        if encontrado:
            archivo.unlink()
        pendiente.estado = "COMPLETADO"
        pendiente.ultimo_error = None
        pendiente.completado_at = datetime.now(UTC)
        return encontrado
    except (OSError, ValueError) as exc:
        pendiente.estado = "PENDIENTE"
        pendiente.ultimo_error = str(exc)[:500]
        return False


@router.post("/reintentar-archivos")
def reintentar_archivos(
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, int]:
    _solo_administrador(auth.rol)
    pendientes = list(
        session.scalars(
            select(EliminacionArchivoPendiente)
            .where(
                EliminacionArchivoPendiente.tenant_id == tenant_id,
                EliminacionArchivoPendiente.estado == "PENDIENTE",
            )
            .order_by(EliminacionArchivoPendiente.created_at, EliminacionArchivoPendiente.id)
            .limit(100)
            .with_for_update(skip_locked=True)
        )
    )
    completados = 0
    for pendiente in pendientes:
        _intentar_eliminar_archivo(session, almacen, pendiente)
        if pendiente.estado == "COMPLETADO":
            completados += 1
    session.commit()
    return {"procesados": len(pendientes), "completados": completados}
