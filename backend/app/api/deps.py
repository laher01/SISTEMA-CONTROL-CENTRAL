import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.services.expedientes import obtener_tenant
from app.storage import AlmacenLocal

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_hoy(settings: SettingsDep) -> date:
    return settings.hoy()


def get_almacen(settings: SettingsDep) -> AlmacenLocal:
    return AlmacenLocal(settings.storage_dir)


def get_tenant_id(session: SessionDep, settings: SettingsDep) -> uuid.UUID:
    tenant = obtener_tenant(session, settings.tenant_default)
    session.commit()
    return tenant.id


HoyDep = Annotated[date, Depends(get_hoy)]
AlmacenDep = Annotated[AlmacenLocal, Depends(get_almacen)]
TenantDep = Annotated[uuid.UUID, Depends(get_tenant_id)]
