from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import SessionDep, TenantDep
from app.enums import TipoAlerta
from app.models import Alerta
from app.schemas import AlertaOut

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.get("", response_model=list[AlertaOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    resuelta: bool = False,
    tipo: TipoAlerta | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Alerta]:
    consulta = select(Alerta).where(Alerta.tenant_id == tenant_id, Alerta.resuelta == resuelta)
    if tipo is not None:
        consulta = consulta.where(Alerta.tipo == tipo)
    consulta = consulta.order_by(Alerta.created_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(consulta))
