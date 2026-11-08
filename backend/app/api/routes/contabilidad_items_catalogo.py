"""Administración segura del catálogo y reescaneo idempotente de ítems."""

import hashlib
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Select

from app.api.deps import AlmacenDep, OperativeAuthDep, SessionDep, SettingsDep
from app.enums import TipoDocumento
from app.item_models import (
    CategoriaItem,
    LineaComprobanteItem,
    ProductoItem,
    TrabajoReescaneoItems,
)
from app.models import Documento
from app.services import auditoria
from app.services.cache_ocr import procesar_con_cache
from app.services.contabilidad_items_rules import texto_normalizado
from app.services.contabilidad_items_ubl import registrar_items_pdf_estacion, registrar_items_ubl
from app.services.procesamiento_documental import DocumentoNoProcesable, procesar

router = APIRouter(prefix="/contabilidad-items", tags=["contabilidad-items-catalogo"])
_OCR_LOCK = threading.Lock()
MAX_REESCANEO_LOTE = 3
MAX_DOCUMENTO_BYTES = 30 * 1024 * 1024


def _solo_administracion(auth: OperativeAuthDep) -> None:
    if auth.rol != "ADMINISTRADOR":
        raise HTTPException(403, "Solo Administración puede modificar el catálogo o reescanear")


def _normalizar_categoria(nombre: str) -> tuple[str, str]:
    limpio = " ".join(nombre.split())
    normalizado = re.sub(r"\s+", " ", limpio.casefold()).strip()
    return limpio, normalizado


class CategoriaCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)


class CategoriaEditar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    activa: bool | None = None


class ProductoCrear(BaseModel):
    descripcion: str = Field(min_length=2, max_length=500)
    unidad_base: str = Field(min_length=1, max_length=40)
    categoria_id: uuid.UUID


class ProductoEditar(BaseModel):
    categoria_id: uuid.UUID | None = None
    activo: bool | None = None


def _categoria_dict(categoria: CategoriaItem) -> dict[str, object]:
    return {
        "id": str(categoria.id),
        "nombre": categoria.nombre,
        "activa": categoria.activa,
        "created_at": categoria.created_at.isoformat(),
    }


@router.get("/categorias")
def listar_categorias(session: SessionDep, auth: OperativeAuthDep) -> list[dict[str, object]]:
    return [
        _categoria_dict(categoria)
        for categoria in session.scalars(
            select(CategoriaItem)
            .where(CategoriaItem.tenant_id == auth.tenant_id)
            .order_by(CategoriaItem.activa.desc(), CategoriaItem.nombre_normalizado)
        )
    ]


