"""Serializa carga, eliminación y recuperación por tenant en PostgreSQL.

El bloqueo de la fila Tenant permanece hasta COMMIT/ROLLBACK de la sesión.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tenant


def bloquear_tenant_documental(session: Session, tenant_id: uuid.UUID) -> None:
    encontrado = session.scalar(select(Tenant.id).where(Tenant.id == tenant_id).with_for_update())
    if encontrado is None:
        raise ValueError("Tenant inexistente")
