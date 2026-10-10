"""Admisión segura de adjuntos UBL por remitente registrado.

Este servicio se invoca tras recibir el adjunto por un conector autenticado.
No descarga correos ni confirma autoría fiscal por sí mismo.
"""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import CorreoRemitente, Documento, Empresa, Gestor
from app.services.ingesta import (
    ArchivoSubido,
    ComprobanteYaRegistrado,
    DocumentoDuplicado,
    ingerir_documento,
)
from app.services.ubl import UblInvalido, parse_ubl
from app.storage import AlmacenLocal


@dataclass(frozen=True)
class ResultadoCorreo:
    estado: str
    documento_id: uuid.UUID | None = None


def admitir_adjunto_ubl(
    session: Session,
    almacen: AlmacenLocal,
    settings: Settings,
    hoy: date,
    tenant_id: uuid.UUID,
    remitente: str,
    archivo: ArchivoSubido,
) -> ResultadoCorreo:
    """Falla cerrada antes de invocar la ingesta, que puede crear empresas.

    Transacción propiedad del llamador: debe confirmar solo tras finalizar
    el procesamiento de un mensaje y revertir en caso de excepción.
    """
    direccion = remitente.strip().lower()
    registros = list(
        session.scalars(
            select(CorreoRemitente).where(
                CorreoRemitente.tenant_id == tenant_id,
                CorreoRemitente.direccion == direccion,
                CorreoRemitente.activo.is_(True),
            )
        )
    )
    gestores = {
        registro.gestor_id
        for registro in registros
        if session.scalar(
            select(Gestor.id).where(
                Gestor.id == registro.gestor_id,
                Gestor.tenant_id == tenant_id,
                Gestor.deleted_at.is_(None),
            )
        )
        is not None
    }
    if len(gestores) != 1:
        return ResultadoCorreo("REMITENTE_NO_REGISTRADO" if not gestores else "GESTOR_AMBIGUO")
    if not archivo.nombre.lower().endswith(".xml"):
        return ResultadoCorreo("REVISION_TIPO_DOCUMENTO")
    try:
        comprobante = parse_ubl(archivo.contenido)
    except UblInvalido:
        return ResultadoCorreo("REVISION_XML_INVALIDO")
    if comprobante is None:
        return ResultadoCorreo("REVISION_XML_NO_SOPORTADO")
    receptor = session.scalar(
        select(Empresa.id).where(
            Empresa.tenant_id == tenant_id,
            Empresa.ruc == comprobante.receptor.ruc,
            Empresa.autorizada.is_(True),
            Empresa.deleted_at.is_(None),
        )
    )
    if receptor is None:
        return ResultadoCorreo("RECEPTOR_NO_AUTORIZADO")
    gestor_id = next(iter(gestores))
    usuario_id = session.scalar(
        select(Gestor.usuario_id).where(
            Gestor.tenant_id == tenant_id,
            Gestor.id == gestor_id,
        )
    )
    if usuario_id is None:
        return ResultadoCorreo("GESTOR_SIN_USUARIO")
    try:
        documento: Documento = ingerir_documento(
            session,
            almacen,
            settings,
            hoy,
            tenant_id,
            archivo,
            gestor_id=gestor_id,
            usuario_id=usuario_id,
        )
    except (DocumentoDuplicado, ComprobanteYaRegistrado):
        return ResultadoCorreo("DUPLICADO")
    return ResultadoCorreo("INGRESADO", documento.id)
