import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PermisoConfigurado

PERMISO_ELIMINAR_REGISTROS = "ELIMINAR_REGISTROS"


def permiso_habilitado(
    session: Session,
    tenant_id: uuid.UUID,
    rol: str,
    permiso: str,
) -> bool:
    if permiso == PERMISO_ELIMINAR_REGISTROS and rol in ("ADMINISTRADOR", "GESTOR"):
        return True
    configurado = session.scalar(
        select(PermisoConfigurado).where(
            PermisoConfigurado.tenant_id == tenant_id,
            PermisoConfigurado.rol == rol,
            PermisoConfigurado.permiso == permiso,
            PermisoConfigurado.habilitado.is_(True),
        )
    )
    return configurado is not None
