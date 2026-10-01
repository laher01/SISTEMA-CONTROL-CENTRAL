"""Inicializa la base local de FACT CENTRAL sin depender de Docker."""

from app.core.config import get_settings
from app.core.db import get_engine
from app.models import Base


def main() -> None:
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(get_engine())
    print(f"Base local lista: {settings.database_url}")
    print(f"Almacén documental: {settings.storage_dir.resolve()}")


if __name__ == "__main__":
    main()
