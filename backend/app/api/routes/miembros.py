import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import Miembro
from app.schemas import MiembroActualizar, MiembroIn, MiembroOut

router = APIRouter(prefix="/miembros", tags=["miembros"])


@router.post("", response_model=MiembroOut, status_code=status.HTTP_201_CREATED)
def crear(session: SessionDep, tenant_id: TenantDep, datos: MiembroIn) -> Miembro:
    miembro = Miembro(
        tenant_id=tenant_id,
        codigo=datos.codigo.strip().upper(),
        nombre=datos.nombre.strip(),
        rol=datos.rol,
    )
    session.add(miembro)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código del miembro ya existe") from exc
    return miembro


@router.get("", response_model=list[MiembroOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    rol: RolMiembro | None = None,
) -> list[Miembro]:
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
    miembro_id: uuid.UUID,
    datos: MiembroActualizar,
) -> Miembro:
    miembro = session.get(Miembro, miembro_id)
    if miembro is None or miembro.tenant_id != tenant_id or miembro.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Miembro no encontrado")

    if datos.codigo is not None:
        miembro.codigo = datos.codigo.strip().upper()
    if datos.nombre is not None:
        miembro.nombre = datos.nombre.strip()
    if datos.rol is not None:
        miembro.rol = datos.rol
    if datos.activo is not None:
        miembro.activo = datos.activo

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código del miembro ya existe") from exc
    return miembro
