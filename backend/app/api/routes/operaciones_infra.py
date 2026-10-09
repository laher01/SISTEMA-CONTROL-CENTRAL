import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import inspect, select, text

from app.api.deps import SessionDep, SettingsDep
from app.api.routes.infraestructura import (
    AgenteDep,
    CorrelacionDep,
    SuperadminDep,
    sin_cache,
    version_publica,
)
from app.models_operaciones_infra import BackupInfra, OperacionInfra
from app.schemas_operaciones_infra import (
    BackupIn,
    DespliegueIn,
    LoteIn,
    RestauracionVerificadaIn,
    ResultadoOperacionIn,
    ValidacionVersionIn,
)
from app.services.operaciones_infra import OperacionesInfraService

router = APIRouter(
    prefix="/infraestructura",
    tags=["operaciones-infraestructura"],
    dependencies=[Depends(sin_cache)],
)


@router.get("/agentes/{nodo_id}/identidad")
def identidad_agente(nodo: AgenteDep, response: Response) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    return {"id": nodo.id, "entorno": nodo.entorno, "codigo": nodo.codigo}


def operacion_publica(operacion: OperacionInfra) -> dict[str, object]:
    return {
        "id": operacion.id,
        "nodo_id": operacion.nodo_id,
        "tipo": operacion.tipo,
        "estado": operacion.estado,
        "version_id": operacion.version_id,
        "grupo_id": operacion.grupo_id,
        "orden": operacion.orden,
        "creada_at": operacion.created_at,
        "iniciada_at": operacion.iniciada_at,
        "finalizada_at": operacion.finalizada_at,
        "resultado": operacion.resultado,
        "parametros": operacion.parametros,
    }


@router.get("/operaciones")
def listar_operaciones(
    session: SessionDep,
    auth: SuperadminDep,
    settings: SettingsDep,
) -> dict[str, object]:
    operaciones = session.scalars(
        select(OperacionInfra)
        .order_by(
            OperacionInfra.created_at.desc(),
        )
        .limit(100)
    )
    return {
        "habilitadas": settings.infra_operaciones_habilitadas,
        "produccion_habilitada": settings.infra_produccion_habilitada,
        "operaciones": [operacion_publica(o) for o in operaciones],
    }


@router.post("/versiones/{version_id}/aprobar")
def aprobar_version(
    version_id: uuid.UUID,
    datos: ValidacionVersionIn,
    session: SessionDep,
    settings: SettingsDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, object]:
    return version_publica(
        OperacionesInfraService(session, settings).aprobar_version(
            version_id,
            datos.evidencia_ci,
            auth,
            correlacion_id,
        )
    )


@router.post("/despliegues", status_code=201)
def solicitar_despliegue(
    datos: DespliegueIn,
    session: SessionDep,
    settings: SettingsDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, object]:
    return operacion_publica(
        OperacionesInfraService(session, settings).solicitar_despliegue(
            datos,
            auth,
            correlacion_id,
        )
    )


@router.post("/rollback-imagen", status_code=201)
def solicitar_rollback(
    datos: DespliegueIn,
    session: SessionDep,
    settings: SettingsDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, object]:
    return operacion_publica(
        OperacionesInfraService(session, settings).solicitar_despliegue(
            datos,
            auth,
            correlacion_id,
            "ROLLBACK_IMAGEN",
        )
    )


@router.post("/lotes", status_code=201)
def solicitar_lote(
    datos: LoteIn,
    session: SessionDep,
    settings: SettingsDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> list[dict[str, object]]:
    return [
        operacion_publica(o)
        for o in OperacionesInfraService(session, settings).solicitar_lote(
            datos,
            auth,
            correlacion_id,
        )
    ]


@router.post("/backups", status_code=201)
def solicitar_backup(
    datos: BackupIn,
    session: SessionDep,
    settings: SettingsDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, object]:
    return operacion_publica(
        OperacionesInfraService(session, settings).solicitar_backup(
            datos,
            auth,
            correlacion_id,
        )
    )


@router.get("/backups")
def listar_backups(session: SessionDep, auth: SuperadminDep) -> list[dict[str, object]]:
    return [
        {
            "id": b.id,
            "nodo_id": b.nodo_id,
            "operacion_id": b.operacion_id,
            "estado": b.estado,
            "objeto": b.objeto,
            "sha256": b.sha256,
            "bytes": b.bytes,
            "version": b.version,
            "migracion": b.migracion,
            "fecha": b.created_at,
            "retencion_dias": b.retencion_dias,
            "restauracion_verificada_at": b.restauracion_verificada_at,
        }
        for b in session.scalars(
            select(BackupInfra).order_by(BackupInfra.created_at.desc()).limit(100)
        )
    ]


@router.post("/backups/{backup_id}/restauracion-verificada")
def registrar_restauracion(
    backup_id: uuid.UUID,
    datos: RestauracionVerificadaIn,
    session: SessionDep,
    settings: SettingsDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, str]:
    backup = session.get(BackupInfra, backup_id)
    if backup is None:
        raise HTTPException(404, "Backup no encontrado")
    if backup.estado != "VERIFICADO":
        raise HTTPException(409, "El backup no tiene integridad verificada")
    backup.restauracion_verificada_at = datetime.now(UTC)
    service = OperacionesInfraService(session, settings)
    service.registrar_evento(
        auth,
        correlacion_id,
        "infra.backup.restauracion_verificada",
        backup.id,
        {
            "evidencia": datos.evidencia,
            "entorno": datos.entorno,
            "verificacion": "DECLARACION_SUPERADMIN",
        },
    )
    service.guardar()
    return {"estado": "REGISTRADO"}


@router.post("/agentes/{nodo_id}/reclamar")
def reclamar(
    session: SessionDep,
    settings: SettingsDep,
    nodo: AgenteDep,
    response: Response,
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    return {"operacion": OperacionesInfraService(session, settings).reclamar(nodo)}


@router.post("/agentes/{nodo_id}/operaciones/{operacion_id}/resultado")
def resultado(
    operacion_id: uuid.UUID,
    datos: ResultadoOperacionIn,
    session: SessionDep,
    settings: SettingsDep,
    nodo: AgenteDep,
) -> dict[str, object]:
    return operacion_publica(
        OperacionesInfraService(session, settings).resultado(nodo, operacion_id, datos)
    )


@router.get("/agentes/{nodo_id}/salud")
def salud_agente(session: SessionDep, nodo: AgenteDep, response: Response) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SET LOCAL statement_timeout = '3000ms'"))
    session.execute(text("SELECT 1"))
    migracion = None
    if inspect(session.connection()).has_table("alembic_version"):
        migracion = session.scalar(text("SELECT version_num FROM alembic_version"))
    return {"backend": "OK", "postgresql": "OK", "redis": "NO_CONFIGURADO", "migracion": migracion}
