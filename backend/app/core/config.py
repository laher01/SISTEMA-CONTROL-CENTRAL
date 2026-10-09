from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FC_", extra="ignore")

    database_url: str = "postgresql+psycopg://fact:fact@localhost:5432/fact_central"
    storage_dir: Path = Path("./storage")
    tenant_default: str = "default"
    tenant_domain: str = ""
    zona_horaria: str = "America/Lima"
    dia_limite_expediente: int = 7
    umbral_bancarizacion_pen: Decimal = Decimal("2000")
    umbral_bancarizacion_usd: Decimal = Decimal("500")
    max_upload_mb: int = 20
    max_extracted_chars: int = 200_000
    max_ocr_pdf_pages: int = 50
    tenant_ruc: str | None = None
    procesamiento_automatico: bool = True
    confianza_minima_clasificacion: float = 0.80
    confianza_minima_expediente: float = 0.75
    cors_origins: list[str] = []
    session_cookie_name: str = "factcentral_session"
    session_hours: int = 12
    nexus_ruc_url_template: str | None = None
    nexus_ruc_token: str | None = None
    nexus_search_url: str | None = None
    nexus_search_token: str | None = None
    nexus_external_timeout_seconds: int = 10
    infra_desconexion_segundos: int = Field(default=180, ge=30, le=86400)
    infra_cpu_umbral: float = Field(default=90, ge=0, le=100)
    infra_ram_umbral: float = Field(default=90, ge=0, le=100)
    infra_disco_umbral: float = Field(default=85, ge=0, le=100)
    infra_operaciones_habilitadas: bool = False
    infra_produccion_habilitada: bool = False
    infra_lease_segundos: int = Field(default=3600, ge=60, le=3600)

    def hoy(self) -> date:
        return datetime.now(ZoneInfo(self.zona_horaria)).date()


@lru_cache
def get_settings() -> Settings:
    return Settings()
