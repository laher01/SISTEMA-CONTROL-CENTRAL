"""Administración segura del catálogo y reescaneo idempotente de ítems."""

import hashlib
import re
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select

from app.api.deps import AlmacenDep, OperativeAuthDep, SessionDep, SettingsDep
from app.api.routes.contabilidad_items import _alcance
from app.enums import TipoDocumento
from app.item_models import (
    CategoriaItem,
    LineaComprobanteItem,
    ProductoItem,
    TrabajoReescaneoItems,
)
from app.models import Documento, Empresa, Expediente, Gestor, Miembro
from app.security import ContextoAcceso
from app.services import auditoria
from app.services.cache_ocr import procesar_con_cache
from app.services.contabilidad_items_rhe import registrar_item_rhe
from app.services.contabilidad_items_rules import sugerir_categoria, texto_normalizado
from app.services.contabilidad_items_ubl import registrar_items_pdf_estacion, registrar_items_ubl
from app.services.expedientes import expediente_tiene_documentos_activos
from app.services.procesamiento_documental import DocumentoNoProcesable, procesar

router = APIRouter(prefix="/contabilidad-items", tags=["contabilidad-items-catalogo"])
_OCR_LOCK = threading.Lock()
MAX_REESCANEO_LOTE = 3
MAX_DOCUMENTO_BYTES = 30 * 1024 * 1024
ROLES_REESCANEO = {"ADMINISTRADOR", "SECRETARIA", "GERENTE", "RESPONSABLE", "USUARIO", "GESTOR"}
VENCIMIENTO_PROCESAMIENTO = timedelta(minutes=30)


def _solo_administracion(auth: OperativeAuthDep) -> None:
    if auth.rol != "ADMINISTRADOR":
        raise HTTPException(403, "Solo Administración puede modificar el catálogo o reescanear")


def _autorizar_reescaneo(auth: OperativeAuthDep) -> None:
    if auth.rol not in ROLES_REESCANEO:
        raise HTTPException(403, "Rol sin acceso al reescaneo de ítems")


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
    descripcion: str = Field(min_length=2, max_length=2000)
    unidad_base: str = Field(min_length=1, max_length=40)
    categoria_id: uuid.UUID


class ProductoEditar(BaseModel):
    categoria_id: uuid.UUID | None = None
    activo: bool | None = None


class ClasificacionLinea(BaseModel):
    categoria: str = Field(min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, min_length=2, max_length=2000)


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


class CategoriasEliminar(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=5000)


@router.post("/categorias/eliminar")
def eliminar_categorias(
    datos: CategoriasEliminar, session: SessionDep, auth: OperativeAuthDep
) -> dict[str, int]:
    _solo_administracion(auth)
    ids = set(datos.ids)
    categorias = list(
        session.scalars(
            select(CategoriaItem)
            .where(CategoriaItem.tenant_id == auth.tenant_id, CategoriaItem.id.in_(ids))
            .order_by(CategoriaItem.id)
            .with_for_update()
        )
    )
    if len(categorias) != len(ids):
        raise HTTPException(404, "Hay categorías que ya no están disponibles")
    nombres = [categoria.nombre for categoria in categorias]
    session.query(ProductoItem).filter(
        ProductoItem.tenant_id == auth.tenant_id, ProductoItem.categoria.in_(nombres)
    ).update(
        {ProductoItem.categoria: "POR_CATEGORIZAR", ProductoItem.clasificacion_confirmada: False},
        synchronize_session=False,
    )
    for categoria in categorias:
        auditoria.registrar(
            session,
            auth.tenant_id,
            "ITEM_CATEGORIA_ELIMINADA",
            "categoria_item",
            categoria.id,
            {"nombre": categoria.nombre},
        )
        session.delete(categoria)
    session.commit()
    return {"eliminadas": len(categorias)}


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
    solo_con_lineas: bool = False,
    limite: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, object]:
    if auth.rol not in ROLES_REESCANEO:
        raise HTTPException(403, "Rol sin acceso al catálogo de ítems")
    lineas_visibles = (
        select(
            LineaComprobanteItem.producto_id.label("producto_id"),
            func.count(LineaComprobanteItem.id).label("lineas_asociadas"),
            func.min(LineaComprobanteItem.unidad).label("unidad"),
        )
        .join(Documento, Documento.id == LineaComprobanteItem.documento_id)
        .join(Expediente, Expediente.id == Documento.expediente_id)
        .where(
            LineaComprobanteItem.tenant_id == auth.tenant_id,
            Documento.tenant_id == auth.tenant_id,
            Documento.deleted_at.is_(None),
            Expediente.tenant_id == auth.tenant_id,
            Expediente.deleted_at.is_(None),
            expediente_tiene_documentos_activos(),
            _alcance(auth),
        )
        .group_by(LineaComprobanteItem.producto_id)
        .subquery()
    )
    consulta = (
        select(
            ProductoItem,
            func.coalesce(lineas_visibles.c.lineas_asociadas, 0).label("lineas_asociadas"),
            lineas_visibles.c.unidad,
        )
        .outerjoin(lineas_visibles, lineas_visibles.c.producto_id == ProductoItem.id)
        .where(ProductoItem.tenant_id == auth.tenant_id)
    )
    if solo_con_lineas or auth.rol not in {"ADMINISTRADOR", "SECRETARIA"}:
        consulta = consulta.where(lineas_visibles.c.producto_id.is_not(None))
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
                "unidad_base": producto.unidad_base or unidad or "",
                "categoria": producto.categoria,
                "categoria_confirmada": producto.clasificacion_confirmada,
                "activo": producto.activo,
                "lineas_asociadas": lineas_asociadas,
            }
            for producto, lineas_asociadas, unidad in filas
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


