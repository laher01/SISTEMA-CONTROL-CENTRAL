"""OAuth Google: aislamiento entre tenants y configuración obligatoria."""

from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import CorreoBuzon, CorreoOAuthCredencial, CorreoOAuthIntento, Miembro
from tests.conftest import AuthPrueba


def test_google_no_inicia_sin_configuracion(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-GOOGLE",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    buzon = CorreoBuzon(
        tenant_id=tenant_id,
        direccion="factura.central.2023@gmail.com",
        proveedor="GOOGLE",
        responsable_id=responsable.id,
        activo=False,
    )
    session.add(buzon)
    session.commit()
    auth_prueba.como_admin()
    respuesta = client.post(f"/api/v1/correo/buzones/{buzon.id}/google/iniciar")
    assert respuesta.status_code == 503
    auth_prueba.como_gerente()
    prohibido = client.post(f"/api/v1/correo/buzones/{buzon.id}/google/iniciar")
    assert prohibido.status_code == 403


def test_google_inicia_estado_pkce_para_buzon_correcto(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
    monkeypatch,
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-GOOGLE2",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    buzon = CorreoBuzon(
        tenant_id=tenant_id,
        direccion="factura.central.2023@gmail.com",
        proveedor="GOOGLE",
        responsable_id=responsable.id,
        activo=False,
    )
    session.add(buzon)
    session.commit()
    monkeypatch.setattr(
        "app.api.routes.correo.get_settings",
        lambda: Settings(
            google_oauth_client_id="client-id-pruebas",
            google_oauth_client_secret="secreto-de-prueba",
            correo_token_encryption_key=Fernet.generate_key().decode("ascii"),
            google_oauth_redirect_uri="https://app.nexomarnegocioseirl.online/api/v1/correo/google/callback",
        ),
    )
    auth_prueba.como_admin()
    respuesta = client.post(f"/api/v1/correo/buzones/{buzon.id}/google/iniciar")
    assert respuesta.status_code == 200, respuesta.text
    params = parse_qs(urlparse(respuesta.json()["authorization_url"]).query)
    assert params["client_id"] == ["client-id-pruebas"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"][0]
    assert params["scope"] == ["https://www.googleapis.com/auth/gmail.readonly"]
    intento = session.scalar(select(CorreoOAuthIntento))
    assert intento is not None
    assert intento.tenant_id == tenant_id
    assert intento.buzon_id == buzon.id
    assert intento.cuenta_id == auth_prueba.contexto.cuenta_id
    assert intento.state_hash != params["state"][0]
    assert not buzon.activo


def test_callback_activa_solo_buzon_que_google_verifica(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
    monkeypatch,
) -> None:
    from app.services.google_oauth_correo import GMAIL_READONLY_SCOPE

    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-CALLBACK",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    buzon = CorreoBuzon(
        tenant_id=tenant_id,
        direccion="factura.central.2023@gmail.com",
        proveedor="GOOGLE",
        responsable_id=responsable.id,
        activo=False,
    )
    session.add(buzon)
    session.commit()
    llave = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(
        "app.api.routes.correo.get_settings",
        lambda: Settings(
            google_oauth_client_id="oauth-TEST",
            google_oauth_client_secret="secreto-pruebas",
            google_oauth_redirect_uri="https://app.nexomarnegocioseirl.online/api/v1/correo/google/callback",
            correo_token_encryption_key=llave,
        ),
    )
    monkeypatch.setattr(
        "app.api.routes.correo.intercambiar_codigo_google",
        lambda **kwargs: ("access-test", "refresh-test", GMAIL_READONLY_SCOPE),
    )
    comprobadas: list[str] = []
    monkeypatch.setattr(
        "app.api.routes.correo.comprobar_buzon_google",
        lambda **kwargs: comprobadas.append(kwargs["direccion"]),
    )
    session.get(Miembro, auth_prueba.contexto.miembro_id).rol = "ADMINISTRADOR"
    session.commit()
    auth_prueba.como_admin()
    inicio = client.post(f"/api/v1/correo/buzones/{buzon.id}/google/iniciar")
    assert inicio.status_code == 200, inicio.text
    state = parse_qs(urlparse(inicio.json()["authorization_url"]).query)["state"][0]
    respuesta = client.get(
        "/api/v1/correo/google/callback",
        params={"code": "codigo-simulado", "state": state},
        follow_redirects=False,
        headers={"host": "app.nexomarnegocioseirl.online"},
    )
    assert respuesta.status_code == 303, respuesta.text
    assert comprobadas == ["factura.central.2023@gmail.com"]
    session.refresh(buzon)
    assert buzon.activo is True
    credencial = session.scalar(select(CorreoOAuthCredencial))
    assert credencial is not None
    assert credencial.buzon_id == buzon.id
    assert credencial.token_cifrado != "refresh-test"
    assert Fernet(llave.encode()).decrypt(credencial.token_cifrado.encode()) == b"refresh-test"
    repetido = client.get(
        "/api/v1/correo/google/callback",
        params={"code": "codigo-simulado", "state": state},
        follow_redirects=False,
        headers={"host": "app.nexomarnegocioseirl.online"},
    )
    assert repetido.status_code == 400
