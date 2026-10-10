"""Acceso compatible a expedientes anteriores a la atribución gerencial.

GRTEGLOBAL mantiene consulta de expedientes históricos aún sin gerente.
No concede acceso a los expedientes asignados a otras gerencias.
"""

from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.models import Expediente
from app.security import ContextoAcceso


def alcance_expedientes_gerente(auth: ContextoAcceso) -> ColumnElement[bool]:
    if auth.codigo == "GRTEGLOBAL":
        return or_(
            Expediente.gerente_id == auth.miembro_id,
            Expediente.gerente_id.is_(None),
        )
    return Expediente.gerente_id == auth.miembro_id


def expediente_visible_gerente(expediente: Expediente, auth: ContextoAcceso) -> bool:
    return expediente.gerente_id == auth.miembro_id or (
        auth.codigo == "GRTEGLOBAL" and expediente.gerente_id is None
    )
