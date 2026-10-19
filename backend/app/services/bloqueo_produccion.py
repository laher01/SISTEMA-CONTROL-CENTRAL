"""Primitiva de bloqueo del contrato MISD / liquidaciones.

Ninguna ruta está protegida hasta que TODOS los productores de pagos y retiros
adquieran este bloqueo antes de consultar elegibilidad. No llamar fuera de transacción.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tenant


def bloquear_tenant_para_produccion(session: Session, tenant_id: uuid.UUID) -> None:
    """Serializa mutaciones de producción por tenant en PostgreSQL.

    El bloqueo vive hasta COMMIT o ROLLBACK. SQLite no implementa FOR UPDATE:
    los ensayos de concurrencia deben ejecutarse con PostgreSQL.
    """
    encontrado = session.scalar(select(Tenant.id).where(Tenant.id == tenant_id).with_for_update())
    if encontrado is None:
        raise ValueError("Tenant inexistente para bloqueo transaccional")
