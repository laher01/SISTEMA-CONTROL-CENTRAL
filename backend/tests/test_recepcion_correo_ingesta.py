"""Regresiones: admisión de correo no puede saltarse controles previos."""

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import CorreoRemitente, Empresa, Gestor, Miembro
from app.services.expedientes import obtener_tenant
from app.services.ingesta import ArchivoSubido
from app.services.recepcion_correo_ingesta import admitir_adjunto_ubl
from app.storage import AlmacenLocal
from tests.xml import RECEPTOR, factura


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


def test_receptor_no_autorizado_con_ubl_valido(session: Session, settings: Settings) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    _registrar_gestor(session, tenant.id, "G4", "proveedor@example.com")
    resultado = admitir_adjunto_ubl(
        session,
        AlmacenLocal(settings.storage_dir),
        settings,
        date(2026, 10, 10),
        tenant.id,
        "proveedor@example.com",
        ArchivoSubido("factura.xml", "application/xml", factura()),
    )
    assert resultado.estado == "RECEPTOR_NO_AUTORIZADO"


def test_usuario_inactivo_con_ubl_valido(session: Session, settings: Settings) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    _registrar_gestor(session, tenant.id, "G5", "proveedor@example.com")
    receptor = Empresa(
        tenant_id=tenant.id,
        ruc=RECEPTOR,
        razon_social="EMPRESA RECEPTORA",
        autorizada=True,
    )
    session.add(receptor)
    session.flush()
    from sqlalchemy import select

    usuario = session.scalar(select(Miembro).where(Miembro.codigo == "USR-G5"))
    assert usuario is not None
    usuario.activo = False
    session.flush()
    resultado = admitir_adjunto_ubl(
        session,
        AlmacenLocal(settings.storage_dir),
        settings,
        date(2026, 10, 10),
        tenant.id,
        "proveedor@example.com",
        ArchivoSubido("factura.xml", "application/xml", factura()),
    )
    assert resultado.estado == "USUARIO_NO_AUTORIZADO"


def test_xml_duplicado_no_crea_segundo_documento(session: Session, settings: Settings) -> None:
    tenant = obtener_tenant(session, settings.tenant_default)
    _registrar_gestor(session, tenant.id, "G6", "proveedor@example.com")
    session.add(
        Empresa(
            tenant_id=tenant.id,
            ruc=RECEPTOR,
            razon_social="EMPRESA RECEPTORA",
            autorizada=True,
        )
    )
    session.flush()
    archivo = ArchivoSubido("factura.xml", "application/xml", factura())
    almacen = AlmacenLocal(settings.storage_dir)
    primero = admitir_adjunto_ubl(
        session, almacen, settings, date(2026, 10, 10), tenant.id, "proveedor@example.com", archivo
    )
    assert primero.estado == "INGRESADO"
    assert primero.documento_id is not None
    segundo = admitir_adjunto_ubl(
        session, almacen, settings, date(2026, 10, 10), tenant.id, "proveedor@example.com", archivo
    )
    assert segundo.estado == "DUPLICADO"
    from sqlalchemy import func, select

    from app.models import Documento

    assert session.scalar(
        select(func.count()).select_from(Documento).where(Documento.tenant_id == tenant.id)
    ) == 1
