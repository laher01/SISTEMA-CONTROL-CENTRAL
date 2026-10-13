"""Simulación de Gmail worker sin conectarse realmente a Google."""

from email.message import EmailMessage

import pytest

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import (
    CorreoBuzon,
    CorreoMensaje,
    CorreoOAuthCredencial,
    CorreoRemitente,
    Empresa,
    Gestor,
    Miembro,
)
from app.services.expedientes import obtener_tenant
from app.workers.correo_google import revisar_ciclo_google
from tests.xml import RECEPTOR, factura


def test_worker_google_lee_una_vez_y_atribuye_a_jenny(
    session: Session, settings: Settings, monkeypatch
) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    usuario = Miembro(
        tenant_id=tenant.id,
        codigo="WILLI-GMAIL",
        nombre="Willi",
        rol="USUARIO",
        activo=True,
    )
    responsable = Miembro(
        tenant_id=tenant.id,
        codigo="RESP-GMAIL",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add_all([usuario, responsable])
    session.flush()
    jenny = Gestor(
        tenant_id=tenant.id,
        codigo="JENNY-GMAIL",
        nombre="Jenny",
        usuario_id=usuario.id,
    )
    session.add(jenny)
    session.flush()
    session.add(
        CorreoRemitente(
            tenant_id=tenant.id,
            direccion="jenny2026@gmail.com",
            gestor_id=jenny.id,
            activo=True,
        )
    )
    buzon = CorreoBuzon(
        tenant_id=tenant.id,
        direccion="factura.central.2023@gmail.com",
        proveedor="GOOGLE",
        responsable_id=responsable.id,
        activo=True,
    )
    session.add(buzon)
    session.flush()
    session.add(
        CorreoOAuthCredencial(
            tenant_id=tenant.id,
            buzon_id=buzon.id,
            proveedor="GOOGLE",
            token_cifrado="cifrado-ficticio",
            permisos="https://www.googleapis.com/auth/gmail.readonly",
            verificado_at=buzon.created_at,
        )
    )
    session.add(
        Empresa(
            tenant_id=tenant.id,
            ruc=RECEPTOR,
            razon_social="CLIENTE AUTORIZADO",
            autorizada=True,
        )
    )
    session.commit()
    mensaje = EmailMessage()
    mensaje["From"] = "Jenny <jenny2026@gmail.com>"
    mensaje["To"] = buzon.direccion
    mensaje.set_content("Factura adjunta")
    mensaje.add_attachment(
        factura(), maintype="application", subtype="xml", filename="F001-123.xml"
    )
    monkeypatch.setattr(
        "app.workers.correo_google.descifrar_refresh_token",
        lambda *args: "refresh-ficticio",
    )
    monkeypatch.setattr(
        "app.workers.correo_google.renovar_google_token",
        lambda **kwargs: "access-ficticio",
    )
    monkeypatch.setattr(
        "app.workers.correo_google.listar_ids_gmail",
        lambda token: ["gmail-uid-001"],
    )
    monkeypatch.setattr(
        "app.workers.correo_google.obtener_correo_gmail",
        lambda token, uid: mensaje.as_bytes(),
    )
    config = Settings(
        tenant_default=settings.tenant_default,
        storage_dir=settings.storage_dir,
        correo_google_worker_enabled=True,
        google_oauth_client_id="id-test",
        google_oauth_client_secret="secret-test",
        correo_token_encryption_key="key-ficticia",
    )
    assert revisar_ciclo_google(session, config) == 1
    registros = list(session.scalars(select(CorreoMensaje)))
    assert len(registros) == 1
    assert registros[0].gestor_id == jenny.id
    assert registros[0].estado == "INGRESADO"
    assert revisar_ciclo_google(session, config) == 0
    assert len(list(session.scalars(select(CorreoMensaje)))) == 1


@pytest.mark.parametrize("limite", [0, -1, 101])
def test_worker_google_rechaza_limites_invalidos(
    session: Session, settings: Settings, limite: int
) -> None:
    with pytest.raises(ValueError, match="limite_por_buzon"):
        revisar_ciclo_google(session, settings, limite_por_buzon=limite)
