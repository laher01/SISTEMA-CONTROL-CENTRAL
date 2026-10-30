import hashlib
import io
import uuid
from datetime import date
from decimal import Decimal
from threading import Lock
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pypdf import PdfReader
from sqlalchemy import and_, case, delete, false, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, selectinload

from app.api.deps import AlmacenDep, HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.api.errores import no_encontrado
from app.core.config import Settings
from app.enums import EstadoDocumento, Moneda, RolMiembro, TipoDocumento
from app.models import (
    Alerta,
    AlertaManual,
    Auditoria,
    ChatMensaje,
    CorreccionIA,
    CuentaAcceso,
    Documento,
    EliminacionArchivoPendiente,
    Empresa,
    Expediente,
    Gestor,
    Miembro,
    ReferenciaGRE,
    RelacionDocumento,
    SolicitudCargaEmisor,
    SolicitudRetiroMISD,
)
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
from app.security import cuenta_administradora_responsable
from app.services import auditoria
from app.services.ambito_emisor import EstadoAmbitoEmisor, revisar_asignaciones_emisor
from app.services.ambito_gerencia import alcance_expedientes_gerente, expediente_visible_gerente
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
from app.services.cache_ocr import eliminar_cache_ocr, procesar_con_cache
from app.services.eliminacion import (
    bloquear_clave_archivo,
    procesar_archivo_pendiente,
)
from app.services.expedientes import (
    actualizar_expediente,
    buscar_expediente,
    eliminar_expediente_vacio,
)
from app.services.identidad_cotizaciones import identidad_cotizacion
from app.services.ingesta import (
    ArchivoSubido,
    ComprobanteYaRegistrado,
    DocumentoDuplicado,
    ExpedienteNoEncontrado,
    crear_expediente,
    ingerir_documento,
    vincular_documento,
)
from app.services.jerarquia_documental import nombres_jerarquia
from app.services.lotes_imagenes import MAX_IMAGENES_POR_SUBLOTE
from app.services.metadatos_documento import metadatos_individuales
from app.services.permisos import (
    PERMISO_ELIMINAR_REGISTROS,
    permiso_habilitado,
)
from app.services.procesamiento_documental import DocumentoNoProcesable, procesar
from app.services.relaciones_documentales import sugerir_relaciones
from app.services.separador_pdf import analizar_paquete, extraer_fragmento
from app.services.ubl import UblInvalido, parece_xml, parse_ubl
from app.storage import AlmacenLocal

router = APIRouter(prefix="/documentos", tags=["documentos"])
_PROCESAMIENTO_LOCK = Lock()


def _duplicado(
    session: SessionDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
) -> HTTPException:
    documento = session.get(Documento, documento_id)
    detalle: dict[str, object] = {
        "mensaje": "El archivo ya fue cargado en este administrador",
        "duplicado": True,
    }
    if documento is not None and (
        auth.rol in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR, RolMiembro.SECRETARIA)
        or (auth.rol == RolMiembro.USUARIO and auth.usuario_id == documento.usuario_id)
        or (auth.rol == "GESTOR" and auth.gestor_id == documento.gestor_id)
    ):
        detalle["documento_id"] = str(documento.id)
    return HTTPException(status.HTTP_409_CONFLICT, detalle)


def _comprobante_duplicado(
    session: SessionDep,
    auth: OperativeAuthDep,
    expediente_id: uuid.UUID,
) -> HTTPException:
    expediente = session.get(Expediente, expediente_id)
    if expediente is None:
        return HTTPException(status.HTTP_409_CONFLICT, "Comprobante ya registrado")
    detalles: dict[str, object] = {
        "mensaje": "Esta factura ya fue registrada en este administrador. Coordine su revisión.",
        "duplicado": True,
    }
    autorizado = (
        auth.rol in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR, RolMiembro.SECRETARIA)
        or (auth.rol == RolMiembro.USUARIO and expediente.usuario_id == auth.usuario_id)
        or (auth.rol == "GESTOR" and expediente.gestor_id == auth.gestor_id)
    )
    if autorizado:
        usuario = session.get(Miembro, expediente.usuario_id) if expediente.usuario_id else None
        gestor = session.get(Gestor, expediente.gestor_id) if expediente.gestor_id else None
        detalles["mensaje"] = (
            f"Factura duplicada: {expediente.serie}-{expediente.correlativo}. "
            f"Monto: {expediente.moneda} {expediente.importe_total}. "
            f"Usuario: {usuario.nombre if usuario else 'Sin usuario'}. "
            f"Gestor: {gestor.nombre if gestor else 'Sin gestor'}. "
            f"Fecha de registro: {expediente.created_at.date().isoformat()}."
        )
        detalles["expediente_id"] = str(expediente.id)
    return HTTPException(status.HTTP_409_CONFLICT, detalles)


