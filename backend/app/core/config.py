from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FC_", extra="ignore")

    database_url: str = "postgresql+psycopg://fact:fact@localhost:5432/fact_central"
    storage_dir: Path = Path("./storage")
    tenant_default: str = "default"
    zona_horaria: str = "America/Lima"
    dia_limite_expediente: int = 7
    umbral_bancarizacion_pen: Decimal = Decimal("2000")
    umbral_bancarizacion_usd: Decimal = Decimal("500")
    max_upload_mb: int = 20
    cors_origins: list[str] = []

    def hoy(self) -> date:
        return datetime.now(ZoneInfo(self.zona_horaria)).date()


@lru_cache
def get_settings() -> Settings:
    return Settings()
