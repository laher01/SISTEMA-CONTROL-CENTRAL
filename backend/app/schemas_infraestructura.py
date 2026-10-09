import re
import uuid
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

EntornoInfra = Literal["development", "staging", "canary", "production"]
EstadoServicio = Literal["OK", "FALLO", "NO_CONFIGURADO"]


class ContratoInfra(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NodoIn(ContratoInfra):
    codigo: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9_-]+$")
    nombre: str = Field(min_length=1, max_length=200)
    hostname: str = Field(min_length=1, max_length=253)
    endpoint_privado: str = Field(min_length=1, max_length=500)
    proveedor: str = Field(min_length=1, max_length=80)
    region: str = Field(min_length=1, max_length=80)
    sistema_operativo: str = Field(min_length=1, max_length=100)
    entorno: EntornoInfra
    cpu_nucleos: int | None = Field(default=None, ge=1, le=65536)
    ram_bytes: int | None = Field(default=None, ge=1, le=2**63 - 1)
    disco_bytes: int | None = Field(default=None, ge=1, le=2**63 - 1)

    @field_validator("endpoint_privado")
    @classmethod
    def endpoint_sin_credenciales(cls, valor: str) -> str:
        partes = urlsplit(valor)
        if (
            partes.scheme not in {"http", "https"}
            or not partes.hostname
            or partes.username
            or partes.password
            or partes.query
            or partes.fragment
            or any(ord(c) < 33 for c in valor)
        ):
            raise ValueError("Use endpoint http/https sin credenciales, query ni fragmento")
        if partes.hostname in {"169.254.169.254", "metadata.google.internal"}:
            raise ValueError("No se admite un endpoint de metadata cloud")
        return valor


class ReporteIn(ContratoInfra):
    reporte_id: uuid.UUID
    cpu_porcentaje: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    ram_porcentaje: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    disco_porcentaje: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    servicios: dict[Literal["backend", "postgresql", "redis", "storage"], EstadoServicio]
    version: str | None = Field(default=None, min_length=1, max_length=100)


class VersionIn(ContratoInfra):
    version: str = Field(min_length=5, max_length=100)
    commit_git: str = Field(pattern=r"^[0-9a-f]{40}$")
    imagen_docker: str = Field(min_length=1, max_length=300, pattern=r"^[a-z0-9./_-]+$")
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    construida_at: datetime
    entorno: EntornoInfra
    migracion_desde: str = Field(min_length=1, max_length=100)
    migracion_hasta: str = Field(min_length=1, max_length=100)
    migracion_reversible: bool = False

    @field_validator("version")
    @classmethod
    def version_semantica(cls, valor: str) -> str:
        numero = r"(?:0|[1-9][0-9]*)"
        if not re.fullmatch(
            rf"{numero}\.{numero}\.{numero}(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", valor
        ):
            raise ValueError("Versión semántica inválida")
        return valor

    @field_validator("construida_at")
    @classmethod
    def fecha_con_zona(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None:
            raise ValueError("La fecha de construcción requiere zona horaria")
        return valor


class TenantNodoIn(ContratoInfra):
    tenant_id: uuid.UUID
    nodo_id: uuid.UUID
