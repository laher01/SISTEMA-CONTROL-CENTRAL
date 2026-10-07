from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import PermisoConfigurado
from app.schemas import PermisoConfiguradoIn, PermisoConfiguradoOut

router = APIRouter(prefix="/configuracion/permisos", tags=["configuracion"])


@router.get("", response_model=list[PermisoConfiguradoOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[PermisoConfigurado]:
    _solo_admin(auth.rol)
    return list(
        session.scalars(
            select(PermisoConfigurado)
            .where(PermisoConfigurado.tenant_id == tenant_id)
            .order_by(PermisoConfigurado.rol, PermisoConfigurado.permiso)
        )
    )


@router.put("", response_model=PermisoConfiguradoOut)
def configurar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: PermisoConfiguradoIn,
) -> PermisoConfigurado:
    _solo_admin(auth.rol)
    existente = session.scalar(
        select(PermisoConfigurado).where(
            PermisoConfigurado.tenant_id == tenant_id,
            PermisoConfigurado.rol == datos.rol,
            PermisoConfigurado.permiso == datos.permiso,
        )
    )
    if existente is None:
        existente = PermisoConfigurado(
            tenant_id=tenant_id,
            rol=datos.rol,
            permiso=datos.permiso,
            habilitado=datos.habilitado,
        )
        session.add(existente)
    else:
        existente.habilitado = datos.habilitado
    session.commit()
    return existente


def _solo_admin(rol: str) -> None:
    if rol != RolMiembro.ADMINISTRADOR:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo Administración puede cambiar permisos",
        )
