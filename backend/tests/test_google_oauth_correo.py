from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from app.services import google_oauth_correo
from app.services.google_oauth_correo import (
    consulta_gmail_periodo,
    crear_url_autorizacion,
    listar_ids_gmail,
    nuevo_desafio_pkce,
)


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
            client_id="a",
            redirect_uri="http://localhost/callback",
            state="s",
            code_challenge="c",
        )


def test_periodo_gmail_incluye_el_dia_final() -> None:
    assert consulta_gmail_periodo(desde=date(2026, 10, 1), hasta=date(2026, 10, 15)) == (
        "after:2026/10/01 before:2026/10/16"
    )


def test_periodo_gmail_rechaza_fechas_invertidas() -> None:
    with pytest.raises(ValueError):
        consulta_gmail_periodo(desde=date(2026, 10, 15), hasta=date(2026, 10, 1))


def test_listado_gmail_con_filtro_de_fechas(monkeypatch: pytest.MonkeyPatch) -> None:
    urls: list[str] = []

    def simular_google(url: str, **_kwargs: object) -> dict[str, object]:
        urls.append(url)
        return {"messages": [{"id": "mensaje123"}]}

    monkeypatch.setattr(google_oauth_correo, "_json_google", simular_google)
    assert listar_ids_gmail(
        "token-ficticio", desde=date(2026, 10, 1), hasta=date(2026, 10, 15)
    ) == ["mensaje123"]
    filtro = parse_qs(urlparse(urls[0]).query)
    assert filtro["q"] == ["after:2026/10/01 before:2026/10/16"]


def test_listado_gmail_rechaza_filtro_incompleto() -> None:
    with pytest.raises(ValueError):
        listar_ids_gmail("token-ficticio", desde=date(2026, 10, 1))
