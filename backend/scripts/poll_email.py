"""Ejecuta una lectura IMAP de buzones activos en un proceso independiente.

Uso: uv run python scripts/poll_email.py
Planificar desde el orquestador de staging, no en el servidor HTTP.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_engine
from app.models import CorreoBuzon
from app.services.recepcion_correo_imap import consultar_buzon


def main() -> None:
    settings = get_settings()
    with Session(get_engine()) as session:
        buzones = list(session.scalars(select(CorreoBuzon.id).where(CorreoBuzon.activo.is_(True))))
        for buzon_id in buzones:
            try:
                consultar_buzon(session, settings, buzon_id)
            except Exception as exc:
                session.rollback()
                buzon = session.get(CorreoBuzon, buzon_id)
                if buzon is not None:
                    buzon.ultimo_error = str(exc)[:500]
                    session.commit()


if __name__ == "__main__":
    main()
