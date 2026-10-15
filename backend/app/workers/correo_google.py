"""Worker Gmail separado de HTTP: solo buzones Google autorizados de cada tenant."""

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


def revisar_ciclo_google(session: Session, settings: Settings) -> int:
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
    for buzon, credencial in buzones:
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
            for id_mensaje in (
                listar_ids_gmail(acceso, desde=buzon.importar_desde)
                if buzon.importar_desde else listar_ids_gmail(acceso)
            ):
                previo = session.scalar(
                    select(CorreoMensaje.id).where(
                        CorreoMensaje.tenant_id == buzon.tenant_id,
                        CorreoMensaje.buzon_id == buzon.id,
                        CorreoMensaje.identificador_externo == id_mensaje,
                    )
                )
                if previo is not None:
                    continue
                contenido = obtener_correo_gmail(acceso, id_mensaje)
                if len(contenido) > MAX_MENSAJE_BYTES:
                    continue
                procesar_mensaje(session, settings, buzon, id_mensaje, contenido)
                total += 1
            buzon.ultimo_error = None
            session.commit()
        except (GoogleOAuthError, OSError, ValueError) as exc:
            session.rollback()
            buzon.ultimo_error = type(exc).__name__ + ": recepción no disponible"
            session.commit()
        except Exception:
            session.rollback()
            buzon.ultimo_error = "ERROR_PROCESAMIENTO"
            session.commit()
    return total


def main() -> None:
    settings = get_settings()
    intervalo = max(60, settings.correo_google_interval_seconds)
    while True:
        with get_sessionmaker()() as session:
            revisar_ciclo_google(session, settings)
        time.sleep(intervalo)


if __name__ == "__main__":
    main()
