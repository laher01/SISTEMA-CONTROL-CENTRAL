"""Inventario global de espacios administrativos: exclusivo de SUPERADMIN."""

import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep
from app.enums import RolMiembro
from app.models import CuentaAcceso, Gestor, Miembro, Tenant
from app.security import crear_o_restablecer_cuenta
from app.tenant_host import validar_subdominio


class AltaAdministracionIn(BaseModel):
    nombre_administrador: str = Field(min_length=3, max_length=180)
    nombre_espacio: str = Field(min_length=3, max_length=200)
    origen: str = "SUPERADMIN"
    subdominio: str | None = Field(default=None, max_length=63)


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
            "codigo": tenant.codigo or "",
            "subdominio": tenant.subdominio or "",
            "origen": tenant.origen_alta,
            "estado": tenant.estado,
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


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_administracion(
    datos: AltaAdministracionIn,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    """Provisión única de tenant y ADMIN01; no hereda datos de tenant anterior."""
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Exclusivo de SUPERADMIN")
    if datos.origen != "SUPERADMIN":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Origen no autorizado")
    nombre = " ".join(datos.nombre_administrador.strip().upper().split())
    partes = nombre.split()
    if len(partes) < 3:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Indique tres nombres/apellidos")
    sigla = "".join(parte[0] for parte in partes[:3])
    if not re.fullmatch(r"[A-Z]{3}", sigla):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Iniciales inválidas")
    espacio = " ".join(datos.nombre_espacio.strip().split())
    if (
        session.scalar(select(Tenant.id).where(func.lower(Tenant.nombre) == espacio.lower()))
        is not None
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Nombre administrativo ya registrado")
    if (
        session.scalar(select(Tenant.id).where(func.lower(Tenant.codigo) == espacio.lower()))
        is not None
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El nombre administrativo coincide con un código de Administración",
        )

    if session.bind is not None and session.bind.dialect.name == "postgresql":
        numero = session.scalar(select(func.nextval("secuencia_administraciones")))
    else:
        codigos = session.scalars(select(Tenant.codigo).where(Tenant.codigo.is_not(None))).all()
        numeros = []
        for existente in codigos:
            if existente is None:
                continue
            coincidencia = re.fullmatch(r"[A-Z]{3}-(\d{3})-AD", existente.upper())
            if coincidencia:
                numeros.append(int(coincidencia.group(1)))
        numero = max(numeros, default=0) + 1

    if numero is None or numero > 999:
        raise HTTPException(status.HTTP_409_CONFLICT, "Numeración agotada")
    codigo = f"{sigla}-{numero:03d}-AD"
    if (
        session.scalar(select(Tenant.id).where(func.lower(Tenant.nombre) == codigo.lower()))
        is not None
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El código generado coincide con el nombre de otra Administración",
        )
    try:
        subdominio = validar_subdominio(datos.subdominio) if datos.subdominio else None
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    tenant = Tenant(
        nombre=espacio,
        codigo=codigo,
        subdominio=subdominio,
        origen_alta="SUPERADMIN",
        estado="ACTIVO",
    )
    session.add(tenant)
    try:
        session.flush()
        administrador = Miembro(
            tenant_id=tenant.id,
            codigo="ADMIN01",
            nombre=nombre,
            rol=RolMiembro.ADMINISTRADOR,
            activo=True,
            creado_por_cuenta_id=None,
        )
        session.add(administrador)
        session.flush()
        _, temporal = crear_o_restablecer_cuenta(
            session, tenant.id, administrador.codigo, miembro_id=administrador.id
        )
        session.commit()
    except (IntegrityError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "No se pudo crear la Administración") from exc
    return {
        "tenant_id": str(tenant.id),
        "codigo": codigo,
        "nombre": tenant.nombre,
        "subdominio": tenant.subdominio or "",
        "login": administrador.codigo,
        "clave_temporal": temporal,
        "origen": "SUPERADMIN",
    }
