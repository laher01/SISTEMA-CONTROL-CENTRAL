"""Pruebas de Microsoft OAuth sin llamadas de red ni secretos reales."""

import pytest

from app.services import microsoft_oauth_correo as oauth


def test_url_consentimiento_pkce():
    url = oauth.crear_url_microsoft(
        client_id="ejemplo",
        redirect_uri="https://factcentral.online/api/v1/correo/microsoft/callback",
        state="estado",
        code_challenge="challenge",
    )
    assert "code_challenge_method=S256" in url
    assert "Mail.Read" in url
    assert "state=estado" in url


def test_verificacion_identidad_graph(monkeypatch):
    monkeypatch.setattr(
        oauth,
        "_consultar_json",
        lambda *args, **kw: {
            "mail": "operaciones@ejemplo.com",
            "userPrincipalName": "operaciones@tenant.onmicrosoft.com",
        },
    )
    oauth.comprobar_buzon_microsoft(access_token="ficticio", direccion="operaciones@ejemplo.com")
    with pytest.raises(oauth.MicrosoftOAuthError):
        oauth.comprobar_buzon_microsoft(access_token="ficticio", direccion="otra@ejemplo.com")


def test_intercambio_rechaza_scope_insuficiente(monkeypatch):
    monkeypatch.setattr(
        oauth,
        "_consultar_json",
        lambda *args, **kw: {
            "access_token": "acceso",
            "refresh_token": "refresco",
            "scope": "User.Read",
        },
    )
    with pytest.raises(oauth.MicrosoftOAuthError):
        oauth.intercambiar_codigo_microsoft(
            code="code",
            verifier="verifier",
            client_id="id",
            redirect_uri="https://example.org/callback",
        )


def test_intercambio_autorizado(monkeypatch):
    monkeypatch.setattr(
        oauth,
        "_consultar_json",
        lambda *args, **kw: {
            "access_token": "acceso",
            "refresh_token": "refresco",
            "scope": "Mail.Read User.Read",
        },
    )
    access, refresh, scopes = oauth.intercambiar_codigo_microsoft(
        code="code",
        verifier="verifier",
        client_id="id",
        redirect_uri="https://example.org/callback",
    )
    assert (access, refresh, scopes) == ("acceso", "refresco", "Mail.Read User.Read")
