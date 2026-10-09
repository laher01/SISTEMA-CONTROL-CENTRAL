import re
import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.codigos import codigo_automatico
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
        codigo=(
            datos.codigo.strip().upper()
            if datos.codigo
            else codigo_automatico(session, tenant_id, datos.nombre, datos.rol)
        ),
        nombre=datos.nombre.strip(),
        rol=datos.rol,
        porcentaje_produccion=(
            (
                datos.porcentaje_produccion
                if datos.porcentaje_produccion is not None
                else Decimal("1.5000")
            )
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


class AsignacionResponsableIn(BaseModel):
    responsable_id: uuid.UUID | None


@router.get("/mis-usuarios", response_model=list[MiembroOut])
def mis_usuarios_responsable(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[Miembro]:
    if auth.rol != RolMiembro.RESPONSABLE or auth.miembro_id is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el Responsable puede consultar sus Usuarios",
        )
    return list(
        session.scalars(
            select(Miembro)
            .where(
                Miembro.tenant_id == tenant_id,
                Miembro.rol == RolMiembro.USUARIO,
                Miembro.responsable_id == auth.miembro_id,
                Miembro.deleted_at.is_(None),
                Miembro.activo.is_(True),
            )
            .order_by(Miembro.codigo)
        )
    )


class AltaUsuarioResponsableIn(BaseModel):
    nombre: str
    porcentaje_produccion: Decimal | None = None
    codigo: str | None = None


class EditarUsuarioResponsableIn(BaseModel):
    nombre: str
    codigo: str
    porcentaje_produccion: Decimal


@router.post(
    "/mis-usuarios",
    response_model=AltaMiembroOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_usuario_responsable(
    datos: AltaUsuarioResponsableIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> AltaMiembroOut:
    """Un Responsable crea únicamente Usuarios de su propio equipo."""
    if auth.rol != RolMiembro.RESPONSABLE or auth.miembro_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Responsable")
    responsable = session.get(Miembro, auth.miembro_id)
    if (
        responsable is None
        or responsable.tenant_id != tenant_id
        or responsable.rol != RolMiembro.RESPONSABLE
        or not responsable.activo
        or responsable.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Responsable no habilitado")
    nombre = " ".join(datos.nombre.strip().split())
    if len(nombre) < 3 or len(nombre) > 200:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Nombre inválido")
    porcentaje = (
        datos.porcentaje_produccion
        if datos.porcentaje_produccion is not None
        else Decimal("1.5000")
    )
    if not porcentaje.is_finite() or porcentaje < 0 or porcentaje > 100:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Porcentaje inválido")
    usuario = Miembro(
        tenant_id=tenant_id,
        codigo=(validar_codigo_manual(datos.codigo) if datos.codigo is not None else codigo_automatico(session, tenant_id, nombre, RolMiembro.USUARIO)),
        nombre=nombre,
        rol=RolMiembro.USUARIO,
        responsable_id=responsable.id,
        porcentaje_produccion=porcentaje,
        activo=True,
        creado_por_cuenta_id=auth.cuenta_id,
    )
    session.add(usuario)
    try:
        session.flush()
        _, temporal = crear_o_restablecer_cuenta(
            session, tenant_id, usuario.codigo, miembro_id=usuario.id
        )
        session.commit()
    except (IntegrityError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "No se pudo crear el Usuario") from exc
    return AltaMiembroOut(
        miembro=MiembroOut.model_validate(usuario),
        credencial=CredencialTemporalOut(login=usuario.codigo, clave_temporal=temporal),
    )



def validar_codigo_manual(valor: str) -> str:
    codigo = valor.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,49}", codigo):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Código manual inválido (3-50 caracteres)")
    return codigo


@router.patch("/mis-usuarios/{usuario_id}", response_model=MiembroOut)
def editar_usuario_responsable(
    usuario_id: uuid.UUID,
    datos: EditarUsuarioResponsableIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> Miembro:
    if auth.rol != RolMiembro.RESPONSABLE or auth.miembro_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Responsable")
    usuario = session.get(Miembro, usuario_id)
    if (usuario is None or usuario.tenant_id != tenant_id
        or usuario.responsable_id != auth.miembro_id
        or usuario.rol != RolMiembro.USUARIO or usuario.deleted_at is not None):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado en tu equipo")
    nombre = " ".join(datos.nombre.split())
    if not 3 <= len(nombre) <= 200:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Nombre inválido")
    if not datos.porcentaje_produccion.is_finite() or not 0 <= datos.porcentaje_produccion <= 100:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Porcentaje inválido")
    codigo = validar_codigo_manual(datos.codigo)
    try:
        if codigo != usuario.codigo:
            actualizar_login_cuenta(session, tenant_id, codigo, miembro_id=usuario.id)
        usuario.codigo = codigo
        usuario.nombre = nombre
        usuario.porcentaje_produccion = datos.porcentaje_produccion
        session.commit()
    except (IntegrityError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Código/login ya existe") from exc
    return usuario


@router.put("/{usuario_id}/responsable", response_model=MiembroOut)
def asignar_responsable(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    usuario_id: uuid.UUID,
    datos: AsignacionResponsableIn,
) -> Miembro:
    _solo_admin(auth.rol)
    usuario = usuario_operativo(session, tenant_id, usuario_id)
    if datos.responsable_id is not None:
        responsable = session.get(Miembro, datos.responsable_id)
        if (
            responsable is None
            or responsable.tenant_id != tenant_id
            or responsable.rol != RolMiembro.RESPONSABLE
            or responsable.deleted_at is not None
            or not responsable.activo
        ):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Responsable inválido")
    usuario.responsable_id = datos.responsable_id
    session.commit()
    return usuario


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

    if miembro.rol == RolMiembro.RESPONSABLE and (
        (datos.rol is not None and datos.rol != RolMiembro.RESPONSABLE) or datos.activo is False
    ):
        asignados = session.scalar(
            select(Miembro.id).where(
                Miembro.tenant_id == tenant_id,
                Miembro.rol == RolMiembro.USUARIO,
                Miembro.responsable_id == miembro.id,
                Miembro.deleted_at.is_(None),
            )
        )
        if asignados is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Reasigne los Usuarios antes de desactivar o cambiar el rol del Responsable",
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
