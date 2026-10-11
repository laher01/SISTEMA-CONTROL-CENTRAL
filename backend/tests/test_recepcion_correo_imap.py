"""Pruebas del lector de correo sin conexiones externas."""

from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import CorreoBuzon, CorreoMensaje, Miembro
from app.services.expedientes import obtener_tenant
from app.services.recepcion_correo_imap import _adjuntos_xml, procesar_mensaje


def test_extrae_xml_de_correo_ficticio() -> None:
    mensaje = EmailMessage()
    mensaje["From"] = "Gestor Pruebas <GESTOR@example.test>"
    mensaje["To"] = "buzon@example.test"
    mensaje.set_content("Archivos adjuntos")
    mensaje.add_attachment(
        b"<documento>prueba</documento>",
        maintype="application",
        subtype="xml",
        filename="factura.xml",
    )
    remitente, adjuntos = _adjuntos_xml(mensaje.as_bytes())
    assert remitente == "gestor@example.test"
    assert len(adjuntos) == 1
    assert adjuntos[0].nombre == "factura.xml"


def test_uid_duplicado_no_reprocesa(session: Session, settings: Settings) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    responsable = Miembro(
        tenant_id=tenant.id,
        codigo="RESP-IMAP",
        nombre="Responsable IMAP",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    buzon = CorreoBuzon(
        tenant_id=tenant.id,
        direccion="buzon@example.test",
        proveedor="IMAP",
        responsable_id=responsable.id,
        activo=True,
    )
    session.add(buzon)
    session.commit()

    mensaje = EmailMessage()
    mensaje["From"] = "nadie@example.test"
    mensaje.set_content("Sin documentos")
    assert procesar_mensaje(session, settings, buzon, "123", mensaje.as_bytes()) == "REVISION"
    assert procesar_mensaje(session, settings, buzon, "123", mensaje.as_bytes()) == (
        "DUPLICADO_MENSAJE"
    )
    assert session.query(CorreoMensaje).count() == 1