@router.post("/paquete")
async def importar_paquete_pdf(
    session: SessionDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    archivo: Annotated[UploadFile, File()],
    confirmar: Annotated[bool, Form()] = False,
    indices_documentos: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    """Primero previsualiza; únicamente con confirmar=true ingiere documentos.

    Se mantiene la deduplicación existente por SHA y clave fiscal.
    Cada comprobante tiene su propia transacción; un error no borra otros.
    """
    if auth.rol != "GESTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Gestor puede cargar documentos")
    if auth.usuario_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La sesión no tiene Usuario propietario")
    limite = settings.max_upload_mb * 1024 * 1024
    contenido = await archivo.read(limite + 1)
    if len(contenido) > limite:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Paquete demasiado grande")
    if not contenido.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Se requiere un PDF válido")
    try:
        segmentos = analizar_paquete(contenido)
    except DocumentoNoProcesable as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if not confirmar:
        return {
            "modo": "vista_previa",
            "total": len(segmentos),
            "documentos": [segmento.descripcion() for segmento in segmentos],
        }

    # Los índices provienen de la vista previa; nunca confiar en el cliente
    # para introducir páginas o documentos que no detectó el separador.
    if indices_documentos is not None:
        try:
            seleccion = {int(valor.strip()) for valor in indices_documentos.split(",")}
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Selección de documentos inválida"
            ) from exc
        if not seleccion or any(indice < 0 or indice >= len(segmentos) for indice in seleccion):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Selección fuera del paquete analizado"
            )
        segmentos = [segmento for indice, segmento in enumerate(segmentos) if indice in seleccion]

    # Un paquete comercial conserva su original en la misma área documental.
    # La huella binaria permite reutilizarlo si se repite la importación.
    paquete_original: Documento | None = None
    if any(segmento.tipo == "COT" for segmento in segmentos):
        sha_paquete = hashlib.sha256(contenido).hexdigest()
        paquete_original = session.scalar(
            select(Documento).where(
                Documento.tenant_id == tenant_id,
                Documento.sha256 == sha_paquete,
                Documento.deleted_at.is_(None),
            )
        )
        if paquete_original is not None and (
            paquete_original.usuario_id != auth.usuario_id
            or (auth.rol == "GESTOR" and paquete_original.gestor_id != auth.gestor_id)
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Paquete original fuera de su ámbito")
        if paquete_original is None:
            try:
                paquete_original = ingerir_documento(
                    session,
                    almacen,
                    settings,
                    hoy,
                    tenant_id,
                    ArchivoSubido(
                        nombre=archivo.filename or "paquete_cotizaciones.pdf",
                        mime_type="application/pdf",
                        contenido=contenido,
                    ),
                    TipoDocumento.OTRO,
                    None,
                    auth.gestor_id if auth.rol == "GESTOR" else None,
                    auth.usuario_id,
                    cuenta_administradora_responsable(session, auth),
                )
                session.commit()
            except DocumentoDuplicado:
                session.rollback()
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "Paquete original duplicado; vuelva a analizar"
                ) from None

    resultados: list[dict[str, object]] = []
    for segmento in segmentos:
        clave = segmento.descripcion()
        nombre = (
            f"{segmento.ruc_emisor}-{segmento.tipo}-{segmento.serie}-{segmento.correlativo}.pdf"
        )
        try:
            subido = ArchivoSubido(
                nombre=nombre,
                mime_type="application/pdf",
                contenido=extraer_fragmento(contenido, segmento),
            )
            documento = ingerir_documento(
                session,
                almacen,
                settings,
                hoy,
                tenant_id,
                subido,
                TipoDocumento.COT if segmento.tipo == "COT" else None,
                None,
                auth.gestor_id if auth.rol == "GESTOR" else None,
                auth.usuario_id,
                cuenta_administradora_responsable(session, auth),
            )
            if segmento.tipo == "COT" and paquete_original is not None:
                lector_individual = PdfReader(io.BytesIO(subido.contenido))
                texto_cotizacion = "\n".join(
                    pagina.extract_text() or "" for pagina in lector_individual.pages
                )
                identidad = identidad_cotizacion(texto_cotizacion, segmento.correlativo)
                documento.huella_comercial = identidad["huella"]
                documento.datos_extraidos = {
                    "origen_paquete": {
                        "documento_padre_id": str(paquete_original.id),
                        "sha256_original": paquete_original.sha256,
                        "pagina_inicio": segmento.inicio + 1,
                        "pagina_fin": segmento.fin,
                    },
                    "cotizacion": {
                        "numero": segmento.correlativo,
                        "identidad": identidad,
                        "estado_identidad": identidad["estado"],
                    },
                }
                session.add(
                    RelacionDocumento(
                        tenant_id=tenant_id,
                        origen_id=paquete_original.id,
                        destino_id=documento.id,
                        tipo="ORIGEN_PAQUETE",
                        evidencia=(f"Paginas {segmento.inicio + 1}-{segmento.fin}"),
                        confirmado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
                    )
                )
                auditoria.registrar(
                    session,
                    tenant_id,
                    "COTIZACION_SEPARADA",
                    "documento",
                    documento.id,
                    {"documento_padre_id": str(paquete_original.id)},
                )
            # Conservar cotizaciones como evidencia comercial, no como expediente fiscal.
            if segmento.tipo == "COT" and settings.procesamiento_automatico:
                try:
                    lectura = procesar(
                        subido.contenido,
                        settings.max_extracted_chars,
                        settings.max_ocr_pdf_pages,
                    )
                    guardar_procesamiento(session, documento, lectura.a_dict())
                except DocumentoNoProcesable as exc:
                    registrar_fallo(session, documento, str(exc))
            if (
                segmento.tipo != "COT"
                and settings.procesamiento_automatico
                and _es_procesable(documento)
            ):
                try:
                    _procesar_y_aplicar(session, settings, almacen, hoy, documento)
                except DocumentoNoProcesable as exc:
                    registrar_fallo(session, documento, str(exc))
            session.commit()
            resultados.append(
                {
                    **clave,
                    "estado": "relacionado" if documento.expediente_id else "revision",
                    "documento_id": str(documento.id),
                    "expediente_id": str(documento.expediente_id)
                    if documento.expediente_id
                    else None,
                }
            )
        except (DocumentoDuplicado, ComprobanteYaRegistrado):
            session.rollback()
            resultados.append({**clave, "estado": "duplicado"})
        except IntegrityError as exc:
            session.rollback()
            if "huella_comercial" in str(exc.orig).lower():
                resultados.append({**clave, "estado": "duplicado"})
            else:
                resultados.append(
                    {**clave, "estado": "error", "detalle": "Conflicto de integridad"}
                )
        except (UblInvalido, DocumentoNoProcesable) as exc:
            session.rollback()
            resultados.append({**clave, "estado": "error", "detalle": str(exc)})
    return {
        "modo": "importado",
        "total": len(segmentos),
        "relacionados": sum(x["estado"] == "relacionado" for x in resultados),
        "revision": sum(x["estado"] == "revision" for x in resultados),
        "duplicados": sum(x["estado"] == "duplicado" for x in resultados),
        "errores": sum(x["estado"] == "error" for x in resultados),
        "documentos": resultados,
    }


