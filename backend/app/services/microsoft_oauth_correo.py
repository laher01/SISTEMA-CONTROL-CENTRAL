"""Construcción de consentimiento OAuth Microsoft con PKCE.

Una URL de consentimiento NO conecta el buzón: faltan callback seguro,
canje de código, almacenamiento cifrado y autorización real del titular.
"""

import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

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
        raise ValueError("Callback OAuth inválido: use HTTPS sin credenciales ni fragmentos")
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


# Funciones auxiliares de Graph. Estas no activan ni conectan un buzón.
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_ME_URL = "https://graph.microsoft.com/v1.0/me"


class MicrosoftOAuthError(ValueError):
    """Error sin exponer códigos de autorización ni tokens."""


def _consultar_json(url: str, *, datos: bytes | None = None, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if datos is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    req = Request(url, data=datos, headers=headers, method="POST" if datos is not None else "GET")
    try:
        with urlopen(req, timeout=12) as response:
            parsed = json.loads(response.read(128 * 1024))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise MicrosoftOAuthError("Microsoft rechazó la solicitud de autorización") from exc
    if not isinstance(parsed, dict):
        raise MicrosoftOAuthError("Respuesta Microsoft inválida")
    return parsed


def intercambiar_codigo_microsoft(
    *, code: str, verifier: str, client_id: str, redirect_uri: str,
    client_secret: str | None = None,
) -> tuple[str, str, str]:
    """Canje OAuth de autorización; no almacena tokens."""
    if not all((code, verifier, client_id, redirect_uri)):
        raise MicrosoftOAuthError("Faltan parámetros OAuth")
    parametros = {
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
        "scope": "openid profile email offline_access " + MICROSOFT_MAIL_READ_SCOPE,
    }
    if client_secret:
        parametros["client_secret"] = client_secret
    resultado = _consultar_json(MICROSOFT_TOKEN_URL, datos=urlencode(parametros).encode())
    acceso = resultado.get("access_token")
    refresco = resultado.get("refresh_token")
    permisos = resultado.get("scope", "")
    if not isinstance(acceso, str) or not isinstance(refresco, str) or not acceso or not refresco:
        raise MicrosoftOAuthError("Microsoft no devolvió credenciales renovables")
    if not isinstance(permisos, str) or not any(s.lower() == "mail.read" for s in permisos.split()):
        raise MicrosoftOAuthError("No se concedió Mail.Read")
    return acceso, refresco, permisos


def comprobar_buzon_microsoft(*, access_token: str, direccion: str) -> None:
    """Comprueba identidad exacta, nunca vincula buzones solo por consentimiento."""
    perfil = _consultar_json(MICROSOFT_ME_URL, token=access_token)
    direcciones = {
        str(perfil.get("mail") or "").strip().casefold(),
        str(perfil.get("userPrincipalName") or "").strip().casefold(),
    }
    if direccion.strip().casefold() not in direcciones:
        raise MicrosoftOAuthError("La cuenta Microsoft no coincide con el buzón registrado")
