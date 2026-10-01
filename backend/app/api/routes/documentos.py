import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AlmacenDep, HoyDep, SessionDep, SettingsDep, TenantDep
from app.api.errores import no_encontrado, validar_gestor
from app.enums import EstadoDocumento, TipoDocumento
from app.models import Documento
from app.schemas import DocumentoOut, DocumentoVincular
from app.services import auditoria
from app.services.ingesta import (
    ArchivoSubido,
    DocumentoDuplicado,
    ExpedienteNoEncontrado,
    ingerir_documento,
    vincular_documento,
)
from app.services.procesamiento_documental import DocumentoNoProcesable, procesar
from app.services.ubl import UblInvalido

router = APIRouter(prefix="/documentos", tags=["documentos"])


def _duplicado(documento_id: uuid.UUID) -> HTTPException:
    return HTTPException(
        status.HTTP_409_CONFLICT,
        {"mensaje": "El archivo ya fue cargado", "documento_id": str(documento_id)},
    )


@router.post("", response_model=DocumentoOut, status_code=status.HTTP_201_CREATED)
async def subir_documento(
    session: SessionDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    archivo: Annotated[UploadFile, File()],
    tipo_documento: Annotated[TipoDocumento | None, Form()] = None,
    expediente_id: Annotated[uuid.UUID | None, Form()] = None,
    gestor_id: Annotated[uuid.UUID | None, Form()] = None,
) -> Documento:
    limite = settings.max_upload_mb * 1024 * 1024
    contenido = await archivo.read(limite + 1)
    if len(contenido) > limite:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Archivo demasiado grande")
    if not contenido:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Archivo vacío")
    if expediente_id is not None and tipo_documento is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "tipo_documento es obligatorio al indicar expediente_id",
        )
    validar_gestor(session, tenant_id, gestor_id)
    subido = ArchivoSubido(
        nombre=archivo.filename or "sin_nombre",
        mime_type=archivo.content_type or "application/octet-stream",
        contenido=contenido,
    )
    try:
        documento = ingerir_documento(
            session,
            almacen,
            settings,
            hoy,
            tenant_id,
            subido,
            tipo_documento,
            expediente_id,
            gestor_id,
        )
        session.commit()
    except DocumentoDuplicado as exc:
        raise _duplicado(exc.documento_id) from exc
    except ExpedienteNoEncontrado as exc:
        raise no_encontrado("Expediente") from exc
    except UblInvalido as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto al registrar") from exc
    return documento


@router.get("", response_model=list[DocumentoOut])
def listar_documentos(
    session: SessionDep,
    tenant_id: TenantDep,
    estado: EstadoDocumento | None = None,
    expediente_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Documento]:
    consulta = select(Documento).where(
        Documento.tenant_id == tenant_id, Documento.deleted_at.is_(None)
    )
    if estado is not None:
        consulta = consulta.where(Documento.estado == estado)
    if expediente_id is not None:
        consulta = consulta.where(Documento.expediente_id == expediente_id)
    consulta = consulta.order_by(Documento.created_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(consulta))


def _documento(session: SessionDep, tenant_id: uuid.UUID, documento_id: uuid.UUID) -> Documento:
    documento = session.get(Documento, documento_id)
    if documento is None or documento.tenant_id != tenant_id or documento.deleted_at:
        raise no_encontrado("Documento")
    return documento


@router.get("/{documento_id}", response_model=DocumentoOut)
def obtener_documento(
    session: SessionDep, tenant_id: TenantDep, documento_id: uuid.UUID
) -> Documento:
    return _documento(session, tenant_id, documento_id)


MIME_EN_LINEA = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "image/gif", "image/webp", "text/plain"}
)


@router.get("/{documento_id}/archivo")
def descargar_archivo(
    session: SessionDep, almacen: AlmacenDep, tenant_id: TenantDep, documento_id: uuid.UUID
) -> FileResponse:
    documento = _documento(session, tenant_id, documento_id)
    en_linea = documento.mime_type in MIME_EN_LINEA
    return FileResponse(
        almacen.ruta_absoluta(documento.ruta_storage),
        media_type=documento.mime_type if en_linea else "application/octet-stream",
        filename=documento.nombre_original,
        content_disposition_type="inline" if en_linea else "attachment",
        headers={"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/{documento_id}/procesar", response_model=DocumentoOut)
def procesar_documento(
    session: SessionDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    documento_id: uuid.UUID,
) -> Documento:
    documento = _documento(session, tenant_id, documento_id)
    contenido = almacen.ruta_absoluta(documento.ruta_storage).read_bytes()
    try:
        resultado = procesar(contenido, settings.max_extracted_chars)
    except DocumentoNoProcesable as exc:
        auditoria.registrar(
            session,
            tenant_id,
            "PROCESAMIENTO_DOCUMENTAL_FALLIDO",
            "documento",
            documento.id,
            {"motivo": str(exc)},
        )
        session.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    datos = dict(documento.datos_extraidos or {})
    datos["procesamiento_documental"] = resultado.a_dict()
    documento.datos_extraidos = datos
    auditoria.registrar(
        session,
        tenant_id,
        "PROCESAMIENTO_DOCUMENTAL_COMPLETADO",
        "documento",
        documento.id,
        {
            "metodo": resultado.metodo,
            "motor": resultado.motor,
            "requiere_ocr": resultado.requiere_ocr,
        },
    )
    session.commit()
    return documento


@router.post("/{documento_id}/vincular", response_model=DocumentoOut)
def vincular(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    documento_id: uuid.UUID,
    datos: DocumentoVincular,
) -> Documento:
    documento = _documento(session, tenant_id, documento_id)
    try:
        vincular_documento(
            session, settings, hoy, documento, datos.expediente_id, datos.tipo_documento
        )
    except ExpedienteNoEncontrado as exc:
        raise no_encontrado("Expediente") from exc
    session.commit()
    return documento
