"""Construcción de consentimiento OAuth Microsoft con PKCE.

Una URL de consentimiento NO conecta el buzón: faltan callback seguro,
canje de código, almacenamiento cifrado y autorización real del titular.
"""

import secrets
from urllib.parse import urlencode, urlsplit

from app.services.google_oauth_correo import nuevo_desafio_pkce

MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_MAIL_READ_SCOPE = "https://graph.microsoft.com/Mail.Read"


def crear_url_microsoft(
    *, client_id: str, redirect_uri: str, state: str, code_challenge: str
) -> str:
    if not all((client_id, state, code_challenge)):
        raise ValueError("OAuth Microsoft requiere client_id, state y PKCE")
    destino = urlsplit(redirect_uri)
    if (
        destino.scheme != "https"
        or not destino.hostname
        or destino.username is not None
        or destino.password is not None
        or destino.fragment
    ):
        raise ValueError("El callback OAuth debe ser HTTPS y no contener credenciales ni fragmentos")
    parametros = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": f"openid profile email offline_access {MICROSOFT_MAIL_READ_SCOPE}",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    return f"{MICROSOFT_AUTH_URL}?{parametros}"


def nuevo_estado_oauth() -> str:
    return secrets.token_urlsafe(32)


__all__ = ["crear_url_microsoft", "nuevo_desafio_pkce", "nuevo_estado_oauth"]
