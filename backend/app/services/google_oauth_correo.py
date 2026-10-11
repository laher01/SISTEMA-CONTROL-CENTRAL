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
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet

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


def _json_google(
    url: str, *, metodo: str = "GET", cuerpo: bytes | None = None, autorizacion: str | None = None
) -> dict[str, object]:
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
    *,
    code: str,
    verifier: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> tuple[str, str, str]:
    """Obtiene access + refresh token de Google; no persiste ni registra los tokens."""
    cuerpo = urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
    ).encode("utf-8")
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


def descifrar_refresh_token(token_cifrado: str, llave: str) -> str:
    try:
        return Fernet(llave.encode("ascii")).decrypt(token_cifrado.encode("ascii")).decode("utf-8")
    except (ValueError, TypeError) as exc:
        raise GoogleOAuthError("No fue posible descifrar la autorización") from exc


def renovar_google_token(*, refresh_token: str, client_id: str, client_secret: str) -> str:
    cuerpo = urlencode(
        {
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    datos = _json_google(GOOGLE_TOKEN_URL, metodo="POST", cuerpo=cuerpo)
    acceso = datos.get("access_token")
    if not isinstance(acceso, str) or not acceso:
        raise GoogleOAuthError("No se pudo renovar el acceso a Gmail")
    return acceso


def listar_ids_gmail(access_token: str, *, limite: int = 50) -> list[str]:
    parametros = urlencode({"maxResults": max(1, min(limite, 100))})
    datos = _json_google(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages?" + parametros,
        autorizacion=access_token,
    )
    mensajes = datos.get("messages", [])
    if not isinstance(mensajes, list):
        raise GoogleOAuthError("Listado Gmail inválido")
    return [
        mensaje["id"]
        for mensaje in mensajes
        if isinstance(mensaje, dict)
        and isinstance(mensaje.get("id"), str)
        and len(mensaje["id"]) <= 100
    ]


def obtener_correo_gmail(access_token: str, id_mensaje: str) -> bytes:
    if not id_mensaje.isalnum() or len(id_mensaje) > 100:
        raise GoogleOAuthError("Identificador de correo inválido")
    datos = _json_google(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/"
        + quote(id_mensaje, safe="")
        + "?format=raw",
        autorizacion=access_token,
    )
    raw = datos.get("raw")
    if not isinstance(raw, str) or len(raw) > 35 * 1024 * 1024:
        raise GoogleOAuthError("Correo Gmail inválido o demasiado grande")
    try:
        return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    except (ValueError, TypeError) as exc:
        raise GoogleOAuthError("Mensaje Gmail no decodificable") from exc
