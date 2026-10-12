"""Proyección de jerarquía operativa para listados de Secretaría, sin alterar propiedad."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Documento, Expediente, Gestor, Miembro


def nombres_jerarquia(
    session: Session, tenant_id: UUID, filas: list[Documento] | list[Expediente]
) -> dict[UUID, dict[str, str | None]]:
    usuarios_ids = {f.usuario_id for f in filas if f.usuario_id is not None}
    gestores_ids = {f.gestor_id for f in filas if f.gestor_id is not None}
    usuarios = {
        u.id: u
        for u in session.scalars(
            select(Miembro).where(Miembro.tenant_id == tenant_id, Miembro.id.in_(usuarios_ids))
        )
    }
    responsables_ids = {u.responsable_id for u in usuarios.values() if u.responsable_id}
    responsables = {
        r.id: r
        for r in session.scalars(
            select(Miembro).where(Miembro.tenant_id == tenant_id, Miembro.id.in_(responsables_ids))
        )
    }
    gestores = {
        g.id: g
        for g in session.scalars(
            select(Gestor).where(Gestor.tenant_id == tenant_id, Gestor.id.in_(gestores_ids))
        )
    }
    resultado = {}
    for fila in filas:
        usuario = usuarios.get(fila.usuario_id) if fila.usuario_id is not None else None
        gestor = gestores.get(fila.gestor_id) if fila.gestor_id is not None else None
        responsable = responsables.get(usuario.responsable_id) if usuario else None
        resultado[fila.id] = {
            "responsable_nombre": responsable.nombre if responsable else None,
            "responsable_codigo": responsable.codigo if responsable else None,
            "usuario_nombre": usuario.nombre if usuario else None,
            "usuario_codigo": usuario.codigo if usuario else None,
            "gestor_nombre": gestor.nombre if gestor else None,
            "gestor_codigo": gestor.codigo if gestor else None,
        }
    return resultado
