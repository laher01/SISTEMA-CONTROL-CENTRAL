import uuid

from sqlalchemy.orm import Session

from app.models import Auditoria


def registrar(
    session: Session,
    tenant_id: uuid.UUID,
    accion: str,
    entidad: str,
    entidad_id: uuid.UUID,
    datos: dict[str, object] | None = None,
) -> None:
    session.add(
        Auditoria(
            tenant_id=tenant_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            datos=datos,
        )
    )
