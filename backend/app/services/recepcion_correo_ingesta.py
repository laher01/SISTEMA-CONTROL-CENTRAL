"""Admisión segura de adjuntos por remitente registrado.

Este servicio se invoca tras recibir el adjunto por un conector autenticado.
No descarga correos ni confirma autoría fiscal por sí mismo.
"""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import CorreoRemitente, Documento, Empresa, Gestor, Miembro
from app.services.automatizacion_documental import aplicar_automaticamente, guardar_procesamiento
from app.services.ingesta import (
    ArchivoSubido,
    ComprobanteYaRegistrado,
    DocumentoDuplicado,
    ingerir_documento,
)
from app.services.procesamiento_documental import DocumentoNoProcesable, procesar
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
    *,
    permitir_pdf_imagen: bool = False,
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
    lectura = None
    ruc_receptor = None
    if archivo.nombre.lower().endswith(".xml"):
        try:
            comprobante = parse_ubl(archivo.contenido)
        except UblInvalido:
            return ResultadoCorreo("REVISION_XML_INVALIDO")
        if comprobante is None:
            return ResultadoCorreo("REVISION_XML_NO_SOPORTADO")
        ruc_receptor = comprobante.receptor.ruc
    elif permitir_pdf_imagen:
        try:
            lectura = procesar(
                archivo.contenido, settings.max_extracted_chars, settings.max_ocr_pdf_pages
            ).a_dict()
        except DocumentoNoProcesable:
            return ResultadoCorreo("REVISION_ARCHIVO_NO_PROCESABLE")
        sugerencia = lectura.get("clasificacion_sugerida")
        if isinstance(sugerencia, dict) and sugerencia.get("tipo") in ("FACT", "RHE"):
            extraccion = lectura.get("extraccion_estructurada")
            campos = extraccion.get("campos", {}) if isinstance(extraccion, dict) else {}
            receptor_ocr = campos.get("ruc_receptor", {})
            ruc_receptor = receptor_ocr.get("valor")
            if not ruc_receptor:
                return ResultadoCorreo("REVISION_RECEPTOR_NO_IDENTIFICADO")
    else:
        return ResultadoCorreo("REVISION_TIPO_DOCUMENTO")

    if (
        ruc_receptor is not None
        and session.scalar(
            select(Empresa.id).where(
                Empresa.tenant_id == tenant_id,
                Empresa.ruc == ruc_receptor,
                Empresa.autorizada.is_(True),
                Empresa.deleted_at.is_(None),
            )
        )
        is None
    ):
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
    usuario_valido = session.scalar(
        select(Miembro.id).where(
            Miembro.id == usuario_id,
            Miembro.tenant_id == tenant_id,
            Miembro.rol == "USUARIO",
            Miembro.activo.is_(True),
            Miembro.deleted_at.is_(None),
        )
    )
    if usuario_valido is None:
        return ResultadoCorreo("USUARIO_NO_AUTORIZADO")
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
    if lectura is not None:
        try:
            with session.begin_nested():
                guardar_procesamiento(session, documento, lectura)
                resultado = aplicar_automaticamente(session, settings, hoy, documento, lectura)
        except ComprobanteYaRegistrado:
            session.delete(documento)
            return ResultadoCorreo("DUPLICADO")
        if not resultado.relacionado:
            return ResultadoCorreo(resultado.estado, documento.id)
    return ResultadoCorreo("INGRESADO", documento.id)
