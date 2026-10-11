"""OAuth de Microsoft: consentimiento delegado y parámetros de seguridad."""

from urllib.parse import parse_qs, urlparse

import pytest

from app.services.microsoft_oauth_correo import (
    crear_url_microsoft,
    nuevo_desafio_pkce,
    nuevo_estado_oauth,
)


def test_url_consentimiento_microsoft_mail_read_con_pkce() -> None:
    _, challenge = nuevo_desafio_pkce()
    state = nuevo_estado_oauth()
    url = crear_url_microsoft(
        client_id="cliente-prueba",
        redirect_uri="https://app.nexomarnegocioseirl.online/api/v1/correo/callback-microsoft",
        state=state,
        code_challenge=challenge,
    )
    parsed = urlparse(url)
    datos = parse_qs(parsed.query)
    assert parsed.netloc == "login.microsoftonline.com"
    assert datos["client_id"] == ["cliente-prueba"]
    assert datos["state"] == [state]
    assert datos["code_challenge_method"] == ["S256"]
    assert datos["code_challenge"] == [challenge]
    assert "https://graph.microsoft.com/Mail.Read" in datos["scope"][0]
    assert "offline_access" in datos["scope"][0]
    assert "client_secret" not in datos


def test_microsoft_rechaza_redirect_no_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        crear_url_microsoft(
            client_id="cliente",
            redirect_uri="http://localhost/callback",
            state="estado",
            code_challenge="desafio",
        )


def test_estado_oauth_aleatorio() -> None:
    assert nuevo_estado_oauth() != nuevo_estado_oauth()
