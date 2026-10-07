import uuid
from datetime import date
from decimal import Decimal
from threading import Lock
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, selectinload

from app.api.deps import AlmacenDep, HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.api.errores import no_encontrado
from app.core.config import Settings
from app.enums import EstadoDocumento, Moneda, RolMiembro, TipoDocumento
from app.models import Documento, Empresa, Expediente, ahora
from app.schemas import (
    DocumentoOut,
    DocumentoVincular,
    ExpedienteAsistidoIn,
    ExpedienteAsistidoOut,
    ExpedienteOut,
    ExtraccionConfirmar,
    ProcesamientoLoteOut,
    RelacionSugeridaOut,
)
from app.services import auditoria
from app.services.aprendizaje_documental import (
    aplicar_perfiles_aprendidos,
    registrar_correccion_y_aprender,
)
from app.services.automatizacion_documental import (
    ResultadoAutomatizacion,
    aplicar_automaticamente,
    guardar_procesamiento,
    registrar_fallo,
)
from app.services.expedientes import actualizar_expediente, buscar_expediente
from app.services.ingesta import (
    ArchivoSubido,
    DocumentoDuplicado,
    ExpedienteNoEncontrado,
    crear_expediente,
    ingerir_documento,
    vincular_documento,
)
from app.services.permisos import PERMISO_ELIMINAR_REGISTROS, permiso_habilitado
from app.services.procesamiento_documental import DocumentoNoProcesable, procesar
from app.services.relaciones_documentales import sugerir_relaciones
from app.services.ubl import UblInvalido
from app.storage import AlmacenLocal

