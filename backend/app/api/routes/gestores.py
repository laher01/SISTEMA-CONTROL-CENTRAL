from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, TenantDep
from app.models import Gestor
from app.schemas import GestorIn, GestorOut

router = APIRouter(prefix="/gestores", tags=["gestores"])


@router.post("", response_model=GestorOut, status_code=status.HTTP_201_CREATED)
def crear(session: SessionDep, tenant_id: TenantDep, datos: GestorIn) -> Gestor:
    gestor = Gestor(tenant_id=tenant_id, codigo=datos.codigo, nombre=datos.nombre)
    session.add(gestor)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código de gestor ya existe") from exc
    return gestor


@router.get("", response_model=list[GestorOut])
def listar(session: SessionDep, tenant_id: TenantDep) -> list[Gestor]:
    consulta = select(Gestor).where(Gestor.tenant_id == tenant_id, Gestor.deleted_at.is_(None))
    return list(session.scalars(consulta.order_by(Gestor.codigo)))
