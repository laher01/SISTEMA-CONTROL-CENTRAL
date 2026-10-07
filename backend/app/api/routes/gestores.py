import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import Gestor, Miembro
from app.schemas import GestorActualizar, GestorIn, GestorOut

router = APIRouter(prefix="/gestores", tags=["gestores"])


@router.post("", response_model=GestorOut, status_code=status.HTTP_201_CREATED)
def crear(session: SessionDep, tenant_id: TenantDep, datos: GestorIn) -> Gestor:
    usuario = session.get(Miembro, datos.usuario_id)
    if (
        usuario is None
        or usuario.tenant_id != tenant_id
        or usuario.deleted_at is not None
        or not usuario.activo
        or usuario.rol != RolMiembro.USUARIO
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Usuario operativo inválido")
    gestor = Gestor(
        tenant_id=tenant_id,
        codigo=datos.codigo.strip().upper(),
        nombre=datos.nombre.strip(),
        usuario_id=usuario.id,
    )
    session.add(gestor)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código de gestor ya existe") from exc
    return gestor


@router.get("", response_model=list[GestorOut])
def listar(
    session: SessionDep, tenant_id: TenantDep, usuario_id: uuid.UUID | None = None
) -> list[Gestor]:
    consulta = select(Gestor).where(Gestor.tenant_id == tenant_id, Gestor.deleted_at.is_(None))
    if usuario_id is not None:
        consulta = consulta.where(Gestor.usuario_id == usuario_id)
    return list(session.scalars(consulta.order_by(Gestor.codigo)))


@router.patch("/{gestor_id}", response_model=GestorOut)
def actualizar(
    session: SessionDep,
    tenant_id: TenantDep,
    gestor_id: uuid.UUID,
    datos: GestorActualizar,
) -> Gestor:
    gestor = session.get(Gestor, gestor_id)
    if gestor is None or gestor.tenant_id != tenant_id or gestor.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gestor no encontrado")

    if datos.usuario_id is not None:
        usuario = session.get(Miembro, datos.usuario_id)
        if (
            usuario is None
            or usuario.tenant_id != tenant_id
            or usuario.deleted_at is not None
            or not usuario.activo
            or usuario.rol != RolMiembro.USUARIO
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Usuario operativo inválido",
            )
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
