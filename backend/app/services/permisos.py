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
    if permiso == PERMISO_ELIMINAR_REGISTROS:
        # La política MISD nunca concede retiro a roles técnicos o Secretaría.
        if rol in ("SUPERADMIN", "SECRETARIA"):
            return False
        if rol in ("ADMINISTRADOR", "GERENTE", "RESPONSABLE", "USUARIO", "GESTOR"):
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


def requiere_autorizacion_administrativa(rol: str, receptor_autorizado: bool) -> bool:
    """Los expedientes con receptor autorizado no se retiran por roles delegados."""
    return rol != "ADMINISTRADOR" and receptor_autorizado
