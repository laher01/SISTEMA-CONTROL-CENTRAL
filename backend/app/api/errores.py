import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Gestor


def no_encontrado(entidad: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{entidad} no encontrado")


def validar_gestor(session: Session, tenant_id: uuid.UUID, gestor_id: uuid.UUID | None) -> None:
    if gestor_id is None:
        return
    gestor = session.get(Gestor, gestor_id)
    if gestor is None or gestor.tenant_id != tenant_id or gestor.deleted_at is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Gestor inválido")