@router.post("/lote-imagenes")
async def subir_sublote_imagenes(
    session: SessionDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    archivos: Annotated[list[UploadFile], File()],
) -> dict[str, object]:
    """Procesa hasta diez imágenes secuencialmente reutilizando permisos y deduplicación.

    Cada archivo es independiente: un duplicado o un fallo no cancela los
    documentos que ya fueron registrados correctamente en el mismo sublote.
    El endpoint no agrupa páginas en una factura; eso exige revisión del usuario.
    """
    if auth.rol != "GESTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Gestor puede cargar documentos")
    if not 1 <= len(archivos) <= MAX_IMAGENES_POR_SUBLOTE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Cada sublote debe contener entre 1 y 10 imágenes",
        )
    # El límite acumulado evita una solicitud que multiplique hasta diez veces
    # el consumo permitido para un documento individual.
    limite_acumulado = settings.max_upload_mb * 1024 * 1024 * MAX_IMAGENES_POR_SUBLOTE
    tamanos = [getattr(archivo, "size", None) for archivo in archivos]
    if (
        all(isinstance(tamano, int) for tamano in tamanos)
        and sum(tamano for tamano in tamanos if isinstance(tamano, int)) > limite_acumulado
    ):
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Sublote demasiado grande")
    resultados: list[dict[str, object]] = []
    for indice, archivo in enumerate(archivos):
        cabecera = await archivo.read(12)
        await archivo.seek(0)
        firma_valida = (
            cabecera.startswith(b"\xff\xd8\xff")
            or cabecera.startswith(b"\x89PNG\r\n\x1a\n")
            or (cabecera.startswith(b"RIFF") and cabecera[8:12] == b"WEBP")
            or cabecera.startswith((b"II*\x00", b"MM\x00*"))
        )
        if not firma_valida:
            resultados.append(
                {"indice": indice, "estado": "error", "detalle": "Imagen no reconocida"}
            )
            continue
        try:
            documento = await subir_documento(
                session=session,
                settings=settings,
                almacen=almacen,
                hoy=hoy,
                tenant_id=tenant_id,
                auth=auth,
                archivo=archivo,
                tipo_documento=None,
                expediente_id=None,
            )
            resultados.append({"indice": indice, "estado": "ok", "documento_id": str(documento.id)})
        except HTTPException as exc:
            session.rollback()
            detalle = exc.detail
            es_duplicado = (
                exc.status_code == status.HTTP_409_CONFLICT
                and isinstance(detalle, dict)
                and detalle.get("duplicado") is True
            )
            estado = "duplicado" if es_duplicado else "error"
            resultados.append({"indice": indice, "estado": estado, "detalle": detalle})
    return {
        "total": len(archivos),
        "procesados": sum(x["estado"] == "ok" for x in resultados),
        "duplicados": sum(x["estado"] == "duplicado" for x in resultados),
        "errores": sum(x["estado"] == "error" for x in resultados),
        "resultados": resultados,
    }


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
    if auth.rol != "GESTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Gestor puede cargar documentos")
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
    else:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo Gestor puede cargar documentos",
        )
    if usuario_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La sesión no tiene un Usuario propietario")
    if expediente_id is not None:
        expediente = session.get(Expediente, expediente_id)
        if expediente is None or expediente.tenant_id != tenant_id or expediente.deleted_at:
            raise no_encontrado("Expediente")
        _validar_ambito_expediente(auth, expediente, session)
        # Los adjuntos heredan siempre la propiedad del expediente.
        usuario_id = expediente.usuario_id
        gestor_id = expediente.gestor_id

    subido = ArchivoSubido(
        nombre=archivo.filename or "sin_nombre",
        mime_type=archivo.content_type or "application/octet-stream",
        contenido=contenido,
    )
    # Control previo al registro: una factura/guía UBL asignada a otro
    # grupo no puede crear expediente ni incrementar montos.
    if parece_xml(subido.nombre, subido.contenido):
        try:
            ubl = parse_ubl(subido.contenido)
        except UblInvalido as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        if ubl is not None:
            revision = revisar_asignaciones_emisor(
                session, tenant_id, ubl.emisor.ruc, usuario_id, gestor_id
            )
            if revision.estado in (
                EstadoAmbitoEmisor.ASIGNADO_A_OTRO_GRUPO,
                EstadoAmbitoEmisor.AMBIGUO,
            ):
                # El registro de solicitud NO crea un Documento/Expediente.
                # El archivo permanece en área de cuarentena, fuera de los
                # listados, y solo la API de revisión puede liberarlo.
                huella = hashlib.sha256(subido.contenido).hexdigest()
                solicitud = SolicitudCargaEmisor(
                    tenant_id=tenant_id,
                    ruc_emisor=ubl.emisor.ruc,
                    empresa_id=revision.empresa_id,
                    solicitante_cuenta_id=auth.cuenta_id,
                    usuario_solicitante_id=usuario_id,
                    gestor_solicitante_id=gestor_id,
                    gestor_propietario_id=revision.gestor_propietario_id,
                    responsable_propietario_id=revision.responsable_propietario_id,
                    sha256_archivo=huella,
                    estado="PENDIENTE",
                )
                session.add(solicitud)
                session.flush()
                # Usar namespace reservado que no colisione con originales.
                solicitud.ruta_temporal = almacen.guardar(
                    tenant_id, f"cuarentena-{solicitud.id}-{huella}", subido.contenido
                )
                session.add(
                    AlertaManual(
                        tenant_id=tenant_id,
                        creado_por_codigo=auth.codigo,
                        creado_por_rol=auth.rol,
                        destinatario_usuario_id=revision.responsable_propietario_id,
                        destinatario_gestor_id=revision.gestor_propietario_id,
                        para_administracion=True,
                        asunto="Autorización de documento de empresa ajena",
                        mensaje=(
                            f"Solicitud {solicitud.id}; emisor {ubl.emisor.ruc}; "
                            f"solicitante {auth.codigo}; gestor propietario "
                            f"{revision.gestor_propietario_id}; responsable "
                            f"{revision.responsable_propietario_id}."
                        ),
                    )
                )
                auditoria.registrar(
                    session,
                    tenant_id,
                    "CARGA_EMISOR_PENDIENTE",
                    "solicitud_carga_emisor",
                    solicitud.id,
                    {"ruc_emisor": ubl.emisor.ruc, "sha256": huella},
                )
                session.commit()
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    {
                        "codigo": "EMISOR_REQUIERE_AUTORIZACION",
                        "solicitud_id": str(solicitud.id),
                        "mensaje": "Solicitud creada, pendiente de autorización",
                        "ruc_emisor": ubl.emisor.ruc,
                        "estado": revision.estado.value,
                    },
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
            cuenta_administradora_responsable(session, auth),
        )
        hubo_eliminacion_previa = (
            session.scalar(
                select(Auditoria.id)
                .where(
                    Auditoria.tenant_id == tenant_id,
                    Auditoria.accion.in_(
                        ["DOCUMENTO_ELIMINADO", "DOCUMENTO_ELIMINADO_CON_EXPEDIENTE"]
                    ),
                    Auditoria.datos["sha256"].as_string() == documento.sha256,
                )
                .limit(1)
            )
            is not None
        )
        if settings.procesamiento_automatico and _es_procesable(documento):
            try:
                _procesar_y_aplicar(
                    session,
                    settings,
                    almacen,
                    hoy,
                    documento,
                    forzar_cache=hubo_eliminacion_previa,
                )
            except DocumentoNoProcesable as exc:
                registrar_fallo(session, documento, str(exc))
        session.commit()
    except DocumentoDuplicado as exc:
        session.rollback()
        raise _duplicado(session, auth, exc.documento_id) from exc
    except ComprobanteYaRegistrado as exc:
        session.rollback()
        raise _comprobante_duplicado(session, auth, exc.expediente_id) from exc
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
    tipo_empresa: Literal["A", "B"] | None = None,
    dia: date | None = None,
    responsable_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    emisor_ruc: Annotated[str | None, Query(min_length=11, max_length=11)] = None,
    receptor_ruc: Annotated[str | None, Query(min_length=11, max_length=11)] = None,
    empresa_emisora: Annotated[str | None, Query(max_length=100)] = None,
    empresa_receptora: Annotated[str | None, Query(max_length=100)] = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    fecha_emision: date | None = None,
    mes: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
    serie_correlativo: Annotated[str | None, Query(min_length=1, max_length=60)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentoOut]:
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
    if responsable_id is not None:
        usuarios_del_responsable = select(Miembro.id).where(
            Miembro.tenant_id == tenant_id,
            Miembro.responsable_id == responsable_id,
            Miembro.rol == RolMiembro.USUARIO,
            Miembro.deleted_at.is_(None),
        )
        consulta = consulta.where(Documento.usuario_id.in_(usuarios_del_responsable))
    if usuario_id is not None:
        consulta = consulta.where(Documento.usuario_id == usuario_id)
    if gestor_id is not None:
        consulta = consulta.where(Documento.gestor_id == gestor_id)
    if (
        fecha_emision is not None
        or mes is not None
        or serie_correlativo
        or emisor_ruc is not None
        or receptor_ruc is not None
        or tipo_empresa is not None
        or empresa_emisora
        or empresa_receptora
    ):
        consulta = consulta.outerjoin(Expediente, Documento.expediente_id == Expediente.id)
    if fecha_emision is not None:
        fecha_texto = fecha_emision.isoformat()
        consulta = consulta.where(
            or_(
                and_(
                    Documento.tipo_documento.in_([TipoDocumento.FACT, TipoDocumento.RHE]),
                    Expediente.fecha_emision == fecha_emision,
                ),
                Documento.datos_extraidos["fecha_emision"].as_string() == fecha_texto,
                Documento.datos_extraidos["extraccion_confirmada"]["campos"][
                    "fecha_emision"
                ].as_string()
                == fecha_texto,
                Documento.datos_extraidos["procesamiento_documental"]["extraccion_estructurada"][
                    "campos"
                ]["fecha_emision"]["valor"].as_string()
                == fecha_texto,
            )
        )
    if mes is not None:
        consulta = consulta.where(
            or_(
                and_(
                    Documento.tipo_documento.in_([TipoDocumento.FACT, TipoDocumento.RHE]),
                    func.extract("year", Expediente.fecha_emision) == int(mes[:4]),
                    func.extract("month", Expediente.fecha_emision) == int(mes[5:7]),
                ),
                Documento.datos_extraidos["fecha_emision"].as_string().startswith(mes),
                Documento.datos_extraidos["extraccion_confirmada"]["campos"]["fecha_emision"]
                .as_string()
                .startswith(mes),
                Documento.datos_extraidos["procesamiento_documental"]["extraccion_estructurada"][
                    "campos"
                ]["fecha_emision"]["valor"]
                .as_string()
                .startswith(mes),
            )
        )
    if serie_correlativo:
        texto = serie_correlativo.strip().upper()
        if "-" in texto:
            serie, correlativo = texto.split("-", 1)
            numero = correlativo.lstrip("0") or "0"
            candidatos = [
                func.upper(Documento.nombre_original).contains(texto, autoescape=True),
                and_(
                    Documento.tipo_documento.in_([TipoDocumento.FACT, TipoDocumento.RHE]),
                    func.upper(Expediente.serie) == serie,
                    func.ltrim(Expediente.correlativo, "0") == numero,
                ),
            ]
            for ruta_serie, ruta_numero in (
                (
                    Documento.datos_extraidos["serie"].as_string(),
                    Documento.datos_extraidos["correlativo"].as_string(),
                ),
                (
                    Documento.datos_extraidos["extraccion_confirmada"]["campos"][
                        "serie"
                    ].as_string(),
                    Documento.datos_extraidos["extraccion_confirmada"]["campos"][
                        "correlativo"
                    ].as_string(),
                ),
                (
                    Documento.datos_extraidos["procesamiento_documental"][
                        "extraccion_estructurada"
                    ]["campos"]["serie"]["valor"].as_string(),
                    Documento.datos_extraidos["procesamiento_documental"][
                        "extraccion_estructurada"
                    ]["campos"]["correlativo"]["valor"].as_string(),
                ),
            ):
                candidatos.append(
                    and_(
                        func.upper(ruta_serie) == serie,
                        func.ltrim(ruta_numero, "0") == numero,
                    )
                )
            consulta = consulta.where(or_(*candidatos))
        else:
            consulta = consulta.where(
                or_(
                    func.upper(Documento.nombre_original).contains(texto, autoescape=True),
                    func.upper(Expediente.serie + "-" + Expediente.correlativo).contains(
                        texto, autoescape=True
                    ),
                )
            )
    if dia is not None:
        consulta = consulta.where(func.date(Documento.created_at) == dia)
    if fecha_desde is not None:
        consulta = consulta.where(func.date(Documento.created_at) >= fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.where(func.date(Documento.created_at) <= fecha_hasta)

    if (
        emisor_ruc is not None
        or receptor_ruc is not None
        or tipo_empresa is not None
        or empresa_emisora
        or empresa_receptora
    ):
        if emisor_ruc is not None or tipo_empresa is not None or empresa_emisora:
            emisor = aliased(Empresa)
            consulta = consulta.join(emisor, Expediente.emisor_id == emisor.id)
            if emisor_ruc is not None:
                consulta = consulta.where(emisor.ruc == emisor_ruc)
            if tipo_empresa is not None:
                consulta = consulta.where(emisor.clasificacion_proveedor == tipo_empresa)
            if empresa_emisora and empresa_emisora.strip():
                termino = empresa_emisora.strip().lower()
                consulta = consulta.where(
                    (func.lower(emisor.razon_social).contains(termino, autoescape=True))
                    | (emisor.ruc.contains(termino, autoescape=True))
                )
        if receptor_ruc is not None or empresa_receptora:
            receptor = aliased(Empresa)
            consulta = consulta.join(receptor, Expediente.receptor_id == receptor.id)
            if receptor_ruc is not None:
                consulta = consulta.where(receptor.ruc == receptor_ruc)
            if empresa_receptora and empresa_receptora.strip():
                termino = empresa_receptora.strip().lower()
                consulta = consulta.where(
                    (func.lower(receptor.razon_social).contains(termino, autoescape=True))
                    | (receptor.ruc.contains(termino, autoescape=True))
                )

    consulta = consulta.order_by(Documento.created_at.desc()).limit(limit).offset(offset)
    filas = list(session.scalars(consulta))
    jerarquias = nombres_jerarquia(session, tenant_id, filas)
    return [
        DocumentoOut.model_validate(fila).model_copy(
            update={**jerarquias[fila.id], **metadatos_individuales(fila)}
        )
        for fila in filas
    ]


@router.get("/resumen")
def resumen_documentos(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    estado: EstadoDocumento | None = None,
    tipo_documento: TipoDocumento | None = None,
    expediente_id: uuid.UUID | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
    dia: date | None = None,
    responsable_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    emisor_ruc: Annotated[str | None, Query(min_length=11, max_length=11)] = None,
    receptor_ruc: Annotated[str | None, Query(min_length=11, max_length=11)] = None,
    empresa_emisora: Annotated[str | None, Query(max_length=100)] = None,
    empresa_receptora: Annotated[str | None, Query(max_length=100)] = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    fecha_emision: date | None = None,
    mes: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
    serie_correlativo: Annotated[str | None, Query(min_length=1, max_length=60)] = None,
) -> dict[str, int | Decimal]:
    consulta = select(Documento.id, Documento.expediente_id).where(
        Documento.tenant_id == tenant_id, Documento.deleted_at.is_(None)
    )
    consulta = _aplicar_ambito_documentos(consulta, auth)
    if estado is not None:
        consulta = consulta.where(Documento.estado == estado)
    if tipo_documento is not None:
        consulta = consulta.where(Documento.tipo_documento == tipo_documento)
    if expediente_id is not None:
        consulta = consulta.where(Documento.expediente_id == expediente_id)
    if responsable_id is not None:
        usuarios_del_responsable = select(Miembro.id).where(
            Miembro.tenant_id == tenant_id,
            Miembro.responsable_id == responsable_id,
            Miembro.rol == RolMiembro.USUARIO,
            Miembro.deleted_at.is_(None),
        )
        consulta = consulta.where(Documento.usuario_id.in_(usuarios_del_responsable))
    if usuario_id is not None:
        consulta = consulta.where(Documento.usuario_id == usuario_id)
    if gestor_id is not None:
        consulta = consulta.where(Documento.gestor_id == gestor_id)
    if (
        fecha_emision is not None
        or mes is not None
        or serie_correlativo
        or emisor_ruc is not None
        or receptor_ruc is not None
        or tipo_empresa is not None
        or empresa_emisora
        or empresa_receptora
    ):
        consulta = consulta.outerjoin(Expediente, Documento.expediente_id == Expediente.id)
    if fecha_emision is not None:
        fecha_texto = fecha_emision.isoformat()
        consulta = consulta.where(
            or_(
                and_(
                    Documento.tipo_documento.in_([TipoDocumento.FACT, TipoDocumento.RHE]),
                    Expediente.fecha_emision == fecha_emision,
                ),
                Documento.datos_extraidos["fecha_emision"].as_string() == fecha_texto,
                Documento.datos_extraidos["extraccion_confirmada"]["campos"][
                    "fecha_emision"
                ].as_string()
                == fecha_texto,
                Documento.datos_extraidos["procesamiento_documental"]["extraccion_estructurada"][
                    "campos"
                ]["fecha_emision"]["valor"].as_string()
                == fecha_texto,
            )
        )
    if mes is not None:
        consulta = consulta.where(
            or_(
                and_(
                    Documento.tipo_documento.in_([TipoDocumento.FACT, TipoDocumento.RHE]),
                    func.extract("year", Expediente.fecha_emision) == int(mes[:4]),
                    func.extract("month", Expediente.fecha_emision) == int(mes[5:7]),
                ),
                Documento.datos_extraidos["fecha_emision"].as_string().startswith(mes),
                Documento.datos_extraidos["extraccion_confirmada"]["campos"]["fecha_emision"]
                .as_string()
                .startswith(mes),
                Documento.datos_extraidos["procesamiento_documental"]["extraccion_estructurada"][
                    "campos"
                ]["fecha_emision"]["valor"]
                .as_string()
                .startswith(mes),
            )
        )
    if serie_correlativo:
        texto = serie_correlativo.strip().upper()
        if "-" in texto:
            serie, correlativo = texto.split("-", 1)
            numero = correlativo.lstrip("0") or "0"
            candidatos = [
                func.upper(Documento.nombre_original).contains(texto, autoescape=True),
                and_(
                    Documento.tipo_documento.in_([TipoDocumento.FACT, TipoDocumento.RHE]),
                    func.upper(Expediente.serie) == serie,
                    func.ltrim(Expediente.correlativo, "0") == numero,
                ),
            ]
            for ruta_serie, ruta_numero in (
                (
                    Documento.datos_extraidos["serie"].as_string(),
                    Documento.datos_extraidos["correlativo"].as_string(),
                ),
                (
                    Documento.datos_extraidos["extraccion_confirmada"]["campos"][
                        "serie"
                    ].as_string(),
                    Documento.datos_extraidos["extraccion_confirmada"]["campos"][
                        "correlativo"
                    ].as_string(),
                ),
                (
                    Documento.datos_extraidos["procesamiento_documental"][
                        "extraccion_estructurada"
                    ]["campos"]["serie"]["valor"].as_string(),
                    Documento.datos_extraidos["procesamiento_documental"][
                        "extraccion_estructurada"
                    ]["campos"]["correlativo"]["valor"].as_string(),
                ),
            ):
                candidatos.append(
                    and_(
                        func.upper(ruta_serie) == serie,
                        func.ltrim(ruta_numero, "0") == numero,
                    )
                )
            consulta = consulta.where(or_(*candidatos))
        else:
            consulta = consulta.where(
                or_(
                    func.upper(Documento.nombre_original).contains(texto, autoescape=True),
                    func.upper(Expediente.serie + "-" + Expediente.correlativo).contains(
                        texto, autoescape=True
                    ),
                )
            )
    if dia is not None:
        consulta = consulta.where(func.date(Documento.created_at) == dia)
    if fecha_desde is not None:
        consulta = consulta.where(func.date(Documento.created_at) >= fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.where(func.date(Documento.created_at) <= fecha_hasta)
    if (
        emisor_ruc is not None
        or receptor_ruc is not None
        or tipo_empresa is not None
        or empresa_emisora
        or empresa_receptora
    ):
        if emisor_ruc is not None or tipo_empresa is not None or empresa_emisora:
            emisor = aliased(Empresa)
            consulta = consulta.join(emisor, Expediente.emisor_id == emisor.id)
            if emisor_ruc is not None:
                consulta = consulta.where(emisor.ruc == emisor_ruc)
            if tipo_empresa is not None:
                consulta = consulta.where(emisor.clasificacion_proveedor == tipo_empresa)
            if empresa_emisora and empresa_emisora.strip():
                termino = empresa_emisora.strip().lower()
                consulta = consulta.where(
                    (func.lower(emisor.razon_social).contains(termino, autoescape=True))
                    | (emisor.ruc.contains(termino, autoescape=True))
                )
        if receptor_ruc is not None or empresa_receptora:
            receptor = aliased(Empresa)
            consulta = consulta.join(receptor, Expediente.receptor_id == receptor.id)
            if receptor_ruc is not None:
                consulta = consulta.where(receptor.ruc == receptor_ruc)
            if empresa_receptora and empresa_receptora.strip():
                termino = empresa_receptora.strip().lower()
                consulta = consulta.where(
                    (func.lower(receptor.razon_social).contains(termino, autoescape=True))
                    | (receptor.ruc.contains(termino, autoescape=True))
                )
    filtrados = consulta.subquery()
    cantidad = session.scalar(select(func.count()).select_from(filtrados)) or 0
    expedientes_unicos = (
        select(filtrados.c.expediente_id)
        .where(filtrados.c.expediente_id.is_not(None))
        .distinct()
        .subquery()
    )
    total = session.execute(
        select(
            func.count(Expediente.id),
            func.coalesce(
                func.sum(case((Expediente.moneda == "PEN", Expediente.importe_total), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((Expediente.moneda == "USD", Expediente.importe_total), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Expediente.moneda == "PEN")
                            & Expediente.pendiente_aprobacion.is_(False),
                            Expediente.importe_total,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Expediente.moneda == "USD")
                            & Expediente.pendiente_aprobacion.is_(False),
                            Expediente.importe_total,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .join(expedientes_unicos, Expediente.id == expedientes_unicos.c.expediente_id)
        .where(Expediente.tenant_id == tenant_id, Expediente.deleted_at.is_(None))
    ).one()
    return {
        "total_documentos": int(cantidad),
        "total_expedientes": int(total[0]),
        "total_pen": Decimal(total[1]),
        "total_pen_autorizado": Decimal(total[3]),
        "total_usd": Decimal(total[2]),
        "total_usd_autorizado": Decimal(total[4]),
    }


def _documento(session: SessionDep, tenant_id: uuid.UUID, documento_id: uuid.UUID) -> Documento:
    documento = session.get(Documento, documento_id)
    if documento is None or documento.tenant_id != tenant_id or documento.deleted_at:
        raise no_encontrado("Documento")
    return documento


def _documento_de_responsable(
    session: SessionDep, auth: OperativeAuthDep, usuario_id: uuid.UUID | None
) -> bool:
    if auth.miembro_id is None or usuario_id is None:
        return False
    return (
        session.scalar(
            select(Miembro.id).where(
                Miembro.id == usuario_id,
                Miembro.tenant_id == auth.tenant_id,
                Miembro.rol == RolMiembro.USUARIO,
                Miembro.responsable_id == auth.miembro_id,
                Miembro.deleted_at.is_(None),
            )
        )
        is not None
    )


def _validar_ambito_documento(
    auth: OperativeAuthDep, documento: Documento, session: SessionDep
) -> None:
    if auth.rol == "GESTOR" and documento.gestor_id != auth.gestor_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    if auth.rol == RolMiembro.USUARIO and documento.usuario_id != auth.usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    if auth.rol == RolMiembro.RESPONSABLE and not _documento_de_responsable(
        session, auth, documento.usuario_id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    if auth.rol == RolMiembro.GERENTE and (
        documento.expediente is None or not expediente_visible_gerente(documento.expediente, auth)
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")


def _puede_eliminar_documento(
    session: SessionDep, auth: OperativeAuthDep, documento: Documento
) -> bool:
    """Comprueba el ámbito de eliminación, que es más amplio para Usuario que la lectura."""
    if auth.rol == "ADMINISTRADOR":
        return True
    if auth.rol == "RESPONSABLE":
        return False  # requiere aprobación de Administración por MISD
    if auth.rol == "USUARIO":
        if auth.usuario_id is None:
            return False
        if documento.usuario_id == auth.usuario_id:
            return True
        return bool(
            documento.gestor_id
            and session.scalar(
                select(Gestor.id).where(
                    Gestor.id == documento.gestor_id,
                    Gestor.tenant_id == documento.tenant_id,
                    Gestor.usuario_id == auth.usuario_id,
                    Gestor.deleted_at.is_(None),
                )
            )
        )
    if auth.rol == "GESTOR":
        return auth.gestor_id is not None and documento.gestor_id == auth.gestor_id
    return False


def _avisar_eliminacion(
    session: SessionDep, tenant_id: uuid.UUID, actor: OperativeAuthDep, documento: Documento
) -> None:
    """Informa a la cadena operativa afectada sin conservar datos ni hashes del archivo."""
    usuario = session.get(Miembro, documento.usuario_id) if documento.usuario_id else None
    gestor = session.get(Gestor, documento.gestor_id) if documento.gestor_id else None
    ids_miembros = {
        ident
        for ident in (
            usuario.id if usuario else None,
            usuario.responsable_id if usuario else None,
            gestor.usuario_id if gestor else None,
        )
        if ident is not None
    }
    cuentas = (
        set(
            session.scalars(
                select(CuentaAcceso.id).where(
                    CuentaAcceso.tenant_id == tenant_id,
                    or_(
                        CuentaAcceso.miembro_id.in_(ids_miembros),
                        CuentaAcceso.gestor_id == gestor.id if gestor else false(),
                    ),
                    CuentaAcceso.activo.is_(True),
                    CuentaAcceso.deleted_at.is_(None),
                )
            )
        )
        if ids_miembros
        else set()
    )
    texto = (
        "Se eliminó definitivamente un documento de tu equipo. "
        f"Tipo: {documento.tipo_documento or 'sin clasificar'}."
    )
    for cuenta_id in cuentas:
        if cuenta_id != actor.cuenta_id:
            session.add(
                ChatMensaje(
                    tenant_id=tenant_id,
                    remitente_cuenta_id=actor.cuenta_id,
                    destinatario_cuenta_id=cuenta_id,
                    texto=texto,
                )
            )


def _validar_ambito_expediente(
    auth: OperativeAuthDep, expediente: Expediente, session: SessionDep
) -> None:
    if auth.rol == "GESTOR" and expediente.gestor_id != auth.gestor_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    if auth.rol == RolMiembro.USUARIO and expediente.usuario_id != auth.usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    if auth.rol == RolMiembro.RESPONSABLE and not _documento_de_responsable(
        session, auth, expediente.usuario_id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    if auth.rol == RolMiembro.GERENTE and not expediente_visible_gerente(expediente, auth):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")


def _aplicar_ambito_documentos(consulta: Any, auth: OperativeAuthDep) -> Any:
    if auth.rol == "GESTOR":
        return consulta.where(Documento.gestor_id == auth.gestor_id)
    if auth.rol == RolMiembro.USUARIO:
        return consulta.where(Documento.usuario_id == auth.usuario_id)
    if auth.rol == RolMiembro.RESPONSABLE:
        if auth.miembro_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Responsable sin ámbito")
        return consulta.where(
            Documento.usuario_id.in_(
                select(Miembro.id).where(
                    Miembro.tenant_id == auth.tenant_id,
                    Miembro.responsable_id == auth.miembro_id,
                    Miembro.rol == RolMiembro.USUARIO,
                    Miembro.deleted_at.is_(None),
                )
            )
        )
    if auth.rol == RolMiembro.GERENTE:
        return consulta.where(Documento.expediente.has(alcance_expedientes_gerente(auth)))
    return consulta


@router.post("/reindexar-gre-pendientes")
def reindexar_gre_pendientes(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    limit: Annotated[int, Query(ge=1, le=2000)] = 2000,
) -> dict[str, int]:
    """Reconcilia GRE históricas con la extracción guardada, sin llamar OCR."""
    consulta = (
        select(Documento)
        .where(
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
            Documento.expediente_id.is_(None),
            Documento.tipo_documento == TipoDocumento.GRR,
        )
        .order_by(Documento.created_at.desc())
        .limit(limit)
    )
    consulta = _aplicar_ambito_documentos(consulta, auth)
    candidatos = list(session.scalars(consulta))
    indexados = relacionados = 0
    for documento in candidatos:
        existente = session.scalar(
            select(ReferenciaGRE.id).where(
                ReferenciaGRE.tenant_id == tenant_id,
                ReferenciaGRE.documento_id == documento.id,
            )
        )
        if existente is not None:
            continue
        datos = documento.datos_extraidos or {}
        procesamiento = datos.get("procesamiento_documental")
        if not isinstance(procesamiento, dict):
            continue
        resultado = aplicar_automaticamente(session, settings, hoy, documento, procesamiento)
        if resultado.relacionado:
            relacionados += 1
        else:
            ref = session.scalar(
                select(ReferenciaGRE.id).where(
                    ReferenciaGRE.tenant_id == tenant_id,
                    ReferenciaGRE.documento_id == documento.id,
                )
            )
            if ref is not None:
                indexados += 1
        session.commit()
    return {
        "considerados": len(candidatos),
        "provisionales_creados": indexados,
        "guias_relacionadas": relacionados,
    }


@router.get("/provisionales-gre")
def provisionales_gre(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    limit: Annotated[int, Query(ge=1, le=2000)] = 100,
) -> list[dict[str, str | bool]]:
    """Expedientes provisionales identificados por una guía, sin factura ni importe."""
    consulta = (
        select(ReferenciaGRE, Empresa)
        .join(Documento, Documento.id == ReferenciaGRE.documento_id)
        .outerjoin(
            Empresa,
            (Empresa.tenant_id == ReferenciaGRE.tenant_id)
            & (Empresa.ruc == ReferenciaGRE.receptor_ruc),
        )
        .where(
            ReferenciaGRE.tenant_id == tenant_id,
            ReferenciaGRE.expediente_id.is_(None),
            Documento.deleted_at.is_(None),
            Documento.expediente_id.is_(None),
        )
        .order_by(ReferenciaGRE.created_at.desc())
        .limit(limit)
    )
    consulta = _aplicar_ambito_documentos(consulta, auth)
    return [
        {
            "documento_id": str(ref.documento_id),
            "factura": f"{ref.serie}-{ref.correlativo}",
            "estado": "PENDIENTE_FACTURA",
            "moneda": "PEN",
            "monto_contabilizable": "0.00",
            "emisor_ruc": ref.emisor_ruc,
            "receptor_ruc": ref.receptor_ruc,
            "cliente_autorizado": bool(
                empresa and empresa.autorizada and empresa.deleted_at is None
            ),
        }
        for ref, empresa in session.execute(consulta)
    ]


@router.get("/capacidades")
def capacidades_documentales(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, bool]:
    """Permisos generales efectivos; el ámbito individual se valida en cada acción."""
    puede_eliminar_directamente = auth.rol in {
        "ADMINISTRADOR",
        "USUARIO",
        "GESTOR",
    } and permiso_habilitado(session, tenant_id, auth.rol, PERMISO_ELIMINAR_REGISTROS)
    puede_solicitar_o_eliminar = auth.rol == "RESPONSABLE" or puede_eliminar_directamente
    return {
        "puede_retirar": puede_solicitar_o_eliminar,
        "puede_restaurar": False,
        "puede_eliminar_definitivamente": puede_eliminar_directamente,
    }


class PrevisualizacionRetiradaIn(BaseModel):
    documentos_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


@router.post("/previsualizar-retirada")
def previsualizar_retirada(
    datos: PrevisualizacionRetiradaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    """Verifica retiradas sin modificar estado ni exponer documentos fuera del ámbito."""
    if auth.rol == RolMiembro.SUPERADMIN or not permiso_habilitado(
        session, tenant_id, auth.rol, PERMISO_ELIMINAR_REGISTROS
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para retirar registros")
    if len(set(datos.documentos_ids)) != len(datos.documentos_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "IDs repetidos en el lote")
    resultados: list[dict[str, str]] = []
    for documento_id in datos.documentos_ids:
        documento = session.get(Documento, documento_id)
        if documento is None or documento.tenant_id != tenant_id or documento.deleted_at:
            resultados.append({"id": str(documento_id), "estado": "NO_DISPONIBLE"})
            continue
        if auth.rol == "RESPONSABLE":
            if _documento_de_responsable(session, auth, documento.usuario_id):
                resultados.append({"id": str(documento_id), "estado": "REQUIERE_MISD"})
            else:
                resultados.append({"id": str(documento_id), "estado": "NO_DISPONIBLE"})
            continue
        if not _puede_eliminar_documento(session, auth, documento):
            resultados.append({"id": str(documento_id), "estado": "NO_DISPONIBLE"})
            continue
        resultados.append({"id": str(documento_id), "estado": "APTO_ELIMINACION"})
    return {
        "total": len(resultados),
        "aptos": sum(fila["estado"] == "APTO_ELIMINACION" for fila in resultados),
        "resultados": resultados,
        "solo_previsualizacion": True,
    }


@router.post("/retirar-lote")
def retirar_documentos_lote(
    datos: PrevisualizacionRetiradaIn,
    session: SessionDep,
    almacen: AlmacenDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    """Elimina cada archivo seleccionado de manera independiente y definitiva."""
    if auth.rol == RolMiembro.SUPERADMIN or not permiso_habilitado(
        session, tenant_id, auth.rol, PERMISO_ELIMINAR_REGISTROS
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para retirar registros")
    if len(set(datos.documentos_ids)) != len(datos.documentos_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "IDs repetidos en el lote")
    resultados: list[dict[str, str]] = []
    for documento_id in datos.documentos_ids:
        try:
            resultado = eliminar_documento(
                session, almacen, settings, hoy, tenant_id, auth, documento_id
            )
        except HTTPException as exc:
            session.rollback()
            resultados.append(
                {"id": str(documento_id), "estado": "NO_RETIRADO", "codigo": str(exc.status_code)}
            )
        else:
            estado = (
                "ELIMINADO"
                if resultado["estado"] == "completado"
                else "ELIMINADO_ARCHIVO_PENDIENTE"
            )
            resultados.append({"id": str(documento_id), "estado": estado})
    return {
        "total": len(resultados),
        "eliminados": sum(fila["estado"].startswith("ELIMINADO") for fila in resultados),
        "resultados": resultados,
    }


@router.get("/{documento_id}", response_model=DocumentoOut)
def obtener_documento(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
) -> Documento:
    documento = _documento(session, tenant_id, documento_id)
    _validar_ambito_documento(auth, documento, session)
    return documento


@router.delete("/{documento_id}")
def eliminar_documento(
    session: SessionDep,
    almacen: AlmacenDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    documento_id: uuid.UUID,
) -> dict[str, str]:
    candidato = session.scalar(
        select(Documento).where(
            Documento.id == documento_id,
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
        )
    )
    if candidato is None:
        raise no_encontrado("Documento")
    if candidato.expediente_id is not None:
        expediente_bloqueado = session.scalar(
            select(Expediente)
            .where(
                Expediente.id == candidato.expediente_id,
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if expediente_bloqueado is None:
            raise no_encontrado("Documento")
    documento = session.scalar(
        select(Documento)
        .where(
            Documento.id == documento_id,
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if documento is None:
        raise no_encontrado("Documento")
    if auth.rol == "RESPONSABLE":
        if _documento_de_responsable(session, auth, documento.usuario_id):
            raise HTTPException(409, "El Responsable debe solicitar aprobación a Administración")
        raise no_encontrado("Documento")
    if not _puede_eliminar_documento(session, auth, documento) or not permiso_habilitado(
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
    # La baja es operativa y definitiva. Se limpian relaciones derivadas; si el
    # documento era comprobante de pago se conserva el pago sin su archivo adjunto.
    from app.item_models import AuditoriaFacturaItem, LineaComprobanteItem
    from app.models import PagoERP

    session.execute(
        delete(RelacionDocumento).where(
            (RelacionDocumento.origen_id == documento.id)
            | (RelacionDocumento.destino_id == documento.id)
        )
    )
    session.execute(delete(ReferenciaGRE).where(ReferenciaGRE.documento_id == documento.id))
    session.execute(delete(CorreccionIA).where(CorreccionIA.documento_id == documento.id))
    session.execute(
        delete(LineaComprobanteItem).where(LineaComprobanteItem.documento_id == documento.id)
    )
    session.execute(
        update(PagoERP)
        .where(PagoERP.tenant_id == tenant_id, PagoERP.voucher_documento_id == documento.id)
        .values(voucher_documento_id=None)
    )
    solicitudes_misd = set()
    if expediente is not None:
        solicitudes_misd = set(
            session.scalars(
                select(SolicitudRetiroMISD.id).where(
                    SolicitudRetiroMISD.tenant_id == tenant_id,
                    SolicitudRetiroMISD.expediente_id == expediente.id,
                )
            )
        )
    solicitudes_emisor = list(
        session.scalars(
            select(SolicitudCargaEmisor).where(
                SolicitudCargaEmisor.tenant_id == tenant_id,
                SolicitudCargaEmisor.sha256_archivo == documento.sha256,
            )
        )
    )
    ids_solicitudes_emisor = {solicitud.id for solicitud in solicitudes_emisor}
    rutas_cuarentena = [
        solicitud.ruta_temporal for solicitud in solicitudes_emisor if solicitud.ruta_temporal
    ]
    session.execute(
        delete(Auditoria).where(
            Auditoria.tenant_id == tenant_id,
            Auditoria.entidad_id.in_({documento.id} | solicitudes_misd | ids_solicitudes_emisor),
            Auditoria.entidad.in_({"documento", "solicitud_retiro", "solicitud_carga_emisor"}),
        )
    )
    for solicitud_id in ids_solicitudes_emisor:
        session.execute(
            delete(AlertaManual).where(
                AlertaManual.tenant_id == tenant_id,
                AlertaManual.mensaje.contains(str(solicitud_id)),
            )
        )
    if expediente is not None:
        session.execute(
            delete(ChatMensaje).where(
                ChatMensaje.tenant_id == tenant_id,
                ChatMensaje.texto.contains(str(expediente.id)),
            )
        )
        session.execute(
            delete(SolicitudRetiroMISD).where(
                SolicitudRetiroMISD.tenant_id == tenant_id,
                SolicitudRetiroMISD.expediente_id == expediente.id,
            )
        )
    for solicitud in solicitudes_emisor:
        session.delete(solicitud)
    _avisar_eliminacion(session, tenant_id, auth, documento)
    ruta_storage = documento.ruta_storage
    sha_archivo = documento.sha256
    bloquear_clave_archivo(session, tenant_id, sha_archivo)
    pendientes = [
        EliminacionArchivoPendiente(tenant_id=tenant_id, ruta_storage=ruta)
        for ruta in [ruta_storage, *rutas_cuarentena]
    ]
    session.add_all(pendientes)
    session.delete(documento)
    session.flush()
    if expediente is not None and expediente.deleted_at is None:
        queda_documento = session.scalar(
            select(Documento.id)
            .where(
                Documento.tenant_id == tenant_id,
                Documento.expediente_id == expediente.id,
                Documento.deleted_at.is_(None),
            )
            .limit(1)
        )
        if queda_documento is None:
            # Si se retiró el último archivo, eliminar también el expediente:
            # de lo contrario quedan filas vacías que reaparecen en Expedientes.
            session.execute(
                delete(Alerta).where(
                    Alerta.tenant_id == tenant_id,
                    Alerta.expediente_id == expediente.id,
                )
            )
            session.execute(
                delete(AlertaManual).where(
                    AlertaManual.tenant_id == tenant_id,
                    AlertaManual.expediente_id == expediente.id,
                )
            )
            session.execute(
                delete(Auditoria).where(
                    Auditoria.tenant_id == tenant_id,
                    Auditoria.entidad == "expediente",
                    Auditoria.entidad_id == expediente.id,
                )
            )
            session.execute(
                delete(AuditoriaFacturaItem).where(
                    AuditoriaFacturaItem.tenant_id == tenant_id,
                    AuditoriaFacturaItem.expediente_id == expediente.id,
                )
            )
            session.delete(expediente)
        else:
            actualizar_expediente(session, expediente, hoy, settings)
    session.commit()
    eliminar_cache_ocr(
        sha_archivo,
        str(tenant_id),
        settings.storage_dir / "_ocr_cache",
        settings.max_extracted_chars,
        settings.max_ocr_pdf_pages,
    )
    todos_completados = True
    for pendiente in pendientes:
        if procesar_archivo_pendiente(session, almacen, pendiente):
            session.delete(pendiente)
        else:
            todos_completados = False
    session.commit()
    return {"estado": "completado" if todos_completados else "pendiente"}


@router.post("/{documento_id}/restaurar")
def restaurar_documento(documento_id: uuid.UUID) -> None:
    """La eliminación es definitiva; una carga posterior crea otro registro."""
    raise HTTPException(
        status.HTTP_410_GONE,
        "La restauración fue retirada. Vuelva a cargar el archivo para crear un ingreso nuevo.",
    )


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
    _validar_ambito_documento(auth, documento, session)
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
    _validar_ambito_documento(auth, documento, session)
    try:
        _procesar_y_aplicar(session, settings, almacen, hoy, documento)
    except DocumentoNoProcesable as exc:
        registrar_fallo(session, documento, str(exc))
        session.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except ComprobanteYaRegistrado as exc:
        session.rollback()
        raise _comprobante_duplicado(session, auth, exc.expediente_id) from exc
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
                forzar_cache=forzar,
            )
        except HTTPException as exc:
            # MISD puede retirar un candidato después de seleccionar el lote.
            # Saltarlo sin impedir el procesamiento de los siguientes archivos.
            session.rollback()
            vigente = session.get(Documento, documento.id)
            if exc.status_code != status.HTTP_404_NOT_FOUND or vigente is None:
                raise
            session.refresh(vigente)
            if vigente.deleted_at is None:
                raise
            continue
        except DocumentoNoProcesable as exc:
            resultado = registrar_fallo(session, documento, str(exc))
        except ComprobanteYaRegistrado as exc:
            session.rollback()
            documento = session.get(Documento, documento.id)
            if documento is None:
                raise
            resultado = registrar_fallo(
                session,
                documento,
                f"Factura duplicada; expediente existente: {exc.expediente_id}",
            )
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
    forzar_cache: bool = False,
) -> ResultadoAutomatizacion:
    # Volver a consultar la fila: la selección del lote pudo quedar obsoleta
    # mientras otro operador retiraba el documento mediante MISD.
    session.refresh(documento)
    if documento.deleted_at is not None:
        raise no_encontrado("Documento")
    datos = documento.datos_extraidos or {}
    existente = datos.get("procesamiento_documental")
    if reutilizar and isinstance(existente, dict):
        procesamiento = existente
    else:
        contenido = almacen.ruta_absoluta(documento.ruta_storage).read_bytes()
        with _PROCESAMIENTO_LOCK:
            procesamiento = procesar_con_cache(
                contenido,
                str(documento.tenant_id),
                settings.storage_dir / "_ocr_cache",
                settings.max_extracted_chars,
                settings.max_ocr_pdf_pages,
                lambda: procesar(
                    contenido, settings.max_extracted_chars, settings.max_ocr_pdf_pages
                ).a_dict(),
                forzar=forzar_cache,
            )
        aplicar_perfiles_aprendidos(session, documento, procesamiento)
        guardar_procesamiento(session, documento, procesamiento)
    # Conservar los cambios OCR pendientes antes de refrescar la fila: refresh
    # descarta atributos no volcados y provocaba pérdida de la extracción.
    session.flush()
    # El bloqueo de fila protege también la ruta que reutiliza OCR en caché:
    # MISD no puede confirmar una retirada mientras se aplican las relaciones.
    # PostgreSQL mantiene el bloqueo hasta el commit/rollback de la petición.
    bloqueado = session.scalar(
        select(Documento).where(Documento.id == documento.id).with_for_update()
    )
    if bloqueado is None:
        raise no_encontrado("Documento")
    session.refresh(documento)
    if documento.deleted_at is not None:
        raise no_encontrado("Documento")
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
        "PENDIENTE_FACTURA",
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
    _validar_ambito_documento(auth, documento, session)
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
    _validar_ambito_documento(auth, documento, session)
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
    if existente is not None and eliminar_expediente_vacio(session, existente):
        existente = None
    if existente is not None and documento.expediente_id != existente.id:
        # Nunca incorporar un nuevo archivo a una identidad fiscal existente
        # sin comparación explícita. La asociación puede revisarse en Gestor.
        raise _comprobante_duplicado(session, auth, existente.id)
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
        correlativo_original=str(campos["correlativo"]),
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
        try:
            vincular_documento(session, settings, hoy, documento, expediente.id, tipo_documento)
        except ComprobanteYaRegistrado as exc:
            session.rollback()
            raise _comprobante_duplicado(session, auth, exc.expediente_id) from exc
    # Vinculación conservadora de documentos ya extraídos y sin expediente.
    # Solo si existe una única coincidencia, con referencia y ambos RUC,
    # dentro del mismo tenant, usuario y ámbito gestor.
    if creado:
        pendientes = session.scalars(
            select(Documento)
            .where(
                Documento.tenant_id == tenant_id,
                Documento.usuario_id == documento.usuario_id,
                Documento.gestor_id == documento.gestor_id,
                Documento.expediente_id.is_(None),
                Documento.deleted_at.is_(None),
                Documento.tipo_documento.is_not(None),
                Documento.tipo_documento != TipoDocumento.FACT,
            )
            .order_by(Documento.created_at.desc())
            .limit(100)
        )
        for pendiente in pendientes:
            if pendiente.tipo_documento is None:
                continue
            sugerencias = sugerir_relaciones(session, pendiente)
            if len(sugerencias) != 1 or sugerencias[0].expediente.id != expediente.id:
                continue
            evidencias = sugerencias[0].evidencias
            if not (
                any(item.startswith("Comprobante ") for item in evidencias)
                and any(item.startswith("RUC emisor ") for item in evidencias)
                and any(item.startswith("RUC receptor ") for item in evidencias)
            ):
                continue
            vincular_documento(
                session,
                settings,
                hoy,
                pendiente,
                expediente.id,
                TipoDocumento(pendiente.tipo_documento),
            )
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
    _validar_ambito_documento(auth, documento, session)
    sugerencias = sugerir_relaciones(session, documento)
    if auth.rol == "GESTOR":
        sugerencias = [s for s in sugerencias if s.expediente.gestor_id == auth.gestor_id]
    elif auth.rol == RolMiembro.USUARIO:
        sugerencias = [s for s in sugerencias if s.expediente.usuario_id == auth.usuario_id]
    elif auth.rol == RolMiembro.GERENTE:
        sugerencias = [s for s in sugerencias if expediente_visible_gerente(s.expediente, auth)]
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
    _validar_ambito_documento(auth, documento, session)
    expediente = session.get(Expediente, datos.expediente_id)
    if expediente is None or expediente.tenant_id != tenant_id or expediente.deleted_at:
        raise no_encontrado("Expediente")
    _validar_ambito_expediente(auth, expediente, session)
    try:
        vincular_documento(
            session, settings, hoy, documento, datos.expediente_id, datos.tipo_documento
        )
    except ExpedienteNoEncontrado as exc:
        raise no_encontrado("Expediente") from exc
    except ComprobanteYaRegistrado as exc:
        session.rollback()
        raise _comprobante_duplicado(session, auth, exc.expediente_id) from exc
    session.commit()
    return documento
