"""Simulación offline: dos remitentes de Jenny, tres buzones, un documento."""

from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import (
    CorreoBuzon,
    CorreoMensaje,
    CorreoRemitente,
    Documento,
    Empresa,
    Gestor,
    Miembro,
)
from app.services.expedientes import obtener_tenant
from app.services.recepcion_correo_imap import procesar_mensaje
from tests.xml import RECEPTOR, factura


def _correo(remitente: str, destino: str) -> bytes:
    mensaje = EmailMessage()
    mensaje["From"] = remitente
    mensaje["To"] = destino
    mensaje["Subject"] = "Factura electrónica"
    mensaje.set_content("Factura adjunta")
    mensaje.add_attachment(
        factura(),
        maintype="application",
        subtype="xml",
        filename="F001-123.xml",
    )
    return mensaje.as_bytes()


def test_jenny_se_atribuye_a_willi_en_tres_buzones(session: Session, settings: Settings) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    willi = Miembro(
        tenant_id=tenant.id,
        codigo="WILLI01",
        nombre="Willi",
        rol="USUARIO",
        activo=True,
    )
    responsable = Miembro(
        tenant_id=tenant.id,
        codigo="RESP-JENNY",
        nombre="Responsable Jenny",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add_all([willi, responsable])
    session.flush()
    jenny = Gestor(
        tenant_id=tenant.id,
        codigo="JENNY01",
        nombre="Jenny",
        usuario_id=willi.id,
    )
    session.add(jenny)
    session.flush()
    for direccion in ("jenny2026@gmail.com", "astro15@gmail.com"):
        session.add(
            CorreoRemitente(
                tenant_id=tenant.id,
                gestor_id=jenny.id,
                direccion=direccion,
                activo=True,
            )
        )
    destinos = (
        "factur.central.2023@gmail.com",
        "factura_central@outlook.com",
        "laher01.paita@gmail.com",
    )
    buzones = [
        CorreoBuzon(
            tenant_id=tenant.id,
            responsable_id=responsable.id,
            direccion=destino,
            proveedor="IMAP",
            activo=True,
        )
        for destino in destinos
    ]
    session.add_all(buzones)
    session.add(
        Empresa(
            tenant_id=tenant.id,
            ruc=RECEPTOR,
            razon_social="CLIENTE AUTORIZADO",
            autorizada=True,
        )
    )
    session.commit()

    buzon0 = procesar_mensaje(
        session,
        settings,
        buzones[0],
        "uid-10",
        _correo("Jenny <jenny2026@gmail.com>", destinos[0]),
    )
    assert buzon0 == "INGRESADO"
    buzon1 = procesar_mensaje(
        session,
        settings,
        buzones[1],
        "uid-10",
        _correo("Jenny <astro15@gmail.com>", destinos[1]),
    )
    assert buzon1 == "REVISION"
    buzon2 = procesar_mensaje(
        session,
        settings,
        buzones[2],
        "uid-11",
        _correo("Jenny <jenny2026@gmail.com>", destinos[2]),
    )
    assert buzon2 == "REVISION"
    documentos = list(session.scalars(select(Documento).where(Documento.tenant_id == tenant.id)))
    assert len(documentos) == 1
    assert documentos[0].gestor_id == jenny.id
    assert documentos[0].usuario_id == willi.id
    mensajes = list(
        session.scalars(select(CorreoMensaje).where(CorreoMensaje.tenant_id == tenant.id))
    )
    assert len(mensajes) == 3
    mismo_uid = procesar_mensaje(
        session,
        settings,
        buzones[0],
        "uid-10",
        _correo("Jenny <jenny2026@gmail.com>", destinos[0]),
    )
    assert mismo_uid == "DUPLICADO_MENSAJE"


def test_remitente_no_registrado_no_crea_documento(session: Session, settings: Settings) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    responsable = Miembro(
        tenant_id=tenant.id,
        codigo="RESP-UNKNOWN",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    buzon = CorreoBuzon(
        tenant_id=tenant.id,
        responsable_id=responsable.id,
        direccion="entrada@example.test",
        proveedor="IMAP",
        activo=True,
    )
    session.add(buzon)
    session.commit()
    estado = procesar_mensaje(
        session,
        settings,
        buzon,
        "uid-2",
        _correo("falso@example.test", buzon.direccion),
    )
    assert estado == "REVISION"
    documentos = list(session.scalars(select(Documento).where(Documento.tenant_id == tenant.id)))
    assert len(documentos) == 0
