"""Google OAuth 2.0 authorization primitives for authorized mailbox setup.

Authorization must begin in a browser session operated by ADMINISTRADOR.
Do not log or persist code_verifier, access tokens or refresh tokens in plaintext.
"""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

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
    if not redirect_uri.startswith("https://"):
        raise ValueError("El callback OAuth debe utilizar HTTPS")
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
