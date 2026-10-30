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
        # Matriz operativa fija: Gestor/User eliminan dentro de su ámbito;
        # Responsable solo solicita aprobación a Administración; Administración
        # puede eliminar en todo el tenant. Gerencia, Secretaría y Superadmin no.
        return rol in ("ADMINISTRADOR", "RESPONSABLE", "USUARIO", "GESTOR")
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
