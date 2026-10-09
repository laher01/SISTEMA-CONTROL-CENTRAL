import uuid
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import OperativeAuthDep, SessionDep, SettingsDep
from app.enums import RolMiembro
from app.models_infraestructura import NodoInfraestructura, VersionInfraestructura
from app.schemas_infraestructura import NodoIn, ReporteIn, TenantNodoIn, VersionIn
from app.security import ContextoAcceso
from app.services.infraestructura import InfraestructuraService, en_utc

router = APIRouter(prefix="/infraestructura", tags=["infraestructura"])
bearer = HTTPBearer(auto_error=False)


def superadmin(auth: OperativeAuthDep, request: Request, settings: SettingsDep) -> ContextoAcceso:
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(403, "Infraestructura es exclusiva de SUPERADMIN")
    if request.method not in {"GET", "HEAD"}:
        origin = request.headers.get("origin")
        if origin:
            partes = urlsplit(origin)
            actual = urlsplit(str(request.base_url))
            if (partes.scheme, partes.netloc) != (
                actual.scheme,
                actual.netloc,
            ) and origin not in settings.cors_origins:
                raise HTTPException(403, "Origen no autorizado")
    return auth


def correlacion(
    response: Response,
    valor: Annotated[uuid.UUID | None, Header(alias="X-Correlation-ID")] = None,
) -> uuid.UUID:
    identificador = valor or uuid.uuid4()
    response.headers["X-Correlation-ID"] = str(identificador)
    response.headers["Cache-Control"] = "no-store"
    return identificador


SuperadminDep = Annotated[ContextoAcceso, Depends(superadmin)]
CorrelacionDep = Annotated[uuid.UUID, Depends(correlacion)]


def agente(
    nodo_id: uuid.UUID,
    session: SessionDep,
    credencial: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> NodoInfraestructura:
    if credencial is None:
        raise HTTPException(401, "Se requiere credencial de agente")
    return InfraestructuraService(session).autenticar_agente(nodo_id, credencial.credentials)


AgenteDep = Annotated[NodoInfraestructura, Depends(agente)]


@router.get("/nodos")
def listar_nodos(
    session: SessionDep,
    auth: SuperadminDep,
    settings: SettingsDep,
    limite: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, object]]:
    service = InfraestructuraService(session)
    return [service.resumen_nodo(n, settings) for n in service.repository.nodos(limite, offset)]


@router.post("/nodos", status_code=201)
def crear_nodo(
    datos: NodoIn,
    session: SessionDep,
    auth: SuperadminDep,
    settings: SettingsDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, object]:
    service = InfraestructuraService(session)
    nodo = service.crear_nodo(datos, auth, correlacion_id)
    return service.resumen_nodo(nodo, settings)


@router.put("/nodos/{nodo_id}")
def actualizar_nodo(
    nodo_id: uuid.UUID,
    datos: NodoIn,
    session: SessionDep,
    auth: SuperadminDep,
    settings: SettingsDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, object]:
    service = InfraestructuraService(session)
    nodo = service.actualizar_nodo(nodo_id, datos, auth, correlacion_id)
    return service.resumen_nodo(nodo, settings)


@router.delete("/nodos/{nodo_id}", status_code=204)
def desactivar_nodo(
    nodo_id: uuid.UUID,
    session: SessionDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> None:
    InfraestructuraService(session).desactivar_nodo(nodo_id, auth, correlacion_id)


@router.post("/nodos/{nodo_id}/credencial")
def rotar_credencial(
    nodo_id: uuid.UUID,
    session: SessionDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, str]:
    token = InfraestructuraService(session).rotar_token(nodo_id, auth, correlacion_id)
    return {"token": token}


@router.post("/agentes/{nodo_id}/reportes")
def reportar(
    datos: ReporteIn,
    session: SessionDep,
    nodo: AgenteDep,
) -> dict[str, object]:
    reporte = InfraestructuraService(session).reportar(nodo, datos)
    return {
        "id": reporte.id,
        "reporte_id": reporte.reporte_id,
        "recibido_at": en_utc(reporte.created_at),
    }


@router.get("/dashboard")
def dashboard(
    session: SessionDep,
    auth: SuperadminDep,
    settings: SettingsDep,
) -> dict[str, object]:
    return InfraestructuraService(session).dashboard(settings)


def version_publica(version: VersionInfraestructura) -> dict[str, object]:
    return {
        "id": version.id,
        "version": version.version,
        "commit_git": version.commit_git,
        "imagen_docker": version.imagen_docker,
        "digest": version.digest,
        "construida_at": version.construida_at,
        "entorno": version.entorno,
        "validacion": version.validacion,
        "aprobacion": version.aprobacion,
        "migracion_desde": version.migracion_desde,
        "migracion_hasta": version.migracion_hasta,
        "migracion_reversible": version.migracion_reversible,
    }


@router.get("/versiones")
def listar_versiones(session: SessionDep, auth: SuperadminDep) -> list[dict[str, object]]:
    return [version_publica(v) for v in InfraestructuraService(session).repository.versiones()]


@router.post("/versiones", status_code=201)
def registrar_version(
    datos: VersionIn,
    session: SessionDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, object]:
    return version_publica(
        InfraestructuraService(session).crear_version(datos, auth, correlacion_id)
    )


@router.post("/asociaciones", status_code=201)
def asociar_tenant(
    datos: TenantNodoIn,
    session: SessionDep,
    auth: SuperadminDep,
    correlacion_id: CorrelacionDep,
) -> dict[str, object]:
    asociacion = InfraestructuraService(session).asociar_tenant(datos, auth, correlacion_id)
    return {"id": asociacion.id, "tenant_id": asociacion.tenant_id, "nodo_id": asociacion.nodo_id}


@router.get("/eventos")
def listar_eventos(session: SessionDep, auth: SuperadminDep) -> list[dict[str, object]]:
    return [
        {
            "id": e.id,
            "actor_cuenta_id": e.actor_cuenta_id,
            "correlacion_id": e.correlacion_id,
            "accion": e.accion,
            "recurso_id": e.recurso_id,
            "resultado": e.resultado,
            "fecha": e.created_at,
            "datos": e.datos,
        }
        for e in InfraestructuraService(session).repository.eventos()
    ]


@router.get("/salud")
def salud(session: SessionDep, auth: SuperadminDep, response: Response) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    try:
        if session.get_bind().dialect.name == "postgresql":
            session.execute(text("SET LOCAL statement_timeout = '3000ms'"))
        session.execute(text("SELECT 1"))
        db = "OK"
    except SQLAlchemyError:
        session.rollback()
        db = "FALLO"
        response.status_code = 503
    return {"backend": "OK", "base_datos": db, "redis": "NO_CONFIGURADO"}