router = APIRouter(prefix="/documentos", tags=["documentos"])
_PROCESAMIENTO_LOCK = Lock()


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
    auth: OperativeAuthDep,
    archivo: Annotated[UploadFile, File()],
    tipo_documento: Annotated[TipoDocumento | None, Form()] = None,
    expediente_id: Annotated[uuid.UUID | None, Form()] = None,
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
    if auth.rol == "GESTOR":
        gestor_id = auth.gestor_id
        usuario_id = auth.usuario_id
    elif auth.rol == RolMiembro.USUARIO:
        gestor_id = None
        usuario_id = auth.usuario_id
    elif auth.rol == RolMiembro.SECRETARIA:
        if expediente_id is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Secretaría solo puede adjuntar documentos a expedientes existentes",
            )
        expediente_secretaria = session.get(Expediente, expediente_id)
        if (
            expediente_secretaria is None
            or expediente_secretaria.tenant_id != tenant_id
            or expediente_secretaria.deleted_at
        ):
            raise no_encontrado("Expediente")
        gestor_id = expediente_secretaria.gestor_id
        usuario_id = expediente_secretaria.usuario_id
    else:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo Usuario, Gestor o Secretaría puede cargar documentos operativos",
        )
    if usuario_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La sesión no tiene un Usuario propietario")
    if expediente_id is not None:
        expediente = session.get(Expediente, expediente_id)
        if expediente is None or expediente.tenant_id != tenant_id or expediente.deleted_at:
            raise no_encontrado("Expediente")
        _validar_ambito_expediente(auth, expediente)
        # Los adjuntos heredan siempre la propiedad del expediente.
        usuario_id = expediente.usuario_id
        gestor_id = expediente.gestor_id

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
            usuario_id,
        )
        if settings.procesamiento_automatico and _es_procesable(documento):
            try:
                _procesar_y_aplicar(session, settings, almacen, hoy, documento)
            except DocumentoNoProcesable as exc:
                registrar_fallo(session, documento, str(exc))
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
    auth: OperativeAuthDep,
    estado: EstadoDocumento | None = None,
    tipo_documento: TipoDocumento | None = None,
    expediente_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    emisor_ruc: Annotated[str | None, Query(min_length=11, max_length=11)] = None,
    receptor_ruc: Annotated[str | None, Query(min_length=11, max_length=11)] = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Documento]:
    consulta = (
        select(Documento)
        .options(
            selectinload(Documento.expediente).selectinload(Expediente.emisor),
            selectinload(Documento.expediente).selectinload(Expediente.receptor),
        )
        .where(Documento.tenant_id == tenant_id, Documento.deleted_at.is_(None))
    )
    consulta = _aplicar_ambito_documentos(consulta, auth)
    if estado is not None:
        consulta = consulta.where(Documento.estado == estado)
    if tipo_documento is not None:
        consulta = consulta.where(Documento.tipo_documento == tipo_documento)
    if expediente_id is not None:
        consulta = consulta.where(Documento.expediente_id == expediente_id)
    if usuario_id is not None:
        consulta = consulta.where(Documento.usuario_id == usuario_id)
    if gestor_id is not None:
        consulta = consulta.where(Documento.gestor_id == gestor_id)
    if fecha_desde is not None:
        consulta = consulta.where(func.date(Documento.created_at) >= fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.where(func.date(Documento.created_at) <= fecha_hasta)

    if emisor_ruc is not None or receptor_ruc is not None:
        consulta = consulta.join(Expediente, Documento.expediente_id == Expediente.id)
        if emisor_ruc is not None:
            emisor = aliased(Empresa)
            consulta = consulta.join(emisor, Expediente.emisor_id == emisor.id).where(
                emisor.ruc == emisor_ruc
            )
        if receptor_ruc is not None:
            receptor = aliased(Empresa)
            consulta = consulta.join(receptor, Expediente.receptor_id == receptor.id).where(
                receptor.ruc == receptor_ruc
            )

    consulta = consulta.order_by(Documento.created_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(consulta))


def _documento(session: SessionDep, tenant_id: uuid.UUID, documento_id: uuid.UUID) -> Documento:
    documento = session.get(Documento, documento_id)
    if documento is None or documento.tenant_id != tenant_id or documento.deleted_at:
        raise no_encontrado("Documento")
    return documento


def _validar_ambito_documento(auth: OperativeAuthDep, documento: Documento) -> None:
    if auth.rol == "GESTOR" and documento.gestor_id != auth.gestor_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    if auth.rol == RolMiembro.USUARIO and documento.usuario_id != auth.usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")


def _validar_ambito_expediente(auth: OperativeAuthDep, expediente: Expediente) -> None:
    if auth.rol == "GESTOR" and expediente.gestor_id != auth.gestor_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    if auth.rol == RolMiembro.USUARIO and expediente.usuario_id != auth.usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")


def _aplicar_ambito_documentos(consulta: Any, auth: OperativeAuthDep) -> Any:
    if auth.rol == "GESTOR":
        return consulta.where(Documento.gestor_id == auth.gestor_id)
    if auth.rol == RolMiembro.USUARIO:
        return consulta.where(Documento.usuario_id == auth.usuario_id)
    return consulta


@router.get("/{documento_id}", response_model=DocumentoOut)
def obtener_documento(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
) -> Documento:
    documento = _documento(session, tenant_id, documento_id)
    _validar_ambito_documento(auth, documento)
    return documento


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_documento(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
) -> None:
    documento = _documento(session, tenant_id, documento_id)
    _validar_ambito_documento(auth, documento)
    if not permiso_habilitado(
        session,
        tenant_id,
        auth.rol,
        PERMISO_ELIMINAR_REGISTROS,
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No tiene permiso para eliminar registros",
        )
    expediente = documento.expediente
    documento.deleted_at = ahora()
    auditoria.registrar(
        session,
        tenant_id,
        "DOCUMENTO_ELIMINADO",
        "documento",
        documento.id,
        {
            "nombre_original": documento.nombre_original,
            "sha256": documento.sha256,
            "expediente_id": str(documento.expediente_id) if documento.expediente_id else None,
            "tipo_documento": documento.tipo_documento,
        },
    )
    if expediente is not None:
        actualizar_expediente(session, expediente, hoy, settings)
    session.commit()


MIME_EN_LINEA = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "image/gif", "image/webp", "text/plain"}
)


@router.get("/{documento_id}/archivo")
def descargar_archivo(
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
) -> FileResponse:
    documento = _documento(session, tenant_id, documento_id)
    _validar_ambito_documento(auth, documento)
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
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
) -> Documento:
    documento = _documento(session, tenant_id, documento_id)
    _validar_ambito_documento(auth, documento)
    try:
        _procesar_y_aplicar(session, settings, almacen, hoy, documento)
    except DocumentoNoProcesable as exc:
        registrar_fallo(session, documento, str(exc))
        session.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    session.commit()
    return documento


