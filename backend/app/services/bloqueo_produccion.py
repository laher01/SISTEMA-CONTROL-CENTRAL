"""Compatibilidad MISD: un único bloqueo compartido para pagos y retiradas.

Toda ruta debe tomar el mismo bloqueo ANTES de leer producción y mantener
la transacción hasta commit/rollback. No combina FOR UPDATE con advisory locks.
"""

import uuid

from sqlalchemy.orm import Session

from app.services.bloqueo_financiero_misd import bloquear_tenant_financiero


def bloquear_tenant_para_produccion(session: Session, tenant_id: uuid.UUID) -> None:
    """Alias compatible con el contrato transaccional financiero MISD.

    El aislamiento real se comprueba en PostgreSQL. Este alias evita que
    consumidores antiguos adquieran una primitiva incompatible.
    """
    bloquear_tenant_financiero(session, tenant_id)
