import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import Gestor, Miembro
from app.schemas import (
    AltaMiembroOut,
    CredencialTemporalOut,
    MiembroActualizar,
    MiembroIn,
    MiembroOut,
)
from app.security import actualizar_login_cuenta, crear_o_restablecer_cuenta

router = APIRouter(prefix="/miembros", tags=["miembros"])


@router.post("", response_model=AltaMiembroOut, status_code=status.HTTP_201_CREATED)
def crear(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: MiembroIn,
) -> AltaMiembroOut:
    _solo_admin(auth.rol)
    if datos.rol == RolMiembro.SUPERADMIN and auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo SUPERADMIN puede crear otro SUPERADMIN",
        )
    miembro = Miembro(
        tenant_id=tenant_id,
        codigo=datos.codigo.strip().upper(),
        nombre=datos.nombre.strip(),
        rol=datos.rol,
        porcentaje_produccion=(
            (datos.porcentaje_produccion or Decimal("1.5000"))
            if datos.rol == RolMiembro.USUARIO
            else None
        ),
        creado_por_cuenta_id=auth.cuenta_id,
    )
    session.add(miembro)
    try:
        session.flush()
        _, temporal = crear_o_restablecer_cuenta(
            session,
            tenant_id,
            miembro.codigo,
            miembro_id=miembro.id,
        )
        session.commit()
    except (IntegrityError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código/login ya existe") from exc
    return AltaMiembroOut(
        miembro=MiembroOut.model_validate(miembro),
        credencial=CredencialTemporalOut(login=miembro.codigo, clave_temporal=temporal),
    )


@router.get("", response_model=list[MiembroOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    rol: RolMiembro | None = None,
) -> list[Miembro]:
    _solo_admin(auth.rol)
    consulta = select(Miembro).where(
        Miembro.tenant_id == tenant_id,
        Miembro.deleted_at.is_(None),
        Miembro.activo.is_(True),
    )
    if rol is not None:
        consulta = consulta.where(Miembro.rol == rol)
    return list(session.scalars(consulta.order_by(Miembro.rol, Miembro.codigo)))


def usuario_operativo(session: SessionDep, tenant_id: uuid.UUID, usuario_id: uuid.UUID) -> Miembro:
    usuario = session.get(Miembro, usuario_id)
    if (
        usuario is None
        or usuario.tenant_id != tenant_id
        or usuario.deleted_at is not None
        or not usuario.activo
        or usuario.rol != RolMiembro.USUARIO
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Usuario operativo inválido")
    return usuario


@router.patch("/{miembro_id}", response_model=MiembroOut)
def actualizar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    miembro_id: uuid.UUID,
    datos: MiembroActualizar,
) -> Miembro:
    _solo_admin(auth.rol)
    miembro = session.get(Miembro, miembro_id)
    if miembro is None or miembro.tenant_id != tenant_id or miembro.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Miembro no encontrado")
    if auth.rol != RolMiembro.SUPERADMIN and (
        miembro.rol == RolMiembro.SUPERADMIN or datos.rol == RolMiembro.SUPERADMIN
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo SUPERADMIN puede modificar cuentas SUPERADMIN",
        )

    quedaria_usuario = datos.rol is None or datos.rol == RolMiembro.USUARIO
    quedaria_activo = datos.activo is None or datos.activo
    if miembro.rol == RolMiembro.USUARIO and (not quedaria_usuario or not quedaria_activo):
        tiene_gestores = session.scalar(
            select(Gestor.id).where(
                Gestor.tenant_id == tenant_id,
                Gestor.usuario_id == miembro.id,
                Gestor.deleted_at.is_(None),
            )
        )
        if tiene_gestores is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Reasigne los gestores antes de cambiar el rol o desactivar al Usuario",
            )

    try:
        if datos.codigo is not None:
            actualizar_login_cuenta(
                session,
                tenant_id,
                datos.codigo,
                miembro_id=miembro.id,
            )
            miembro.codigo = datos.codigo.strip().upper()
        if datos.nombre is not None:
            miembro.nombre = datos.nombre.strip()
        if datos.rol is not None:
            miembro.rol = datos.rol
        if "porcentaje_produccion" in datos.model_fields_set:
            miembro.porcentaje_produccion = (
                datos.porcentaje_produccion
                if (datos.rol or miembro.rol) == RolMiembro.USUARIO
                else None
            )
        if miembro.rol == RolMiembro.USUARIO and miembro.porcentaje_produccion is None:
            miembro.porcentaje_produccion = Decimal("1.5000")
        elif miembro.rol != RolMiembro.USUARIO:
            miembro.porcentaje_produccion = None
        if datos.activo is not None:
            miembro.activo = datos.activo
        session.commit()
    except (IntegrityError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El código/login del miembro ya existe",
        ) from exc
    return miembro


@router.post("/{miembro_id}/restablecer-acceso", response_model=CredencialTemporalOut)
def restablecer_acceso(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    miembro_id: uuid.UUID,
) -> CredencialTemporalOut:
    _solo_admin(auth.rol)
    miembro = session.get(Miembro, miembro_id)
    if miembro is None or miembro.tenant_id != tenant_id or miembro.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Miembro no encontrado")
    if miembro.rol == RolMiembro.SUPERADMIN and auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo SUPERADMIN puede restablecer otro SUPERADMIN",
        )
    try:
        _, temporal = crear_o_restablecer_cuenta(
            session,
            tenant_id,
            miembro.codigo,
            miembro_id=miembro.id,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return CredencialTemporalOut(login=miembro.codigo, clave_temporal=temporal)


def _solo_admin(rol: str) -> None:
    if rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo Administración puede realizar esta acción",
        )