@router.post("/procesar-pendientes", response_model=ProcesamientoLoteOut)
def procesar_pendientes(
    session: SessionDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    forzar: bool = False,
    sin_expediente: bool = False,
    completar_partes: bool = False,
) -> ProcesamientoLoteOut:
    """Procesa secuencialmente documentos existentes para proteger VPS pequeñas."""
    consulta = select(Documento).where(
        Documento.tenant_id == tenant_id,
        Documento.deleted_at.is_(None),
    )
    consulta = _aplicar_ambito_documentos(consulta, auth)
    if completar_partes:
        emisor_empresa = aliased(Empresa)
        receptor_empresa = aliased(Empresa)
        consulta = (
            consulta.outerjoin(Expediente, Documento.expediente_id == Expediente.id)
            .outerjoin(emisor_empresa, Expediente.emisor_id == emisor_empresa.id)
            .outerjoin(receptor_empresa, Expediente.receptor_id == receptor_empresa.id)
            .where(
                or_(
                    Documento.expediente_id.is_(None),
                    emisor_empresa.razon_social == emisor_empresa.ruc,
                    receptor_empresa.razon_social == receptor_empresa.ruc,
                )
            )
        )
    elif sin_expediente:
        consulta = consulta.where(Documento.expediente_id.is_(None))
    else:
        consulta = consulta.where(
            Documento.estado.in_(
                [EstadoDocumento.PENDIENTE_CLASIFICACION, EstadoDocumento.PENDIENTE_RELACION]
            )
        )
    consulta = consulta.order_by(Documento.created_at.asc()).limit(200)
    candidatos = list(session.scalars(consulta))
    documentos = [
        documento
        for documento in candidatos
        if forzar or not _automatizacion_ya_evaluada(documento)
    ][:limit]
    relacionados = revision = fallidos = 0
    for documento in documentos:
        try:
            resultado = _procesar_y_aplicar(
                session,
                settings,
                almacen,
                hoy,
                documento,
                reutilizar=not forzar,
            )
        except DocumentoNoProcesable as exc:
            resultado = registrar_fallo(session, documento, str(exc))
        if resultado.relacionado:
            relacionados += 1
        elif resultado.estado == "FALLIDO":
            fallidos += 1
        else:
            revision += 1
        session.commit()
    return ProcesamientoLoteOut(
        considerados=len(documentos),
        relacionados=relacionados,
        revision_requerida=revision,
        fallidos=fallidos,
    )


def _procesar_y_aplicar(
    session: Session,
    settings: Settings,
    almacen: AlmacenLocal,
    hoy: date,
    documento: Documento,
    reutilizar: bool = False,
) -> ResultadoAutomatizacion:
    datos = documento.datos_extraidos or {}
    existente = datos.get("procesamiento_documental")
    if reutilizar and isinstance(existente, dict):
        procesamiento = existente
    else:
        contenido = almacen.ruta_absoluta(documento.ruta_storage).read_bytes()
        with _PROCESAMIENTO_LOCK:
            procesamiento = procesar(
                contenido, settings.max_extracted_chars, settings.max_ocr_pdf_pages
            ).a_dict()
        aplicar_perfiles_aprendidos(session, documento, procesamiento)
        guardar_procesamiento(session, documento, procesamiento)
    return aplicar_automaticamente(session, settings, hoy, documento, procesamiento)


