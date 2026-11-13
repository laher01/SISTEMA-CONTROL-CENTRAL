"""Lector IMAP de adjuntos XML para buzones previamente autorizados.

Ejecutar periódicamente en un worker, no dentro del proceso HTTP.
Las credenciales solo se suministran por variables de entorno.
"""

import email
import imaplib
import os
import uuid
from email.policy import default
from email.utils import parseaddr
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import CorreoBuzon, CorreoMensaje, CorreoRemitente, Gestor
from app.services.ingesta import ArchivoSubido
from app.services.paquetes_correo import FORMATOS, PaqueteNoSeguro, extraer_documentos_paquete
from app.services.procesamiento_documental import DocumentoNoProcesable
from app.services.recepcion_correo_ingesta import admitir_adjunto_ubl
from app.services.separador_pdf import analizar_paquete, extraer_fragmento
from app.storage import AlmacenLocal

MAX_MENSAJE_BYTES = 25 * 1024 * 1024


def _adjuntos_xml(contenido: bytes, *, solo_xml: bool = True) -> tuple[str, list[ArchivoSubido]]:
    mensaje = email.message_from_bytes(contenido, policy=default)
    remitente = parseaddr(str(mensaje.get("From", "")))[1].lower()
    adjuntos: list[ArchivoSubido] = []
    for parte in mensaje.walk():
        if parte.is_multipart():
            continue
        nombre = parte.get_filename()
        if not nombre:
            continue
        extension = PurePosixPath(nombre).suffix.lower()
        if extension not in {*FORMATOS, ".zip", ".rar"}:
            continue
        if solo_xml and extension not in (".xml", ".zip"):
            continue
        archivo = parte.get_payload(decode=True)
        if not isinstance(archivo, bytes) or len(archivo) > MAX_MENSAJE_BYTES:
            raise PaqueteNoSeguro("Adjunto demasiado grande")
        documentos = (
            extraer_documentos_paquete(archivo, extension, solo_xml=solo_xml)
            if extension in (".zip", ".rar")
            else [(nombre, archivo)]
        )
        for nombre_documento, datos in documentos:
            mime = FORMATOS[PurePosixPath(nombre_documento).suffix.lower()]
            adjuntos.append(ArchivoSubido(nombre_documento, mime, datos))
        if len(adjuntos) > 100 or sum(len(a.contenido) for a in adjuntos) > MAX_MENSAJE_BYTES:
            raise PaqueteNoSeguro("El mensaje excede el límite de adjuntos extraídos")
    return remitente, adjuntos


def _separar_adjuntos(archivos: list[ArchivoSubido]) -> list[ArchivoSubido]:
    salida = []
    for archivo in archivos:
        if archivo.mime_type != "application/pdf":
            salida.append(archivo)
            continue
        try:
            segmentos = analizar_paquete(archivo.contenido, max_paginas=50, recepcion_correo=True)
        except DocumentoNoProcesable:
            salida.append(archivo)
            continue
        for segmento in segmentos:
            nombre = f"{PurePosixPath(archivo.nombre).stem}-{segmento.inicio + 1}.pdf"
            salida.append(
                ArchivoSubido(
                    nombre, archivo.mime_type, extraer_fragmento(archivo.contenido, segmento)
                )
            )
    if len(salida) > 100 or sum(len(a.contenido) for a in salida) > MAX_MENSAJE_BYTES:
        raise PaqueteNoSeguro("El PDF separado excede el límite de adjuntos")
    return salida


