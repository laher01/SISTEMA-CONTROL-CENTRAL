"""Regresiones: admisión de correo no puede saltarse controles previos."""

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import CorreoRemitente, Gestor, Miembro
from app.services.expedientes import obtener_tenant
from app.services.ingesta import ArchivoSubido
from app.services.recepcion_correo_ingesta import admitir_adjunto_ubl
from app.storage import AlmacenLocal


def _adjunto(nombre: str = "prueba.xml") -> ArchivoSubido:
    return ArchivoSubido(nombre=nombre, mime_type="application/xml", contenido=b"<invalid")


def _registrar_gestor(session: Session, tenant_id: object, codigo: str, email: str) -> None:
    miembro = Miembro(
        tenant_id=tenant_id,
        codigo=f"USR-{codigo}",
        nombre=codigo,
        rol="USUARIO",
        activo=True,
    )
    session.add(miembro)
    session.flush()
    gestor = Gestor(tenant_id=tenant_id, codigo=codigo, nombre=codigo, usuario_id=miembro.id)
    session.add(gestor)
    session.flush()
    session.add(
        CorreoRemitente(
            tenant_id=tenant_id,
            gestor_id=gestor.id,
            direccion=email,
            activo=True,
        )
    )
    session.flush()


def test_no_ingiere_remitente_desconocido(session: Session, settings: Settings) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    resultado = admitir_adjunto_ubl(
        session,
        AlmacenLocal(settings.storage_dir),
        settings,
        date(2026, 10, 10),
        tenant.id,
        "inexistente@example.com",
        _adjunto(),
    )
    assert resultado.estado == "REMITENTE_NO_REGISTRADO"
    assert resultado.documento_id is None


def test_gestor_ambiguo_no_ingiere(session: Session, settings: Settings) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    _registrar_gestor(session, tenant.id, "G1", "emisor@example.com")
    _registrar_gestor(session, tenant.id, "G2", "emisor@example.com")
    resultado = admitir_adjunto_ubl(
        session,
        AlmacenLocal(settings.storage_dir),
        settings,
        date(2026, 10, 10),
        tenant.id,
        "emisor@example.com",
        _adjunto(),
    )
    assert resultado.estado == "GESTOR_AMBIGUO"


def test_no_ingiere_archivo_no_ubl(session: Session, settings: Settings) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    _registrar_gestor(session, tenant.id, "G1", "emisor@example.com")
    resultado = admitir_adjunto_ubl(
        session,
        AlmacenLocal(settings.storage_dir),
        settings,
        date(2026, 10, 10),
        tenant.id,
        "emisor@example.com",
        _adjunto("foto.png"),
    )
    assert resultado.estado == "REVISION_TIPO_DOCUMENTO"
