import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.security import ContextoAcceso, contexto_desde_token
from app.storage import AlmacenLocal

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
    session.commit()
    return contexto


def get_contexto_operativo(contexto: Annotated[ContextoAcceso, Depends(get_contexto_actual)]) -> ContextoAcceso:
    if contexto.cambio_clave_obligatorio:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Debe cambiar la clave temporal antes de continuar",
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
