import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.security import ContextoAcceso, contexto_desde_token
from app.storage import AlmacenLocal
from app.tenant_host import validar_sesion_host

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_hoy(settings: SettingsDep) -> date:
    return settings.hoy()


def get_almacen(settings: SettingsDep) -> AlmacenLocal:
    return AlmacenLocal(settings.storage_dir)


def get_contexto_actual(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
) -> ContextoAcceso:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Debe iniciar sesión")
    contexto = contexto_desde_token(session, token)
    if contexto is None:
        session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o vencida")
    validar_sesion_host(request, session, settings, contexto.tenant_id)
    session.commit()
    return contexto


def get_contexto_operativo(
    request: Request,
    contexto: Annotated[ContextoAcceso, Depends(get_contexto_actual)],
) -> ContextoAcceso:
    if contexto.cambio_clave_obligatorio:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Debe cambiar la clave temporal antes de continuar",
        )
    permitido_responsable = (
        (
            request.method == "PATCH"
            and request.url.path.startswith("/api/v1/miembros/mis-usuarios/")
            and request.url.path.endswith("/porcentajes")
        )
        or (
            request.method in {"GET", "POST"}
            and request.url.path == "/api/v1/miembros/mis-usuarios"
        )
        or (request.method == "POST" and request.url.path == "/api/v1/comisiones/simular")
        or (request.method == "GET" and request.url.path == "/api/v1/comisiones/receptores")
        or (request.method == "GET" and request.url.path == "/api/v1/responsable/resumen")
        or (request.method == "GET" and request.url.path == "/api/v1/gerencias/vinculos")
        or (
            request.method == "POST"
            and request.url.path
            in {
                "/api/v1/responsable/pagos/cotizar",
                "/api/v1/responsable/pagos/programar",
            }
        )
        or (
            request.method == "DELETE" and request.url.path.startswith("/api/v1/responsable/pagos/")
        )
        or (
            request.method == "POST"
            and request.url.path.startswith("/api/v1/responsable/pedidos/")
            and request.url.path.endswith("/distribuir")
        )
    )
    if contexto.rol == "RESPONSABLE" and not permitido_responsable:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El rol Responsable solo tiene habilitada su cartera de Usuarios en esta etapa",
        )
    return contexto


def get_tenant_id(
    contexto: Annotated[ContextoAcceso, Depends(get_contexto_operativo)],
) -> uuid.UUID:
    return contexto.tenant_id


HoyDep = Annotated[date, Depends(get_hoy)]
AlmacenDep = Annotated[AlmacenLocal, Depends(get_almacen)]
AuthDep = Annotated[ContextoAcceso, Depends(get_contexto_actual)]
OperativeAuthDep = Annotated[ContextoAcceso, Depends(get_contexto_operativo)]
TenantDep = Annotated[uuid.UUID, Depends(get_tenant_id)]
