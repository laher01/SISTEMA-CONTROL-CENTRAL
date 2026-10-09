"""Inventario global de espacios administrativos: exclusivo de SUPERADMIN."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import OperativeAuthDep, SessionDep
from app.enums import RolMiembro
from app.models import CuentaAcceso, Gestor, Miembro, Tenant

router = APIRouter(prefix="/configuracion/administraciones", tags=["configuracion"])


@router.get("")
def listar_administraciones(
    session: SessionDep,
    auth: OperativeAuthDep,
) -> list[dict[str, str | int]]:
    """Inventario de tenants, sin conceder acceso operativo cruzado."""
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo SUPERADMIN puede consultar tenants")
    miembros = {
        (tenant_id, rol): cantidad
        for tenant_id, rol, cantidad in session.execute(
            select(Miembro.tenant_id, Miembro.rol, func.count(Miembro.id))
            .where(Miembro.deleted_at.is_(None), Miembro.activo.is_(True))
            .group_by(Miembro.tenant_id, Miembro.rol)
        )
    }
    gestores = {
        tenant_id: cantidad
        for tenant_id, cantidad in session.execute(
            select(Gestor.tenant_id, func.count(Gestor.id))
            .where(Gestor.deleted_at.is_(None))
            .group_by(Gestor.tenant_id)
        )
    }
    cuentas = {
        tenant_id: cantidad
        for tenant_id, cantidad in session.execute(
            select(CuentaAcceso.tenant_id, func.count(CuentaAcceso.id))
            .where(CuentaAcceso.deleted_at.is_(None), CuentaAcceso.activo.is_(True))
            .group_by(CuentaAcceso.tenant_id)
        )
    }
    return [
        {
            "id": str(tenant.id),
            "nombre": tenant.nombre,
            "administradores": miembros.get((tenant.id, RolMiembro.ADMINISTRADOR), 0),
            "gerentes": miembros.get((tenant.id, RolMiembro.GERENTE), 0),
            "secretarias": miembros.get((tenant.id, RolMiembro.SECRETARIA), 0),
            "usuarios": miembros.get((tenant.id, RolMiembro.USUARIO), 0),
            "gestores": gestores.get(tenant.id, 0),
            "cuentas_activas": cuentas.get(tenant.id, 0),
            "estado_suscripcion": "NO_IMPLEMENTADO",
        }
        for tenant in session.scalars(select(Tenant).order_by(Tenant.nombre))
    ]
