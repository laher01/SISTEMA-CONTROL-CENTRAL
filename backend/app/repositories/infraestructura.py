import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_infraestructura import (
    EventoInfraestructura,
    NodoInfraestructura,
    ReporteNodo,
    TenantNodo,
    VersionInfraestructura,
)


class InfraestructuraRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def nodos(self, limite: int = 200, offset: int = 0) -> list[NodoInfraestructura]:
        return list(
            self.session.scalars(
                select(NodoInfraestructura)
                .order_by(NodoInfraestructura.codigo)
                .offset(offset)
                .limit(limite)
            )
        )

    def nodo(self, nodo_id: uuid.UUID) -> NodoInfraestructura | None:
        return self.session.get(NodoInfraestructura, nodo_id)

    def ultimo_reporte(self, nodo_id: uuid.UUID) -> ReporteNodo | None:
        return self.session.scalar(
            select(ReporteNodo)
            .where(ReporteNodo.nodo_id == nodo_id)
            .order_by(ReporteNodo.created_at.desc(), ReporteNodo.id.desc())
            .limit(1)
        )

    def reporte(self, nodo_id: uuid.UUID, reporte_id: uuid.UUID) -> ReporteNodo | None:
        return self.session.scalar(
            select(ReporteNodo).where(
                ReporteNodo.nodo_id == nodo_id, ReporteNodo.reporte_id == reporte_id
            )
        )

    def versiones(self, limite: int = 100) -> list[VersionInfraestructura]:
        return list(
            self.session.scalars(
                select(VersionInfraestructura)
                .order_by(VersionInfraestructura.created_at.desc())
                .limit(limite)
            )
        )

    def asociaciones(self, nodo_id: uuid.UUID) -> list[TenantNodo]:
        return list(self.session.scalars(select(TenantNodo).where(TenantNodo.nodo_id == nodo_id)))

    def eventos(self, limite: int = 100) -> list[EventoInfraestructura]:
        return list(
            self.session.scalars(
                select(EventoInfraestructura)
                .order_by(EventoInfraestructura.created_at.desc())
                .limit(limite)
            )
        )