@router.post("/categorias", status_code=201)
def crear_categoria(
    datos: CategoriaCrear, session: SessionDep, auth: OperativeAuthDep
) -> dict[str, object]:
    _solo_administracion(auth)
    nombre, normalizado = _normalizar_categoria(datos.nombre)
    if len(nombre) < 2 or not normalizado:
        raise HTTPException(422, "Escriba un nombre de categoría válido")
    categoria = CategoriaItem(
        tenant_id=auth.tenant_id,
        nombre=nombre,
        nombre_normalizado=normalizado,
        creado_por_cuenta_id=auth.cuenta_id,
    )
    session.add(categoria)
    try:
        session.flush()
        auditoria.registrar(
            session,
            auth.tenant_id,
            "ITEM_CATEGORIA_CREADA",
            "categoria_item",
            categoria.id,
            {"nombre": nombre},
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Ya existe una categoría con ese nombre") from exc
    return _categoria_dict(categoria)


@router.patch("/categorias/{categoria_id}")
def editar_categoria(
    categoria_id: uuid.UUID,
    datos: CategoriaEditar,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _solo_administracion(auth)
    categoria = session.scalar(
        select(CategoriaItem)
        .where(CategoriaItem.id == categoria_id, CategoriaItem.tenant_id == auth.tenant_id)
        .with_for_update()
    )
    if categoria is None:
        raise HTTPException(404, "Categoría no encontrada")
    anterior = categoria.nombre
    if datos.nombre is not None:
        nombre, normalizado = _normalizar_categoria(datos.nombre)
        conflicto = session.scalar(
            select(CategoriaItem.id).where(
                CategoriaItem.tenant_id == auth.tenant_id,
                CategoriaItem.nombre_normalizado == normalizado,
                CategoriaItem.id != categoria_id,
            )
        )
        if conflicto is not None:
            raise HTTPException(409, "Ya existe una categoría con ese nombre")
        categoria.nombre = nombre
        categoria.nombre_normalizado = normalizado
        session.query(ProductoItem).filter(
            ProductoItem.tenant_id == auth.tenant_id,
            ProductoItem.categoria == anterior,
        ).update({ProductoItem.categoria: nombre}, synchronize_session=False)
    if datos.activa is not None:
        categoria.activa = datos.activa
    auditoria.registrar(
        session,
        auth.tenant_id,
        "ITEM_CATEGORIA_ACTUALIZADA",
        "categoria_item",
        categoria.id,
        {"anterior": anterior, "nombre": categoria.nombre, "activa": categoria.activa},
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Ya existe una categoría con ese nombre") from exc
    return _categoria_dict(categoria)


@router.get("/catalogo")
def listar_catalogo(
    session: SessionDep,
    auth: OperativeAuthDep,
    buscar: Annotated[str | None, Query(max_length=150)] = None,
    incluir_inactivos: bool = False,
    limite: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, object]:
    _solo_administracion(auth)
    consulta = (
        select(
            ProductoItem,
            func.count(LineaComprobanteItem.id).label("lineas_asociadas"),
        )
        .outerjoin(
            LineaComprobanteItem,
            (LineaComprobanteItem.producto_id == ProductoItem.id)
            & (LineaComprobanteItem.tenant_id == auth.tenant_id),
        )
        .where(ProductoItem.tenant_id == auth.tenant_id)
        .group_by(ProductoItem.id)
    )
    if not incluir_inactivos:
        consulta = consulta.where(ProductoItem.activo.is_(True))
    if buscar and buscar.strip():
        termino = f"%{buscar.strip()}%"
        consulta = consulta.where(
            ProductoItem.descripcion.ilike(termino) | ProductoItem.categoria.ilike(termino)
        )
    consulta = consulta.order_by(ProductoItem.descripcion, ProductoItem.id)
    total = session.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = session.execute(consulta.limit(limite).offset(offset)).all()
    return {
        "total": total,
        "items": [
            {
                "id": str(producto.id),
                "descripcion": producto.descripcion,
                "unidad_base": producto.unidad_base or "",
                "categoria": producto.categoria,
                "categoria_confirmada": producto.clasificacion_confirmada,
                "activo": producto.activo,
                "lineas_asociadas": lineas_asociadas,
            }
            for producto, lineas_asociadas in filas
        ],
    }


@router.post("/catalogo", status_code=201)
def crear_producto(
    datos: ProductoCrear, session: SessionDep, auth: OperativeAuthDep
) -> dict[str, object]:
    _solo_administracion(auth)
    categoria = session.scalar(
        select(CategoriaItem).where(
            CategoriaItem.id == datos.categoria_id,
            CategoriaItem.tenant_id == auth.tenant_id,
            CategoriaItem.activa.is_(True),
        )
    )
    if categoria is None:
        raise HTTPException(422, "Seleccione una categoría activa de este tenant")
    descripcion = " ".join(datos.descripcion.split())
    unidad = " ".join(datos.unidad_base.split()).upper()
    clave = hashlib.sha256(f"{texto_normalizado(descripcion)}|{unidad}".encode()).hexdigest()
    existente = session.scalar(
        select(ProductoItem.id).where(
            ProductoItem.tenant_id == auth.tenant_id,
            ProductoItem.clave_catalogo == clave,
        )
    )
    if existente is not None:
        raise HTTPException(409, "El ítem ya existe para esta unidad; edite su categoría")
    producto = ProductoItem(
        tenant_id=auth.tenant_id,
        clave_catalogo=clave,
        descripcion=descripcion,
        unidad_base=unidad,
        categoria=categoria.nombre,
        clasificacion_confirmada=True,
        activo=True,
    )
    session.add(producto)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "El ítem ya existe para esta unidad; edite su categoría") from exc
    auditoria.registrar(
        session,
        auth.tenant_id,
        "ITEM_CATALOGO_CREADO",
        "producto_item",
        producto.id,
        {"categoria": categoria.nombre, "unidad": unidad},
    )
    session.commit()
    return {
        "id": str(producto.id),
        "descripcion": producto.descripcion,
        "categoria": producto.categoria,
    }


@router.patch("/catalogo/{producto_id}")
def editar_producto(
    producto_id: uuid.UUID,
    datos: ProductoEditar,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _solo_administracion(auth)
    producto = session.scalar(
        select(ProductoItem)
        .where(ProductoItem.id == producto_id, ProductoItem.tenant_id == auth.tenant_id)
        .with_for_update()
    )
    if producto is None:
        raise HTTPException(404, "Ítem no encontrado")
    if datos.categoria_id is not None:
        categoria = session.scalar(
            select(CategoriaItem).where(
                CategoriaItem.id == datos.categoria_id,
                CategoriaItem.tenant_id == auth.tenant_id,
                CategoriaItem.activa.is_(True),
            )
        )
        if categoria is None:
            raise HTTPException(422, "Seleccione una categoría activa de este tenant")
        producto.categoria = categoria.nombre
        producto.clasificacion_confirmada = True
    if datos.activo is not None:
        producto.activo = datos.activo
    auditoria.registrar(
        session,
        auth.tenant_id,
        "ITEM_CATALOGO_ACTUALIZADO",
        "producto_item",
        producto.id,
        {"categoria": producto.categoria, "activo": producto.activo},
    )
    session.commit()
    return {
        "id": str(producto.id),
        "descripcion": producto.descripcion,
        "categoria": producto.categoria,
        "categoria_confirmada": producto.clasificacion_confirmada,
        "activo": producto.activo,
    }


def _facturas_query(auth: OperativeAuthDep) -> Select[tuple[Documento]]:
    return select(Documento).where(
        Documento.tenant_id == auth.tenant_id,
        Documento.deleted_at.is_(None),
        Documento.tipo_documento == TipoDocumento.FACT,
    )


def _formato(documento: Documento) -> str:
    nombre = documento.nombre_original.lower()
    mime = documento.mime_type.lower()
    if nombre.endswith(".xml") or "xml" in mime:
        return "XML"
    if mime.startswith("image/") or nombre.endswith(
        (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")
    ):
        return "IMAGEN"
    if mime == "application/pdf" or nombre.endswith(".pdf"):
        return "PDF"
    return "OTRO"


def _estado_trabajo(trabajo: TrabajoReescaneoItems) -> dict[str, object]:
    return {
        "id": str(trabajo.id),
        "estado": trabajo.estado,
        "total_documentos": trabajo.total_documentos,
        "procesados": trabajo.procesados,
        "lineas_nuevas": trabajo.lineas_nuevas,
        "requieren_revision": trabajo.requieren_revision,
        "errores": trabajo.errores,
        "progreso": (
            round(trabajo.procesados * 100 / trabajo.total_documentos)
            if trabajo.total_documentos
            else 100
        ),
        "created_at": trabajo.created_at.isoformat(),
        "finalizado_at": trabajo.finalizado_at.isoformat() if trabajo.finalizado_at else None,
    }


@router.get("/reescaneo/preview")
def vista_previa_reescaneo(session: SessionDep, auth: OperativeAuthDep) -> dict[str, object]:
    _solo_administracion(auth)
    nombre = func.lower(Documento.nombre_original)
    mime = func.lower(Documento.mime_type)
    es_xml = or_(nombre.like("%.xml"), mime.like("%xml%"))
    es_imagen = or_(
        mime.like("image/%"),
        nombre.like("%.jpg"),
        nombre.like("%.jpeg"),
        nombre.like("%.png"),
        nombre.like("%.tif"),
        nombre.like("%.tiff"),
        nombre.like("%.webp"),
    )
    es_pdf = or_(mime == "application/pdf", nombre.like("%.pdf"))
    formato = case((es_xml, "XML"), (es_imagen, "IMAGEN"), (es_pdf, "PDF"), else_="OTRO").label(
        "formato"
    )
    tiene_lineas = exists(
        select(LineaComprobanteItem.id).where(
            LineaComprobanteItem.tenant_id == Documento.tenant_id,
            LineaComprobanteItem.documento_id == Documento.id,
        )
    ).label("tiene_lineas")
    resumen = session.execute(
        select(formato, tiene_lineas, func.count())
        .where(
            Documento.tenant_id == auth.tenant_id,
            Documento.deleted_at.is_(None),
            Documento.tipo_documento == TipoDocumento.FACT,
        )
        .group_by(formato, tiene_lineas)
    ).all()
    por_formato = {"XML": 0, "PDF": 0, "IMAGEN": 0, "OTRO": 0}
    total = con_lineas = 0
    for tipo, tiene, cantidad in resumen:
        por_formato[tipo] += cantidad
        total += cantidad
        con_lineas += cantidad if tiene else 0
    return {
        "facturas": total,
        "con_lineas": con_lineas,
        "sin_lineas": total - con_lineas,
        "por_formato": por_formato,
        "lote_maximo": MAX_REESCANEO_LOTE,
        "nota": (
            "Se conservan líneas, clasificaciones, expedientes y originales. Se extrae UBL y "
            "los formatos PDF/imágenes con reglas validadas; actualmente, la regla PDF cubre "
            "un formato específico. Los demás quedan para revisión manual."
        ),
    }


@router.get("/reescaneo/trabajos")
def listar_trabajos(session: SessionDep, auth: OperativeAuthDep) -> list[dict[str, object]]:
    _solo_administracion(auth)
    trabajos = session.scalars(
        select(TrabajoReescaneoItems)
        .where(TrabajoReescaneoItems.tenant_id == auth.tenant_id)
        .order_by(TrabajoReescaneoItems.created_at.desc())
        .limit(10)
    )
    return [_estado_trabajo(trabajo) for trabajo in trabajos]


@router.post("/reescaneo/trabajos", status_code=201)
def iniciar_reescaneo(session: SessionDep, auth: OperativeAuthDep) -> dict[str, object]:
    _solo_administracion(auth)
    activo = session.scalar(
        select(TrabajoReescaneoItems.id).where(
            TrabajoReescaneoItems.tenant_id == auth.tenant_id,
            TrabajoReescaneoItems.estado == "EN_PROCESO",
        )
    )
    if activo is not None:
        raise HTTPException(409, "Ya hay un reescaneo activo en este tenant")
    total = session.scalar(select(func.count()).select_from(_facturas_query(auth).subquery())) or 0
    trabajo = TrabajoReescaneoItems(
        tenant_id=auth.tenant_id,
        solicitado_por_cuenta_id=auth.cuenta_id,
        total_documentos=total,
        estado="EN_PROCESO" if total else "COMPLETADO",
        finalizado_at=None if total else datetime.now(UTC),
    )
    session.add(trabajo)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Ya existe un reescaneo activo en este tenant") from exc
    auditoria.registrar(
        session,
        auth.tenant_id,
        "ITEMS_REESCANEO_INICIADO",
        "trabajo_reescaneo_items",
        trabajo.id,
        {"documentos": total},
    )
    session.commit()
    return _estado_trabajo(trabajo)


@router.get("/reescaneo/trabajos/{trabajo_id}")
def obtener_trabajo(
    trabajo_id: uuid.UUID, session: SessionDep, auth: OperativeAuthDep
) -> dict[str, object]:
    _solo_administracion(auth)
    trabajo = session.scalar(
        select(TrabajoReescaneoItems).where(
            TrabajoReescaneoItems.id == trabajo_id,
            TrabajoReescaneoItems.tenant_id == auth.tenant_id,
        )
    )
    if trabajo is None:
        raise HTTPException(404, "Trabajo no encontrado")
    return _estado_trabajo(trabajo)


@router.post("/reescaneo/trabajos/{trabajo_id}/lote")
def procesar_lote_reescaneo(
    trabajo_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    limite: int = Query(1, ge=1, le=MAX_REESCANEO_LOTE),
) -> dict[str, object]:
    _solo_administracion(auth)
    trabajo = session.scalar(
        select(TrabajoReescaneoItems)
        .where(
            TrabajoReescaneoItems.id == trabajo_id,
            TrabajoReescaneoItems.tenant_id == auth.tenant_id,
        )
        .with_for_update()
    )
    if trabajo is None:
        raise HTTPException(404, "Trabajo no encontrado")
    if trabajo.estado != "EN_PROCESO":
        return _estado_trabajo(trabajo)
    if not _OCR_LOCK.acquire(blocking=False):
        raise HTTPException(409, "El OCR está ocupado; vuelva a intentar en unos segundos")
    try:
        consulta = _facturas_query(auth)
        consulta = consulta.where(Documento.created_at <= trabajo.created_at)
        if trabajo.cursor_documento_id is not None:
            consulta = consulta.where(Documento.id > trabajo.cursor_documento_id)
        documentos = list(session.scalars(consulta.order_by(Documento.id).limit(limite)))
        for documento in documentos:
            try:
                with session.begin_nested():
                    lineas_previas = (
                        session.scalar(
                            select(func.count())
                            .select_from(LineaComprobanteItem)
                            .where(
                                LineaComprobanteItem.tenant_id == auth.tenant_id,
                                LineaComprobanteItem.documento_id == documento.id,
                            )
                        )
                        or 0
                    )
                    ruta_relativa = PurePosixPath(documento.ruta_storage)
                    if (
                        ruta_relativa.is_absolute()
                        or not ruta_relativa.parts
                        or ruta_relativa.parts[0] != str(auth.tenant_id)
                        or ".." in ruta_relativa.parts
                    ):
                        raise ValueError("RUTA_STORAGE_INVALIDA")
                    ruta = almacen.ruta_absoluta(documento.ruta_storage)
                    limite_bytes = min(MAX_DOCUMENTO_BYTES, settings.max_upload_mb * 1024 * 1024)
                    if ruta.stat().st_size > limite_bytes:
                        raise ValueError("DOCUMENTO_EXCEDE_LIMITE")
                    with ruta.open("rb") as archivo:
                        contenido = archivo.read(limite_bytes + 1)
                    if len(contenido) > limite_bytes:
                        raise ValueError("DOCUMENTO_EXCEDE_LIMITE")
                    if hashlib.sha256(contenido).hexdigest() != documento.sha256:
                        raise ValueError("HASH_DOCUMENTO_DIFERENTE")
                    if _formato(documento) == "XML":
                        nuevos = registrar_items_ubl(
                            session, auth.tenant_id, documento.id, contenido
                        )
                    elif _formato(documento) in {"PDF", "IMAGEN"}:

                        def extraer_texto(
                            contenido_documento: bytes = contenido,
                        ) -> dict[str, object]:
                            return procesar(
                                contenido_documento,
                                settings.max_extracted_chars,
                                settings.max_ocr_pdf_pages,
                            ).a_dict()

                        lectura = procesar_con_cache(
                            contenido,
                            str(auth.tenant_id),
                            settings.storage_dir / "_ocr_cache",
                            settings.max_extracted_chars,
                            settings.max_ocr_pdf_pages,
                            extraer_texto,
                        )
                        texto = lectura.get("texto")
                        nuevos = (
                            registrar_items_pdf_estacion(
                                session,
                                auth.tenant_id,
                                documento.id,
                                texto,
                            )
                            if isinstance(texto, str)
                            else 0
                        )
                    else:
                        nuevos = 0
                    if nuevos == 0 and lineas_previas == 0:
                        trabajo.requieren_revision += 1
                    trabajo.lineas_nuevas += nuevos
            except (OSError, ValueError, DocumentoNoProcesable, IntegrityError):
                trabajo.errores += 1
            trabajo.procesados += 1
            trabajo.cursor_documento_id = documento.id
            session.flush()
        if len(documentos) < limite or trabajo.procesados >= trabajo.total_documentos:
            trabajo.estado = (
                "COMPLETADO_CON_OBSERVACIONES"
                if trabajo.errores or trabajo.requieren_revision
                else "COMPLETADO"
            )
            trabajo.finalizado_at = datetime.now(UTC)
            auditoria.registrar(
                session,
                auth.tenant_id,
                "ITEMS_REESCANEO_FINALIZADO",
                "trabajo_reescaneo_items",
                trabajo.id,
                {
                    "procesados": trabajo.procesados,
                    "lineas_nuevas": trabajo.lineas_nuevas,
                    "requieren_revision": trabajo.requieren_revision,
                    "errores": trabajo.errores,
                },
            )
        session.commit()
    finally:
        _OCR_LOCK.release()
    return _estado_trabajo(trabajo)


@router.post("/reescaneo/trabajos/{trabajo_id}/cancelar")
def cancelar_reescaneo(
    trabajo_id: uuid.UUID, session: SessionDep, auth: OperativeAuthDep
) -> dict[str, object]:
    _solo_administracion(auth)
    trabajo = session.scalar(
        select(TrabajoReescaneoItems)
        .where(
            TrabajoReescaneoItems.id == trabajo_id,
            TrabajoReescaneoItems.tenant_id == auth.tenant_id,
        )
        .with_for_update()
    )
    if trabajo is None:
        raise HTTPException(404, "Trabajo no encontrado")
    if trabajo.estado == "EN_PROCESO":
        trabajo.estado = "CANCELADO"
        trabajo.finalizado_at = datetime.now(UTC)
        auditoria.registrar(
            session,
            auth.tenant_id,
            "ITEMS_REESCANEO_CANCELADO",
            "trabajo_reescaneo_items",
            trabajo.id,
            {"procesados": trabajo.procesados},
        )
        session.commit()
    return _estado_trabajo(trabajo)