def procesar_mensaje(
    session: Session,
    settings: Settings,
    buzon: CorreoBuzon,
    uid: str,
    contenido: bytes,
) -> str:
    """Registra UID incluso cuando no hay adjuntos; así no reprocesa el correo."""
    existente = session.scalar(
        select(CorreoMensaje.id).where(
            CorreoMensaje.tenant_id == buzon.tenant_id,
            CorreoMensaje.buzon_id == buzon.id,
            CorreoMensaje.identificador_externo == uid,
        )
    )
    if existente is not None:
        return "DUPLICADO_MENSAJE"
    mensaje = email.message_from_bytes(contenido, policy=default)
    remitente = parseaddr(str(mensaje.get("From", "")))[1].lower()
    candidatos = set(
        session.scalars(
            select(CorreoRemitente.gestor_id)
            .join(Gestor, CorreoRemitente.gestor_id == Gestor.id)
            .where(
                CorreoRemitente.tenant_id == buzon.tenant_id,
                CorreoRemitente.direccion == remitente,
                CorreoRemitente.activo.is_(True),
                Gestor.tenant_id == buzon.tenant_id,
                Gestor.deleted_at.is_(None),
            )
        )
    )
    gestor_id = next(iter(candidatos)) if len(candidatos) == 1 else None
    registro = CorreoMensaje(
        tenant_id=buzon.tenant_id,
        buzon_id=buzon.id,
        identificador_externo=uid,
        remitente=remitente,
        gestor_id=gestor_id,
        estado="PENDIENTE",
    )
    session.add(registro)
    if gestor_id is None:
        registro.estado = "REVISION"
        registro.error = "REMITENTE_NO_REGISTRADO" if not candidatos else "GESTOR_AMBIGUO"
        session.commit()
        return registro.estado
    try:
        _, archivos = _adjuntos_xml(contenido, solo_xml=False)
        archivos = _separar_adjuntos(archivos)
    except PaqueteNoSeguro:
        registro.estado = "REVISION"
        registro.error = "PAQUETE_NO_SEGURO"
        session.commit()
        return registro.estado
    resultados = []
    hoy = settings.hoy()
    almacen = AlmacenLocal(settings.storage_dir)
    for archivo in sorted(archivos, key=lambda a: a.mime_type != "application/xml"):
        with session.begin_nested():
            resultado = admitir_adjunto_ubl(
                session,
                almacen,
                settings,
                hoy,
                buzon.tenant_id,
                remitente,
                archivo,
                permitir_pdf_imagen=True,
            )
            resultados.append(resultado.estado)
    registro.estado = (
        "INGRESADO" if "INGRESADO" in resultados else "REVISION" if resultados else "SIN_ADJUNTOS"
    )
    registro.error = ",".join(resultados)[:500] if resultados else None
    session.commit()
    return registro.estado


def consultar_buzon(
    session: Session, settings: Settings, buzon_id: uuid.UUID, *, limite: int = 30
) -> int:
    """Usa TLS con validación por defecto y UIDs persistentes por buzón."""
    buzon = session.get(CorreoBuzon, buzon_id)
    if buzon is None or not buzon.activo:
        raise ValueError("Buzón inexistente o inactivo")
    clave = "FC_IMAP_" + buzon.id.hex.upper()
    host = os.environ.get(clave + "_HOST", "")
    usuario = os.environ.get(clave + "_USER", "")
    password = os.environ.get(clave + "_PASSWORD", "")
    if not (host and usuario and password):
        raise ValueError("Configuración IMAP incompleta para el buzón")
    puerto = int(os.environ.get(clave + "_PORT", "993"))
    procesados = 0
    with imaplib.IMAP4_SSL(host, puerto) as conexion:
        conexion.login(usuario, password)
        estado, _ = conexion.select("INBOX", readonly=True)
        if estado != "OK":
            raise RuntimeError("No se pudo seleccionar el buzón")
        estado, encontrados = conexion.uid("search", "", "ALL")
        if estado != "OK":
            raise RuntimeError("No se pudo consultar el buzón")
        uids = encontrados[0].split()[-max(1, min(limite, 100)) :]
        for uid_bytes in uids:
            uid = uid_bytes.decode("ascii")
            estado, respuesta = conexion.uid("fetch", uid, "(RFC822)")
            if estado != "OK":
                continue
            partes = [item[1] for item in respuesta if isinstance(item, tuple)]
            if not partes or not isinstance(partes[0], bytes):
                continue
            if len(partes[0]) > MAX_MENSAJE_BYTES:
                continue
            try:
                procesar_mensaje(session, settings, buzon, uid, partes[0])
                procesados += 1
            except Exception:
                session.rollback()
                raise
    return procesados