@router.patch("/lineas/{linea_id}/clasificacion")
def clasificar_linea_reescaneada(
    linea_id: uuid.UUID,
    datos: ClasificacionLinea,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    """Corrige metadatos solo cuando la línea está en la cartera autorizada."""
    _autorizar_reescaneo(auth)
    linea = session.scalar(
        select(LineaComprobanteItem)
        .join(Documento, Documento.id == LineaComprobanteItem.documento_id)
        .where(
            LineaComprobanteItem.id == linea_id,
            LineaComprobanteItem.tenant_id == auth.tenant_id,
            Documento.id.in_(_facturas_query(auth).with_only_columns(Documento.id)),
        )
        .with_for_update()
    )
    if linea is None:
        raise HTTPException(404, "Ítem no encontrado en la cartera autorizada")
    producto = session.scalar(
        select(ProductoItem)
        .where(ProductoItem.id == linea.producto_id, ProductoItem.tenant_id == auth.tenant_id)
        .with_for_update()
    )
    if producto is None:
        raise HTTPException(404, "Ítem no encontrado")
    if auth.rol not in {"ADMINISTRADOR", "SECRETARIA"}:
        visibles = _facturas_query(auth).with_only_columns(Documento.id)
        fuera_de_cartera = session.scalar(
            select(func.count())
            .select_from(LineaComprobanteItem)
            .join(Documento, Documento.id == LineaComprobanteItem.documento_id)
            .where(
                LineaComprobanteItem.tenant_id == auth.tenant_id,
                LineaComprobanteItem.producto_id == producto.id,
                Documento.tenant_id == auth.tenant_id,
                Documento.deleted_at.is_(None),
                Documento.id.not_in(visibles),
            )
        )
        if fuera_de_cartera:
            raise HTTPException(
                403,
                "Este ítem también aparece en comprobantes fuera de tu cartera; "
                "solicita el cambio a Administración",
            )
    nombre, normalizado = _normalizar_categoria(datos.categoria)
    if not nombre or not normalizado:
        raise HTTPException(422, "Escribe una categoría válida")
    categoria = session.scalar(
        select(CategoriaItem).where(
            CategoriaItem.tenant_id == auth.tenant_id,
            CategoriaItem.nombre_normalizado == normalizado,
        )
    )
    if categoria is None:
        categoria = CategoriaItem(
            tenant_id=auth.tenant_id,
            nombre=nombre,
            nombre_normalizado=normalizado,
            creado_por_cuenta_id=auth.cuenta_id,
        )
        session.add(categoria)
        try:
            session.flush()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(409, "La categoría se agregó en paralelo; vuelva a cargar") from exc
    anterior = producto.categoria
    producto.categoria = categoria.nombre
    producto.clasificacion_confirmada = True
    if datos.descripcion is not None:
        producto.descripcion = " ".join(datos.descripcion.split())
    auditoria.registrar(
        session,
        auth.tenant_id,
        "ITEMS_LINEA_CLASIFICADA",
        "producto_item",
        producto.id,
        {
            "categoria_anterior": anterior,
            "categoria": producto.categoria,
            "descripcion_actualizada": datos.descripcion is not None,
        },
    )
    session.commit()
    return {
        "linea_id": str(linea.id),
        "producto_id": str(producto.id),
        "categoria": producto.categoria,
        "categoria_confirmada": producto.clasificacion_confirmada,
        "descripcion": producto.descripcion,
    }


def _facturas_query(auth: OperativeAuthDep) -> Select[tuple[Documento]]:
    consulta = select(Documento).where(
        Documento.tenant_id == auth.tenant_id,
        Documento.deleted_at.is_(None),
        Documento.tipo_documento.in_([TipoDocumento.FACT, TipoDocumento.RHE]),
    )
    if auth.rol not in {"ADMINISTRADOR", "SECRETARIA"}:
        consulta = consulta.join(Expediente, Expediente.id == Documento.expediente_id).where(
            Expediente.tenant_id == auth.tenant_id,
            Expediente.deleted_at.is_(None),
            _alcance(auth),
        )
    return consulta


def _contexto_trabajo(trabajo: TrabajoReescaneoItems) -> ContextoAcceso:
    return ContextoAcceso(
        cuenta_id=trabajo.solicitado_por_cuenta_id,
        tenant_id=trabajo.tenant_id,
        rol=trabajo.solicitado_por_rol,
        miembro_id=trabajo.solicitado_por_miembro_id,
        gestor_id=trabajo.solicitado_por_gestor_id,
        usuario_id=trabajo.solicitado_por_usuario_id,
        codigo=trabajo.solicitado_por_codigo,
        nombre="",
        cambio_clave_obligatorio=False,
    )


def _verificar_acceso_trabajo(trabajo: TrabajoReescaneoItems, auth: OperativeAuthDep) -> None:
    if trabajo.tenant_id != auth.tenant_id:
        raise HTTPException(404, "Trabajo no encontrado")
    if auth.rol == "ADMINISTRADOR":
        return
    if auth.cuenta_id != trabajo.solicitado_por_cuenta_id:
        raise HTTPException(404, "Trabajo no encontrado")
    identidad_actual = (
        auth.rol,
        auth.miembro_id,
        auth.usuario_id,
        auth.gestor_id,
    )
    identidad_solicitante = (
        trabajo.solicitado_por_rol,
        trabajo.solicitado_por_miembro_id,
        trabajo.solicitado_por_usuario_id,
        trabajo.solicitado_por_gestor_id,
    )
    if identidad_actual != identidad_solicitante:
        raise HTTPException(404, "Trabajo no encontrado")


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
        "documento_actual_id": str(trabajo.documento_actual_id)
        if trabajo.documento_actual_id
        else None,
        "solicitado_por_rol": trabajo.solicitado_por_rol,
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
    _autorizar_reescaneo(auth)
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
        select(Documento.tipo_documento, formato, tiene_lineas, func.count())
        .where(
            Documento.id.in_(_facturas_query(auth).with_only_columns(Documento.id)),
        )
        .group_by(Documento.tipo_documento, formato, tiene_lineas)
    ).all()
    por_formato = {"XML": 0, "PDF": 0, "IMAGEN": 0, "OTRO": 0}
    por_tipo = {"FACT": 0, "RHE": 0}
    total = con_lineas = 0
    for tipo_documento, tipo_formato, tiene, cantidad in resumen:
        por_tipo[str(tipo_documento)] += cantidad
        por_formato[tipo_formato] += cantidad
        total += cantidad
        con_lineas += cantidad if tiene else 0
    return {
        "facturas": total,
        "por_tipo": por_tipo,
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
    _autorizar_reescaneo(auth)
    consulta = select(TrabajoReescaneoItems).where(
        TrabajoReescaneoItems.tenant_id == auth.tenant_id
    )
    if auth.rol != "ADMINISTRADOR":
        consulta = consulta.where(TrabajoReescaneoItems.solicitado_por_cuenta_id == auth.cuenta_id)
    trabajos = session.scalars(consulta.order_by(TrabajoReescaneoItems.created_at.desc()).limit(10))
    return [_estado_trabajo(trabajo) for trabajo in trabajos]


@router.post("/reescaneo/trabajos", status_code=201)
def iniciar_reescaneo(session: SessionDep, auth: OperativeAuthDep) -> dict[str, object]:
    _autorizar_reescaneo(auth)
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
        solicitado_por_rol=auth.rol,
        solicitado_por_miembro_id=auth.miembro_id,
        solicitado_por_usuario_id=auth.usuario_id,
        solicitado_por_gestor_id=auth.gestor_id,
        solicitado_por_codigo=auth.codigo,
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
    _autorizar_reescaneo(auth)
    trabajo = session.scalar(
        select(TrabajoReescaneoItems).where(
            TrabajoReescaneoItems.id == trabajo_id,
            TrabajoReescaneoItems.tenant_id == auth.tenant_id,
        )
    )
    if trabajo is None:
        raise HTTPException(404, "Trabajo no encontrado")
    _verificar_acceso_trabajo(trabajo, auth)
    return _estado_trabajo(trabajo)


def _consulta_documento_ruta(
    contexto: ContextoAcceso, documento_id: uuid.UUID
) -> Select[tuple[Documento, Expediente, str, str, str, str, str]]:
    gerente = aliased(Miembro)
    usuario = aliased(Miembro)
    responsable = aliased(Miembro)
    gestor = aliased(Gestor)
    return (
        select(
            Documento,
            Expediente,
            Empresa.razon_social,
            gerente.nombre,
            responsable.nombre,
            usuario.nombre,
            gestor.nombre,
        )
        .outerjoin(
            Expediente,
            (Expediente.id == Documento.expediente_id)
            & (Expediente.tenant_id == contexto.tenant_id),
        )
        .outerjoin(
            Empresa,
            (Empresa.id == Expediente.emisor_id) & (Empresa.tenant_id == contexto.tenant_id),
        )
        .outerjoin(
            gerente,
            (gerente.id == Expediente.gerente_id) & (gerente.tenant_id == contexto.tenant_id),
        )
        .outerjoin(
            usuario,
            (usuario.id == Expediente.usuario_id) & (usuario.tenant_id == contexto.tenant_id),
        )
        .outerjoin(
            responsable,
            (responsable.id == usuario.responsable_id)
            & (responsable.tenant_id == contexto.tenant_id),
        )
        .outerjoin(
            gestor,
            (gestor.id == func.coalesce(Expediente.gestor_id, Documento.gestor_id))
            & (gestor.tenant_id == contexto.tenant_id),
        )
        .where(
            Documento.id == documento_id,
            Documento.id.in_(_facturas_query(contexto).with_only_columns(Documento.id)),
        )
    )


def _documento_json(
    fila: Row[
        tuple[
            Documento,
            Expediente,
            str,
            str,
            str,
            str,
            str,
        ]
    ],
) -> dict[str, object]:
    documento, expediente, proveedor, gerente, responsable, usuario, gestor = fila
    ruta = ["Administrador"]
    ruta.extend(nombre for nombre in (gerente, responsable, usuario, gestor) if nombre)
    return {
        "documento_id": str(documento.id),
        "tipo_documento": str(documento.tipo_documento or "OTRO"),
        "comprobante": (
            f"{expediente.serie}-{expediente.correlativo}"
            if expediente is not None
            else documento.nombre_original
        ),
        "fecha_emision": expediente.fecha_emision.isoformat() if expediente is not None else None,
        "emisor": proveedor or "",
        "ruta_jerarquica": ruta,
    }


@router.get("/reescaneo/trabajos/{trabajo_id}/resultado")
def resultado_trabajo(
    trabajo_id: uuid.UUID, session: SessionDep, auth: OperativeAuthDep
) -> dict[str, object]:
    _autorizar_reescaneo(auth)
    trabajo = session.scalar(
        select(TrabajoReescaneoItems).where(
            TrabajoReescaneoItems.id == trabajo_id,
            TrabajoReescaneoItems.tenant_id == auth.tenant_id,
        )
    )
    if trabajo is None:
        raise HTTPException(404, "Trabajo no encontrado")
    _verificar_acceso_trabajo(trabajo, auth)
    contexto = _contexto_trabajo(trabajo)
    documento_info = None
    documento_id = trabajo.documento_actual_id or trabajo.cursor_documento_id
    if documento_id is not None:
        fila = session.execute(_consulta_documento_ruta(contexto, documento_id)).first()
        if fila is not None:
            documento_info = _documento_json(fila)
    lineas: list[dict[str, object]] = []
    if trabajo.cursor_documento_id is not None:
        ids_procesados = (
            _facturas_query(contexto)
            .where(
                Documento.created_at <= trabajo.created_at,
                Documento.id <= trabajo.cursor_documento_id,
            )
            .with_only_columns(Documento.id)
        )
        gerente = aliased(Miembro)
        usuario = aliased(Miembro)
        responsable = aliased(Miembro)
        gestor = aliased(Gestor)
        filas = session.execute(
            select(
                LineaComprobanteItem,
                ProductoItem,
                Documento,
                Expediente,
                Empresa.razon_social,
                gerente.nombre,
                responsable.nombre,
                usuario.nombre,
                gestor.nombre,
            )
            .join(ProductoItem, ProductoItem.id == LineaComprobanteItem.producto_id)
            .join(Documento, Documento.id == LineaComprobanteItem.documento_id)
            .outerjoin(
                Expediente,
                (Expediente.id == Documento.expediente_id)
                & (Expediente.tenant_id == auth.tenant_id),
            )
            .outerjoin(
                Empresa,
                (Empresa.id == Expediente.emisor_id) & (Empresa.tenant_id == auth.tenant_id),
            )
            .outerjoin(
                gerente,
                (gerente.id == Expediente.gerente_id) & (gerente.tenant_id == auth.tenant_id),
            )
            .outerjoin(
                usuario,
                (usuario.id == Expediente.usuario_id) & (usuario.tenant_id == auth.tenant_id),
            )
            .outerjoin(
                responsable,
                (responsable.id == usuario.responsable_id)
                & (responsable.tenant_id == auth.tenant_id),
            )
            .outerjoin(
                gestor,
                (gestor.id == func.coalesce(Expediente.gestor_id, Documento.gestor_id))
                & (gestor.tenant_id == auth.tenant_id),
            )
            .where(
                LineaComprobanteItem.tenant_id == auth.tenant_id,
                ProductoItem.tenant_id == auth.tenant_id,
                Documento.tenant_id == auth.tenant_id,
                Documento.id.in_(ids_procesados),
                Documento.id != trabajo.documento_actual_id,
            )
            .order_by(Documento.id.desc(), LineaComprobanteItem.numero_linea)
            .limit(100)
        ).all()
        for (
            linea,
            producto,
            documento,
            expediente,
            emisor,
            gerente_nombre,
            resp_nombre,
            usuario_nombre,
            gestor_nombre,
        ) in filas:
            ruta = ["Administrador"]
            ruta.extend(
                nombre
                for nombre in (gerente_nombre, resp_nombre, usuario_nombre, gestor_nombre)
                if nombre
            )
            lineas.append(
                {
                    "linea_id": str(linea.id),
                    "producto_id": str(producto.id),
                    "descripcion": producto.descripcion,
                    "descripcion_original": linea.descripcion_original,
                    "unidad": linea.unidad,
                    "categoria": producto.categoria,
                    "categoria_sugerida": sugerir_categoria(linea.descripcion_original),
                    "categoria_confirmada": producto.clasificacion_confirmada,
                    "factura": {
                        "documento_id": str(documento.id),
                        "tipo_documento": str(documento.tipo_documento or "OTRO"),
                        "comprobante": (
                            f"{expediente.serie}-{expediente.correlativo}"
                            if expediente is not None
                            else documento.nombre_original
                        ),
                        "fecha_emision": (
                            expediente.fecha_emision.isoformat() if expediente is not None else None
                        ),
                        "emisor": emisor or "",
                        "ruta_jerarquica": ruta,
                    },
                }
            )
    return {
        "trabajo": _estado_trabajo(trabajo),
        "documento_actual": documento_info if trabajo.documento_actual_id else None,
        "ultima_factura": documento_info if not trabajo.documento_actual_id else None,
        "items": lineas,
        "limite_items_visibles": 100,
    }


@router.post("/reescaneo/trabajos/{trabajo_id}/lote")
def procesar_lote_reescaneo(
    trabajo_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    limite: int = Query(1, ge=1, le=MAX_REESCANEO_LOTE),
) -> dict[str, object]:
    _autorizar_reescaneo(auth)
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
    _verificar_acceso_trabajo(trabajo, auth)
    if trabajo.estado != "EN_PROCESO":
        return _estado_trabajo(trabajo)
    inicio_actual = trabajo.documento_actual_started_at
    if inicio_actual is not None and inicio_actual.tzinfo is None:
        inicio_actual = inicio_actual.replace(tzinfo=UTC)
    if (
        trabajo.documento_actual_id is not None
        and inicio_actual is not None
        and inicio_actual > datetime.now(UTC) - VENCIMIENTO_PROCESAMIENTO
    ):
        raise HTTPException(409, "La factura actual todavía se está procesando")
    if not _OCR_LOCK.acquire(blocking=False):
        raise HTTPException(409, "El OCR está ocupado; vuelva a intentar en unos segundos")
    try:
        contexto = _contexto_trabajo(trabajo)
        consulta = _facturas_query(contexto).where(Documento.created_at <= trabajo.created_at)
        documento_reintentable = trabajo.documento_actual_id
        if documento_reintentable is not None:
            consulta = consulta.where(Documento.id == documento_reintentable)
        elif trabajo.cursor_documento_id is not None:
            consulta = consulta.where(Documento.id > trabajo.cursor_documento_id)
        documentos = list(session.scalars(consulta.order_by(Documento.id).limit(limite)))
        if documento_reintentable is not None and not documentos:
            # El objetivo puede haberse retirado o salido del alcance desde el lote anterior.
            # Avanzar el cursor como error evita atascar indefinidamente el trabajo del tenant.
            trabajo.errores += 1
            trabajo.procesados += 1
            trabajo.cursor_documento_id = documento_reintentable
            trabajo.documento_actual_id = None
            trabajo.documento_actual_started_at = None
            session.commit()
            session.refresh(trabajo)
            consulta_siguiente = _facturas_query(_contexto_trabajo(trabajo)).where(
                Documento.created_at <= trabajo.created_at,
                Documento.id > documento_reintentable,
            )
            documentos = list(
                session.scalars(consulta_siguiente.order_by(Documento.id).limit(limite))
            )
        for documento in documentos:
            trabajo.documento_actual_id = documento.id
            trabajo.documento_actual_started_at = datetime.now(UTC)
            session.commit()
            nuevos = 0
            lineas_previas = 0
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
                        if isinstance(texto, str) and documento.tipo_documento == TipoDocumento.RHE:
                            nuevos = registrar_item_rhe(
                                session, auth.tenant_id, documento.id, texto
                            )
                        elif isinstance(texto, str):
                            nuevos = registrar_items_pdf_estacion(
                                session, auth.tenant_id, documento.id, texto
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
            trabajo.documento_actual_id = None
            trabajo.documento_actual_started_at = None
            session.flush()
            session.commit()
            documento_reintentable = None
            session.refresh(trabajo)
            if trabajo.estado != "EN_PROCESO":
                break
        contexto = _contexto_trabajo(trabajo)
        consulta_pendientes = _facturas_query(contexto).where(
            Documento.created_at <= trabajo.created_at
        )
        if trabajo.cursor_documento_id is not None:
            consulta_pendientes = consulta_pendientes.where(
                Documento.id > trabajo.cursor_documento_id
            )
        pendientes = (
            session.scalar(
                select(func.count()).select_from(
                    consulta_pendientes.with_only_columns(Documento.id).subquery()
                )
            )
            or 0
        )
        session.refresh(trabajo)
        if trabajo.estado == "EN_PROCESO" and (
            not pendientes or trabajo.procesados >= trabajo.total_documentos
        ):
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
    _autorizar_reescaneo(auth)
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
    _verificar_acceso_trabajo(trabajo, auth)
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
