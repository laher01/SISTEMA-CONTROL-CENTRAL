from urllib.parse import parse_qs, urlparse

import pytest

from app.services.google_oauth_correo import crear_url_autorizacion, nuevo_desafio_pkce


def test_google_oauth_solicita_solo_lectura_y_pkce() -> None:
    verifier, challenge = nuevo_desafio_pkce()
    assert verifier and challenge and verifier != challenge
    url = crear_url_autorizacion(
        client_id="test-client-id",
        redirect_uri="https://app.example.test/api/v1/correo/google/callback",
        state="csrf-aleatorio",
        code_challenge=challenge,
    )
    query = parse_qs(urlparse(url).query)
    assert query["scope"] == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert query["state"] == ["csrf-aleatorio"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["access_type"] == ["offline"]
    assert "client_secret" not in query


def test_google_oauth_rechaza_callback_inseguro() -> None:
    with pytest.raises(ValueError):
        crear_url_autorizacion(
            client_id="a", redirect_uri="http://localhost/callback",
            state="s", code_challenge="c",
        )
