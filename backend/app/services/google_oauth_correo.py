"""Google OAuth 2.0 authorization primitives for authorized mailbox setup.

Authorization must begin in a browser session operated by ADMINISTRADOR.
Do not log or persist code_verifier, access tokens or refresh tokens in plaintext.
"""

import base64
import hashlib
import json
import secrets
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, urlsplit

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def nuevo_desafio_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    return verifier, challenge


def crear_url_autorizacion(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
) -> str:
    if not client_id or not state or not code_challenge:
        raise ValueError("OAuth requiere client_id, state y PKCE")
    destino = urlsplit(redirect_uri)
    if (
        destino.scheme != "https"
        or not destino.hostname
        or destino.username is not None
        or destino.password is not None
        or destino.fragment
    ):
        raise ValueError("Callback OAuth inválido: use HTTPS sin credenciales ni fragmentos")
    parametros = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GMAIL_READONLY_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{parametros}"


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"


class GoogleOAuthError(ValueError):
    """Error de autorización controlado: jamás registra secretos."""


def _json_google(url: str, *, metodo: str = "GET", cuerpo: bytes | None = None,
                 autorizacion: str | None = None) -> dict[str, object]:
    headers = {"Accept": "application/json"}
    if cuerpo is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if autorizacion is not None:
        headers["Authorization"] = "Bearer " + autorizacion
    solicitud = Request(url, data=cuerpo, headers=headers, method=metodo)
    try:
        with urlopen(solicitud, timeout=12) as respuesta:
            contenido = respuesta.read(128 * 1024)
        datos = json.loads(contenido)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise GoogleOAuthError("Google rechazó la solicitud OAuth") from exc
    if not isinstance(datos, dict):
        raise GoogleOAuthError("Respuesta OAuth inesperada")
    return cast(dict[str, object], datos)


def intercambiar_codigo_google(
    *, code: str, verifier: str, client_id: str, client_secret: str, redirect_uri: str,
) -> tuple[str, str, str]:
    """Obtiene access + refresh token de Google; no persiste ni registra los tokens."""
    cuerpo = urlencode({
        "code": code, "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect_uri, "grant_type": "authorization_code",
        "code_verifier": verifier,
    }).encode("utf-8")
    datos = _json_google(GOOGLE_TOKEN_URL, metodo="POST", cuerpo=cuerpo)
    acceso = datos.get("access_token")
    refresco = datos.get("refresh_token")
    scope = datos.get("scope")
    if not isinstance(acceso, str) or not isinstance(refresco, str):
        raise GoogleOAuthError("Google no devolvió autorización permanente")
    if not isinstance(scope, str) or GMAIL_READONLY_SCOPE not in scope.split():
        raise GoogleOAuthError("Permiso de lectura Gmail no concedido")
    return acceso, refresco, scope


def comprobar_buzon_google(*, access_token: str, direccion: str) -> None:
    datos = _json_google(GMAIL_PROFILE_URL, autorizacion=access_token)
    real = datos.get("emailAddress")
    if not isinstance(real, str) or real.strip().lower() != direccion.strip().lower():
        raise GoogleOAuthError("La cuenta autorizada no coincide con el buzón registrado")


def cifrar_refresh_token(token: str, llave: str) -> str:
    try:
        return Fernet(llave.encode("ascii")).encrypt(token.encode("utf-8")).decode("ascii")
    except (ValueError, TypeError) as exc:
        raise GoogleOAuthError("Clave de cifrado inválida") from exc
