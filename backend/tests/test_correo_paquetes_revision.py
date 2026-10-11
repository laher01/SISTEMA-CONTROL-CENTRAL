"""Simulaciones de seguridad: remitentes ajenos y ZIP inválidos."""

import io
import zipfile
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import CorreoBuzon, CorreoMensaje, CorreoRemitente, Gestor, Miembro
from app.services.expedientes import obtener_tenant
from app.services.recepcion_correo_imap import procesar_mensaje


def _mensaje(remitente: str, zip_bytes: bytes) -> bytes:
    correo = EmailMessage()
    correo["From"] = remitente
    correo["To"] = "recepcion@example.test"
    correo.set_content("Comprobante")
    correo.add_attachment(zip_bytes, maintype="application", subtype="zip", filename="paquete.zip")
    return correo.as_bytes()


def _zip_peligroso() -> bytes:
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as paquete:
        paquete.writestr("../fuera.xml", b"<Invoice/>")
    return salida.getvalue()


def test_zip_malicioso_queda_en_revision_y_no_bloquea_siguiente(
    session: Session, settings: Settings
) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    usuario = Miembro(
        tenant_id=tenant.id,
        codigo="USER-ZIP",
        nombre="Usuario",
        rol="USUARIO",
        activo=True,
    )
    responsable = Miembro(
        tenant_id=tenant.id,
        codigo="RESP-ZIP",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add_all([usuario, responsable])
    session.flush()
    gestor = Gestor(tenant_id=tenant.id, codigo="G-ZIP", nombre="Jenny", usuario_id=usuario.id)
    session.add(gestor)
    session.flush()
    session.add(
        CorreoRemitente(
            tenant_id=tenant.id,
            direccion="jenny2026@gmail.com",
            gestor_id=gestor.id,
            activo=True,
        )
    )
    buzon = CorreoBuzon(
        tenant_id=tenant.id,
        direccion="recepcion@example.test",
        proveedor="IMAP",
        responsable_id=responsable.id,
        activo=True,
    )
    session.add(buzon)
    session.commit()

    malicioso = _mensaje("jenny2026@gmail.com", _zip_peligroso())
    assert procesar_mensaje(session, settings, buzon, "uid-peligroso", malicioso) == "REVISION"
    registrado = session.scalar(
        select(CorreoMensaje).where(CorreoMensaje.identificador_externo == "uid-peligroso")
    )
    assert registrado is not None
    assert registrado.error == "PAQUETE_NO_SEGURO"
    assert registrado.gestor_id == gestor.id
    assert procesar_mensaje(session, settings, buzon, "uid-peligroso", malicioso) == (
        "DUPLICADO_MENSAJE"
    )
    desconocido = _mensaje("desconocido@example.test", _zip_peligroso())
    assert procesar_mensaje(session, settings, buzon, "uid-desconocido", desconocido) == "REVISION"
    no_autorizado = session.scalar(
        select(CorreoMensaje).where(CorreoMensaje.identificador_externo == "uid-desconocido")
    )
    assert no_autorizado is not None
    assert no_autorizado.error == "REMITENTE_NO_REGISTRADO"
    assert no_autorizado.gestor_id is None
