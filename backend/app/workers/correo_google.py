"""Worker Gmail separado de HTTP: solo buzones Google autorizados de cada tenant."""

import logging
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_sessionmaker
from app.models import CorreoBuzon, CorreoMensaje, CorreoOAuthCredencial
from app.services.google_oauth_correo import (
    GoogleOAuthError,
    descifrar_refresh_token,
    listar_ids_gmail,
    obtener_correo_gmail,
    renovar_google_token,
)
from app.services.recepcion_correo_imap import MAX_MENSAJE_BYTES, procesar_mensaje

logger = logging.getLogger(__name__)


def revisar_ciclo_google(
    session: Session, settings: Settings, *, limite_por_buzon: int = 50
) -> int:
    """Revisa buzones una vez; limite_por_buzon permite pruebas acotadas."""
    if not 1 <= limite_por_buzon <= 100:
        raise ValueError("limite_por_buzon debe estar entre 1 y 100")
    if not (
        settings.correo_google_worker_enabled
        and settings.google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.correo_token_encryption_key
    ):
        return 0
    buzones = list(
        session.execute(
            select(CorreoBuzon, CorreoOAuthCredencial)
            .join(
                CorreoOAuthCredencial,
                (CorreoBuzon.id == CorreoOAuthCredencial.buzon_id)
                & (CorreoBuzon.tenant_id == CorreoOAuthCredencial.tenant_id),
            )
            .where(
                CorreoBuzon.activo.is_(True),
                CorreoBuzon.proveedor == "GOOGLE",
                CorreoOAuthCredencial.proveedor == "GOOGLE",
            )
        )
    )
    total = 0
    logger.info(
        "Gmail: inicio de ciclo; buzones=%s limite=%s", len(buzones), limite_por_buzon
    )
    for buzon, credencial in buzones:
        nuevos = 0
        repetidos = 0
        try:
            refresh = descifrar_refresh_token(
                credencial.token_cifrado,
                settings.correo_token_encryption_key,
            )
            acceso = renovar_google_token(
                refresh_token=refresh,
                client_id=settings.google_oauth_client_id,
                client_secret=settings.google_oauth_client_secret,
            )
            ids = listar_ids_gmail(acceso, limite=limite_por_buzon)
            for id_mensaje in ids:
                previo = session.scalar(
                    select(CorreoMensaje.id).where(
                        CorreoMensaje.tenant_id == buzon.tenant_id,
                        CorreoMensaje.buzon_id == buzon.id,
                        CorreoMensaje.identificador_externo == id_mensaje,
                    )
                )
                if previo is not None:
                    repetidos += 1
                    continue
                contenido = obtener_correo_gmail(acceso, id_mensaje)
                if len(contenido) > MAX_MENSAJE_BYTES:
                    continue
                procesar_mensaje(session, settings, buzon, id_mensaje, contenido)
                total += 1
                nuevos += 1
            buzon.ultimo_error = None
            session.commit()
            logger.info(
                "Gmail: buzón procesado; nuevos=%s repetidos=%s consultados=%s",
                nuevos,
                repetidos,
                len(ids),
            )
        except (GoogleOAuthError, OSError, ValueError) as exc:
            session.rollback()
            buzon.ultimo_error = type(exc).__name__ + ": recepción no disponible"
            session.commit()
            logger.warning("Gmail: recepción fallida; tipo=%s", type(exc).__name__)
        except Exception:
            session.rollback()
            buzon.ultimo_error = "ERROR_PROCESAMIENTO"
            session.commit()
            logger.error("Gmail: fallo inesperado durante procesamiento; revisar último_error")
    logger.info("Gmail: fin de ciclo; mensajes nuevos=%s", total)
    return total


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    intervalo = max(60, settings.correo_google_interval_seconds)
    while True:
        with get_sessionmaker()() as session:
            revisar_ciclo_google(session, settings)
        time.sleep(intervalo)


if __name__ == "__main__":
    main()
