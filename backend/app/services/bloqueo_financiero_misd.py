"""Contrato transaccional común entre liquidaciones y retirada MISD.

El lock debe adquirirse antes de leer producción, validar pagos o bloquear filas
específicas. Se mantiene hasta commit/rollback de la misma sesión.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def bloquear_tenant_financiero(session: Session, tenant_id: uuid.UUID) -> None:
    """Serializa en PostgreSQL las operaciones fiscales incompatibles de un tenant.

    No sustituye los bloqueos específicos de Gestores/Responsables ni la validación
    de pagos tras obtener el lock. Para SQLite no hay advisory locks reales.
    """
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:clave, 0))"),
            {"clave": f"fact-central:misd-liquidacion:{tenant_id}"},
        )
