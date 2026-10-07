import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import Gestor, Miembro
from app.schemas import (
    AltaGestorOut,
    CredencialTemporalOut,
    GestorActualizar,
    GestorIn,
    GestorOut,
)
from app.security import crear_o_restablecer_cuenta

router = APIRouter(prefix="/gestores", tags=["gestores"])


@router.post("", response_model=AltaGestorOut, status_code=status.HTTP_201_CREATED)
def crear(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: GestorIn,
) -> AltaGestorOut:
    usuario_id = _usuario_objetivo(auth, datos.usuario_id)
    usuario = _usuario_valido(session, tenant_id, usuario_id)
    gestor = Gestor(
        tenant_id=tenant_id,
        codigo=datos.codigo.strip().upper(),
        nombre=datos.nombre.strip(),
        usuario_id=usuario.id,
    )
    session.add(gestor)
    try:
        session.flush()
        _, temporal = crear_o_restablecer_cuenta(
            session,
            tenant_id,
            gestor.codigo,
            gestor_id=gestor.id,
        )
        session.commit()
    except (IntegrityError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código/login de gestor ya existe") from exc
    return AltaGestorOut(
        gestor=GestorOut.model_validate(gestor),
        credencial=CredencialTemporalOut(login=gestor.codigo, clave_temporal=temporal),
    )


@router.get("", response_model=list[GestorOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    usuario_id: uuid.UUID | None = None,
) -> list[Gestor]:
    if auth.rol not in (RolMiembro.ADMINISTRADOR, RolMiembro.USUARIO):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para consultar Gestores")

    consulta = select(Gestor).where(
        Gestor.tenant_id == tenant_id,
        Gestor.deleted_at.is_(None),
    )
    if auth.rol == RolMiembro.USUARIO:
        if auth.usuario_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario sin ámbito operativo")
        consulta = consulta.where(Gestor.usuario_id == auth.usuario_id)
    elif usuario_id is not None:
        consulta = consulta.where(Gestor.usuario_id == usuario_id)
    return list(session.scalars(consulta.order_by(Gestor.codigo)))


@router.patch("/{gestor_id}", response_model=GestorOut)
def actualizar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    gestor_id: uuid.UUID,
    datos: GestorActualizar,
) -> Gestor:
    gestor = _gestor_editable(session, tenant_id, auth, gestor_id)

    if datos.usuario_id is not None:
        if auth.rol != RolMiembro.ADMINISTRADOR:
            if datos.usuario_id != auth.usuario_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Un Usuario no puede reasignar su Gestor a otro Usuario",
                )
        usuario = _usuario_valido(session, tenant_id, datos.usuario_id)
        gestor.usuario_id = usuario.id
    if datos.codigo is not None:
        gestor.codigo = datos.codigo.strip().upper()
    if datos.nombre is not None:
        gestor.nombre = datos.nombre.strip()

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código de gestor ya existe") from exc
    return gestor


@router.post("/{gestor_id}/restablecer-acceso", response_model=CredencialTemporalOut)
def restablecer_acceso(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    gestor_id: uuid.UUID,
) -> CredencialTemporalOut:
    gestor = _gestor_editable(session, tenant_id, auth, gestor_id)
    try:
        _, temporal = crear_o_restablecer_cuenta(
            session,
            tenant_id,
            gestor.codigo,
            gestor_id=gestor.id,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return CredencialTemporalOut(login=gestor.codigo, clave_temporal=temporal)


def _usuario_objetivo(auth: OperativeAuthDep, solicitado: uuid.UUID) -> uuid.UUID:
    if auth.rol == RolMiembro.ADMINISTRADOR:
        return solicitado
    if auth.rol == RolMiembro.USUARIO and auth.usuario_id is not None:
        return auth.usuario_id
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración o Usuario puede crear Gestores")


def _usuario_valido(session: SessionDep, tenant_id: uuid.UUID, usuario_id: uuid.UUID) -> Miembro:
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


def _gestor_editable(
    session: SessionDep,
    tenant_id: uuid.UUID,
    auth: OperativeAuthDep,
    gestor_id: uuid.UUID,
) -> Gestor:
    gestor = session.get(Gestor, gestor_id)
    if gestor is None or gestor.tenant_id != tenant_id or gestor.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gestor no encontrado")
    if auth.rol == RolMiembro.ADMINISTRADOR:
        return gestor
    if auth.rol == RolMiembro.USUARIO and gestor.usuario_id == auth.usuario_id:
        return gestor
    raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede administrar este Gestor")
