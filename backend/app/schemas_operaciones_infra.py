import uuid
from typing import Literal

from pydantic import Field

from app.schemas_infraestructura import ContratoInfra


class ValidacionVersionIn(ContratoInfra):
    evidencia_ci: str = Field(
        max_length=300,
        pattern=r"^https://github\.com/laher01/SISTEMA-CONTROL-CENTRAL/actions/runs/[0-9]+$",
    )


class DespliegueIn(ContratoInfra):
    solicitud_id: uuid.UUID
    nodo_id: uuid.UUID
    version_id: uuid.UUID
    backup_id: uuid.UUID | None = None


class BackupIn(ContratoInfra):
    solicitud_id: uuid.UUID
    nodo_id: uuid.UUID
    retencion_dias: int = Field(default=14, ge=1, le=365)


class LoteIn(ContratoInfra):
    solicitud_id: uuid.UUID
    nodos: list[uuid.UUID] = Field(min_length=1, max_length=20)
    version_id: uuid.UUID
    backups: dict[uuid.UUID, uuid.UUID] = Field(default_factory=dict)


class ResultadoOperacionIn(ContratoInfra):
    lease: str = Field(min_length=32, max_length=200)
    estado: Literal["EXITO", "FALLO"]
    codigo_error: (
        Literal[
            "TIMEOUT", "HEALTHCHECK", "IMAGEN", "MIGRACION", "BACKUP", "CONFIGURACION", "AGENTE"
        ]
        | None
    ) = None
    backend_ok: bool = False
    base_datos_ok: bool = False
    imagen_verificada: bool = False
    migracion: str | None = Field(default=None, max_length=100)
    objeto: str | None = Field(default=None, max_length=200, pattern=r"^[A-Za-z0-9._-]+\.age$")
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    bytes: int | None = Field(default=None, ge=1, le=2**63 - 1)
    dump_verificado: bool = False


class RestauracionVerificadaIn(ContratoInfra):
    evidencia: str = Field(min_length=10, max_length=500)
    entorno: Literal["development", "staging"]
