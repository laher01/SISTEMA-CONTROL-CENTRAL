import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
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
    Expediente,
    Miembro,
    PagoERP,
    PlanLiquidacion,
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


def _solo_superadmin(rol: str) -> None:
    if rol != RolMiembro.SUPERADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo SUPERADMIN puede ejecutar mantenimiento crítico",
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


def _filtros(modelo: object, tenant_id: uuid.UUID, datos: MantenimientoSeleccionIn) -> list[object]:
    filtros: list[object] = [modelo.tenant_id == tenant_id]  # type: ignore[attr-defined]
    creadores: list[object] = []
    if datos.cuenta_ids:
        creadores.append(modelo.creado_por_cuenta_id.in_(datos.cuenta_ids))  # type: ignore[attr-defined]
    if datos.incluir_sin_trazabilidad:
        creadores.append(modelo.creado_por_cuenta_id.is_(None))  # type: ignore[attr-defined]
    if len(creadores) == 1:
        filtros.append(creadores[0])
    else:
        from sqlalchemy import or_

        filtros.append(or_(*creadores))
    if datos.fecha_desde is not None:
        filtros.append(func.date(modelo.created_at) >= datos.fecha_desde)  # type: ignore[attr-defined]
    if datos.fecha_hasta is not None:
        filtros.append(func.date(modelo.created_at) <= datos.fecha_hasta)  # type: ignore[attr-defined]
    return filtros


def _contar(session: SessionDep, modelo: object, filtros: list[object]) -> int:
    return int(session.scalar(select(func.count()).select_from(modelo).where(*filtros)) or 0)


def _rol_cuenta(session: SessionDep, cuenta: CuentaAcceso) -> str:
    if cuenta.miembro_id is None:
        return "SIN_MIEMBRO"
    miembro = session.get(Miembro, cuenta.miembro_id)
    return miembro.rol if miembro is not None else "SIN_MIEMBRO"


@router.get("/administradores", response_model=list[MantenimientoAdministradorOut])
def administradores(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[MantenimientoAdministradorOut]:
    _solo_superadmin(auth.rol)
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
        if rol not in {RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR}:
            continue
        registros = {
            nombre: _contar(
                session,
                modelo,
                [
                    modelo.tenant_id == tenant_id,
                    modelo.creado_por_cuenta_id == cuenta.id,
                ],
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
            [
                modelo.tenant_id == tenant_id,
                modelo.creado_por_cuenta_id.is_(None),
            ],
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
    _solo_superadmin(auth.rol)
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
    _solo_superadmin(auth.rol)
    _validar_seleccion(datos)
    if datos.confirmacion != "ELIMINAR-DATOS-OPERATIVOS":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La frase de confirmación no coincide",
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
    session.commit()

    archivos_eliminados = 0
    for ruta in rutas_archivo:
        try:
            archivo = almacen.ruta_absoluta(ruta)
            if archivo.exists():
                archivo.unlink()
                archivos_eliminados += 1
        except (OSError, ValueError):
            continue

    return MantenimientoResultadoOut(
        eliminados=eliminados,
        archivos_eliminados=archivos_eliminados,
    )
