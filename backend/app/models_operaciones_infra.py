import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, ConCreacion, ConId, JsonDict


class OperacionInfra(ConId, ConCreacion, Base):
    __tablename__ = "infra_operaciones"
    __table_args__ = (UniqueConstraint("nodo_id", "solicitud_id"),)

    nodo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("infra_nodos.id"), index=True)
    solicitud_id: Mapped[uuid.UUID]
    version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("infra_versiones.id"))
    actor_cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"))
    tipo: Mapped[str] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    grupo_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    contenido_hash: Mapped[str] = mapped_column(String(64))
    parametros: Mapped[JsonDict]
    resultado: Mapped[JsonDict | None]
    lease_hash: Mapped[str | None] = mapped_column(String(64))
    lease_hasta: Mapped[datetime | None]
    iniciada_at: Mapped[datetime | None]
    finalizada_at: Mapped[datetime | None]


class BackupInfra(ConId, ConCreacion, Base):
    __tablename__ = "infra_backups"

    nodo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("infra_nodos.id"), index=True)
    operacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("infra_operaciones.id"), unique=True)
    version: Mapped[str | None] = mapped_column(String(100))
    migracion: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str] = mapped_column(String(20))
    objeto: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64))
    bytes: Mapped[int] = mapped_column(BigInteger)
    retencion_dias: Mapped[int] = mapped_column(Integer)
    restauracion_verificada_at: Mapped[datetime | None]
