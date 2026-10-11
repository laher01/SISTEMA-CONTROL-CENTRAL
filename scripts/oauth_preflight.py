#!/usr/bin/env python3
"""Diagnóstico local sin red de configuración OAuth para correo FACT CENTRAL.

Ejecutar en el host/contenedor con variables FC_* cargadas. Nunca muestra secretos.
No prueba consentimiento, ni conectividad, ni permisos otorgados.
"""
import os
import sys
from urllib.parse import urlsplit

PREFIX = "FC_"


def is_https_callback(value: str) -> bool:
    try:
        url = urlsplit(value)
        return (
            url.scheme == "https"
            and bool(url.hostname)
            and url.username is None
            and url.password is None
            and not url.fragment
            and url.query == ""
        )
    except ValueError:
        return False


def check_provider(name: str, vars_required: tuple[str, ...]) -> bool:
    missing = [var for var in vars_required if not os.environ.get(PREFIX + var)]
    callback_name = next((var for var in vars_required if var.endswith("REDIRECT_URI")), None)
    callback = os.environ.get(PREFIX + callback_name, "") if callback_name else ""
    problems = [f"falta {PREFIX}{var}" for var in missing]
    if callback and not is_https_callback(callback):
        problems.append(f"{PREFIX}{callback_name} debe ser URL HTTPS sin query ni fragmento")
    if name == "GOOGLE":
        key = os.environ.get("FC_CORREO_TOKEN_ENCRYPTION_KEY", "")
        if key:
            try:
                from cryptography.fernet import Fernet
                Fernet(key.encode("ascii"))
            except (ImportError, ValueError, TypeError):
                problems.append("FC_CORREO_TOKEN_ENCRYPTION_KEY no es una clave Fernet válida")
    print(f"{name}: {'LISTO PARA PRUEBA EXTERNA' if not problems else 'INCOMPLETO'}")
    for issue in problems:
        print("  - " + issue)
    return not problems


def main() -> int:
    google = check_provider("GOOGLE", (
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
        "GOOGLE_OAUTH_REDIRECT_URI",
        "CORREO_TOKEN_ENCRYPTION_KEY",
    ))
    microsoft = check_provider("MICROSOFT (configuración preliminar)", (
        "MICROSOFT_OAUTH_CLIENT_ID",
        "MICROSOFT_OAUTH_REDIRECT_URI",
    ))
    print("Nota: Microsoft todavía necesita implementación completa de callback, token y Graph.")
    print("No introducir ni publicar secretos en este diagnóstico.")
    return 0 if google and microsoft else 1


if __name__ == "__main__":
    sys.exit(main())
