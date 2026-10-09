"""Plano de infraestructura global; no contiene datos operativos de empresas."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, ConCreacion, ConId, JsonDict


class NodoInfraestructura(ConId, ConCreacion, Base):
    __tablename__ = "infra_nodos"

    codigo: Mapped[str] = mapped_column(String(60), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    hostname: Mapped[str] = mapped_column(String(253))
    endpoint_privado: Mapped[str] = mapped_column(String(500))
    proveedor: Mapped[str] = mapped_column(String(80))
    region: Mapped[str] = mapped_column(String(80))
    sistema_operativo: Mapped[str] = mapped_column(String(100))
    entorno: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(default=True)
    cpu_nucleos: Mapped[int | None] = mapped_column(Integer)
    ram_bytes: Mapped[int | None] = mapped_column(BigInteger)
    disco_bytes: Mapped[int | None] = mapped_column(BigInteger)
    token_hash: Mapped[str | None] = mapped_column(String(64))
    ultima_conexion: Mapped[datetime | None]
    version_instalada: Mapped[str | None] = mapped_column(String(100))
    migracion_instalada: Mapped[str | None] = mapped_column(String(100))
    ultimo_despliegue: Mapped[datetime | None]


class ReporteNodo(ConId, ConCreacion, Base):
    __tablename__ = "infra_reportes"
    __table_args__ = (UniqueConstraint("nodo_id", "reporte_id"),)

    nodo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("infra_nodos.id"), index=True)
    reporte_id: Mapped[uuid.UUID]
    contenido_hash: Mapped[str] = mapped_column(String(64))
    cpu_porcentaje: Mapped[float | None] = mapped_column(Float)
    ram_porcentaje: Mapped[float | None] = mapped_column(Float)
    disco_porcentaje: Mapped[float | None] = mapped_column(Float)
    servicios: Mapped[JsonDict]
    version: Mapped[str | None] = mapped_column(String(100))
    migracion: Mapped[str | None] = mapped_column(String(100))


class VersionInfraestructura(ConId, ConCreacion, Base):
    __tablename__ = "infra_versiones"
    __table_args__ = (UniqueConstraint("version", "entorno"),)

    version: Mapped[str] = mapped_column(String(100))
    commit_git: Mapped[str] = mapped_column(String(40))
    imagen_docker: Mapped[str] = mapped_column(String(300))
    digest: Mapped[str] = mapped_column(String(71))
    imagen_frontend: Mapped[str | None] = mapped_column(String(300))
    digest_frontend: Mapped[str | None] = mapped_column(String(71))
    construida_at: Mapped[datetime]
    entorno: Mapped[str] = mapped_column(String(20))
    validacion: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    aprobacion: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    migracion_desde: Mapped[str] = mapped_column(String(100))
    migracion_hasta: Mapped[str] = mapped_column(String(100))
    migracion_reversible: Mapped[bool] = mapped_column(default=False)


class TenantNodo(ConId, ConCreacion, Base):
    __tablename__ = "infra_tenant_nodo"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), unique=True)
    nodo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("infra_nodos.id"), index=True)


class EventoInfraestructura(ConId, ConCreacion, Base):
    __tablename__ = "infra_eventos"

    actor_cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"))
    correlacion_id: Mapped[uuid.UUID]
    accion: Mapped[str] = mapped_column(String(80))
    recurso_id: Mapped[uuid.UUID] = mapped_column(index=True)
    resultado: Mapped[str] = mapped_column(String(20))
    datos: Mapped[JsonDict]