def _es_procesable(documento: Documento) -> bool:
    nombre = documento.nombre_original.lower()
    return documento.mime_type.startswith(("application/pdf", "image/")) or nombre.endswith(
        (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")
    )


def _automatizacion_ya_evaluada(documento: Documento) -> bool:
    datos = documento.datos_extraidos or {}
    automatizacion = datos.get("automatizacion_documental")
    return isinstance(automatizacion, dict) and automatizacion.get("estado") in {
        "REVISION_REQUERIDA",
        "FALLIDO",
    }


@router.put("/{documento_id}/extraccion-confirmada", response_model=DocumentoOut)
def confirmar_extraccion(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
    confirmacion: ExtraccionConfirmar,
) -> Documento:
    documento = _documento(session, tenant_id, documento_id)
    _validar_ambito_documento(auth, documento)
    campos = confirmacion.model_dump(mode="json", exclude_none=True)
    datos = dict(documento.datos_extraidos or {})
    datos["extraccion_confirmada"] = {"version": 2, "campos": campos}
    documento.datos_extraidos = datos
    registrar_correccion_y_aprender(
        session,
        documento,
        auth.codigo,
        auth.rol,
        campos,
        motivo="Corrección o confirmación humana",
    )
    auditoria.registrar(
        session,
        tenant_id,
        "EXTRACCION_DOCUMENTAL_CONFIRMADA",
        "documento",
        documento.id,
        {"campos": sorted(campos)},
    )
    session.commit()
    return documento


@router.post("/{documento_id}/crear-expediente", response_model=ExpedienteAsistidoOut)
def crear_expediente_asistido(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
    solicitud: ExpedienteAsistidoIn,
) -> ExpedienteAsistidoOut:
    """Materializa una extracción ya confirmada y vincula su documento atómicamente."""
    documento = _documento(session, tenant_id, documento_id)
    _validar_ambito_documento(auth, documento)
    gestor_id = documento.gestor_id
    campos = _campos_confirmados(documento)
    faltantes = [
        nombre
        for nombre in (
            "serie",
            "correlativo",
            "ruc_emisor",
            "ruc_receptor",
            "fecha_emision",
            "moneda",
            "importe_total",
        )
        if nombre not in campos
    ]
    if faltantes:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"mensaje": "Faltan campos confirmados", "campos": faltantes},
        )

    tipo_documento = TipoDocumento(solicitud.tipo_comprobante.value)
    serie = str(campos["serie"])
    correlativo = str(int(str(campos["correlativo"])))
    emisor_ruc = str(campos["ruc_emisor"])
    receptor_ruc = str(campos["ruc_receptor"])
    existente = buscar_expediente(
        session,
        tenant_id,
        solicitud.tipo_comprobante,
        serie,
        correlativo,
        emisor_ruc,
        receptor_ruc,
    )
    creado = existente is None
    razon_receptor = (
        solicitud.razon_social_receptor
        or str(campos.get("razon_social_receptor", "")).strip()
        or receptor_ruc
    )
    razon_emisor = (
        solicitud.razon_social_emisor
        or str(campos.get("razon_social_emisor", "")).strip()
        or emisor_ruc
    )
    expediente = existente or crear_expediente(
        session,
        settings,
        hoy,
        tenant_id,
        receptor=(receptor_ruc, razon_receptor),
        emisor=(emisor_ruc, razon_emisor),
        tipo_comprobante=solicitud.tipo_comprobante,
        serie=serie,
        correlativo=correlativo,
        fecha_emision=date.fromisoformat(str(campos["fecha_emision"])),
        moneda=Moneda(str(campos["moneda"])),
        importe_total=Decimal(str(campos["importe_total"])),
        requiere_guia=solicitud.requiere_guia,
        gestor_id=gestor_id,
        usuario_id=documento.usuario_id,
    )
    if documento.expediente_id is not None and documento.expediente_id != expediente.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"mensaje": "El documento ya pertenece a otro expediente"},
        )
    if documento.expediente_id != expediente.id or documento.tipo_documento != tipo_documento:
        vincular_documento(session, settings, hoy, documento, expediente.id, tipo_documento)
    session.commit()
    return ExpedienteAsistidoOut(
        expediente=ExpedienteOut.model_validate(expediente),
        documento=DocumentoOut.model_validate(documento),
        creado=creado,
    )


def _campos_confirmados(documento: Documento) -> dict[str, object]:
    datos = documento.datos_extraidos or {}
    extraccion = datos.get("extraccion_confirmada")
    if not isinstance(extraccion, dict) or not isinstance(extraccion.get("campos"), dict):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Debe confirmar la extracción antes de crear el expediente",
        )
    campos = extraccion["campos"]
    return {str(clave): valor for clave, valor in campos.items()}


@router.get("/{documento_id}/relaciones-sugeridas", response_model=list[RelacionSugeridaOut])
def relaciones_sugeridas(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
) -> list[RelacionSugeridaOut]:
    documento = _documento(session, tenant_id, documento_id)
    _validar_ambito_documento(auth, documento)
    sugerencias = sugerir_relaciones(session, documento)
    if auth.rol == "GESTOR":
        sugerencias = [s for s in sugerencias if s.expediente.gestor_id == auth.gestor_id]
    elif auth.rol == RolMiembro.USUARIO:
        sugerencias = [s for s in sugerencias if s.expediente.usuario_id == auth.usuario_id]
    return [
        RelacionSugeridaOut(
            expediente=sugerencia.expediente,
            puntaje=sugerencia.puntaje,
            evidencias=list(sugerencia.evidencias),
        )
        for sugerencia in sugerir_relaciones(session, documento)
    ]


@router.post("/{documento_id}/vincular", response_model=DocumentoOut)
def vincular(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
    datos: DocumentoVincular,
) -> Documento:
    documento = _documento(session, tenant_id, documento_id)
    _validar_ambito_documento(auth, documento)
    expediente = session.get(Expediente, datos.expediente_id)
    if expediente is None or expediente.tenant_id != tenant_id or expediente.deleted_at:
        raise no_encontrado("Expediente")
    _validar_ambito_expediente(auth, expediente)
    try:
        vincular_documento(
            session, settings, hoy, documento, datos.expediente_id, datos.tipo_documento
        )
    except ExpedienteNoEncontrado as exc:
        raise no_encontrado("Expediente") from exc
    session.commit()
    return documento
