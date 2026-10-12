from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import PermisoConfigurado
from app.schemas import PermisoConfiguradoIn, PermisoConfiguradoOut

router = APIRouter(prefix="/configuracion/permisos", tags=["configuracion"])


# Visibilidad configurable de módulos de Secretaría; Expedientes siempre habilitado.
MODULOS_SECRETARIA = {
    "registros": "SECRETARIA_MENU_REGISTROS",
    "control_documental": "SECRETARIA_MENU_CONTROL_DOCUMENTAL",
    "documentos": "SECRETARIA_MENU_DOCUMENTOS",
}


@router.get("/secretaria")
def modulos_secretaria(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, bool]:
    valores = {
        fila.permiso: fila.habilitado
        for fila in session.scalars(
            select(PermisoConfigurado).where(
                PermisoConfigurado.tenant_id == tenant_id,
                PermisoConfigurado.rol == RolMiembro.SECRETARIA,
                PermisoConfigurado.permiso.in_(list(MODULOS_SECRETARIA.values())),
            )
        )
    }
    return {
        **{clave: valores.get(permiso, True) for clave, permiso in MODULOS_SECRETARIA.items()},
        "expedientes": True,
    }


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
    if rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo Administración puede cambiar permisos",
        )
