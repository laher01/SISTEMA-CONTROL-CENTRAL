"""Vista previa paginada y de solo lectura para el reescaneo histórico UBL.

La vista previa no modifica datos. El registro por página requiere una transacción
controlada por el llamador; no representa todavía una tarea durable reanudable.
"""

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Documento
from app.services.contabilidad_items_ubl import extraer_items_ubl, registrar_items_ubl
from app.storage import AlmacenLocal

MAX_PAGINA = 100
MAX_XML_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class ResultadoVistaPrevia:
    documento_id: uuid.UUID
    estado: str
    lineas_detectadas: int = 0


def previsualizar_pagina(
    session: Session,
    almacen: AlmacenLocal,
    tenant_id: uuid.UUID,
    *,
    despues_id: uuid.UUID | None = None,
    limite: int = 50,
) -> list[ResultadoVistaPrevia]:
    """Paginación por ID estable; sin carga de documentos de otros tenants."""
    if not 1 <= limite <= MAX_PAGINA:
        raise ValueError("El límite debe estar entre 1 y 100")
    consulta = select(Documento).where(
        Documento.tenant_id == tenant_id,
        Documento.deleted_at.is_(None),
    )
    if despues_id is not None:
        consulta = consulta.where(Documento.id > despues_id)
    consulta = consulta.order_by(Documento.id).limit(limite)
    resultados: list[ResultadoVistaPrevia] = []
    for documento in session.scalars(consulta):
        if not documento.nombre_original.lower().endswith(".xml"):
            resultados.append(ResultadoVistaPrevia(documento.id, "NO_XML"))
            continue
        ruta_relativa = PurePosixPath(documento.ruta_storage)
        if (
            ruta_relativa.is_absolute()
            or not ruta_relativa.parts
            or ruta_relativa.parts[0] != str(tenant_id)
            or ".." in ruta_relativa.parts
        ):
            resultados.append(ResultadoVistaPrevia(documento.id, "RUTA_FUERA_TENANT"))
            continue
        try:
            ruta = almacen.ruta_absoluta(documento.ruta_storage)
            if ruta.stat().st_size > MAX_XML_BYTES:
                resultados.append(ResultadoVistaPrevia(documento.id, "EXCEDE_LIMITE"))
                continue
            with ruta.open("rb") as archivo:
                contenido = archivo.read(MAX_XML_BYTES + 1)
            if len(contenido) > MAX_XML_BYTES:
                resultados.append(ResultadoVistaPrevia(documento.id, "EXCEDE_LIMITE"))
                continue
            if hashlib.sha256(contenido).hexdigest() != documento.sha256:
                resultados.append(ResultadoVistaPrevia(documento.id, "HASH_DIFERENTE"))
                continue
            items = extraer_items_ubl(contenido)
            estado = "XML_REVISADO" if items else "SIN_ITEMS_UBL"
            resultados.append(ResultadoVistaPrevia(documento.id, estado, len(items)))
        except (OSError, ValueError):
            resultados.append(ResultadoVistaPrevia(documento.id, "ARCHIVO_NO_DISPONIBLE"))
    return resultados


@dataclass(frozen=True)
class ResultadoLote:
    documento_id: uuid.UUID
    estado: str
    lineas_nuevas: int = 0


def registrar_pagina_verificada(
    session: Session,
    almacen: AlmacenLocal,
    tenant_id: uuid.UUID,
    *,
    despues_id: uuid.UUID | None = None,
    limite: int = 50,
) -> list[ResultadoLote]:
    """Procesa una página segura; el llamador controla commit y cursor.

    Solo persiste ítems de XML revisados. Los errores individuales no impiden
    continuar, y las escrituras se aíslan mediante savepoints por documento.
    """
    previa = previsualizar_pagina(session, almacen, tenant_id, despues_id=despues_id, limite=limite)
    resultados: list[ResultadoLote] = []
    for item in previa:
        if item.estado != "XML_REVISADO":
            resultados.append(ResultadoLote(item.documento_id, item.estado))
            continue
        documento = session.scalar(
            select(Documento).where(
                Documento.id == item.documento_id,
                Documento.tenant_id == tenant_id,
                Documento.deleted_at.is_(None),
            )
        )
        if documento is None:
            resultados.append(ResultadoLote(item.documento_id, "DOCUMENTO_NO_DISPONIBLE"))
            continue
        try:
            ruta_relativa = PurePosixPath(documento.ruta_storage)
            if (
                ruta_relativa.is_absolute()
                or not ruta_relativa.parts
                or ruta_relativa.parts[0] != str(tenant_id)
                or ".." in ruta_relativa.parts
            ):
                resultados.append(ResultadoLote(item.documento_id, "RUTA_FUERA_TENANT"))
                continue
            ruta = almacen.ruta_absoluta(documento.ruta_storage)
            if ruta.stat().st_size > MAX_XML_BYTES:
                resultados.append(ResultadoLote(item.documento_id, "EXCEDE_LIMITE"))
                continue
            with ruta.open("rb") as archivo:
                contenido = archivo.read(MAX_XML_BYTES + 1)
            if len(contenido) > MAX_XML_BYTES:
                resultados.append(ResultadoLote(item.documento_id, "EXCEDE_LIMITE"))
                continue
            if hashlib.sha256(contenido).hexdigest() != documento.sha256:
                resultados.append(ResultadoLote(item.documento_id, "HASH_DIFERENTE"))
                continue
            with session.begin_nested():
                nuevos = registrar_items_ubl(session, tenant_id, documento.id, contenido)
                session.flush()
            resultados.append(ResultadoLote(item.documento_id, "PROCESADO", nuevos))
        except (OSError, ValueError, SQLAlchemyError):
            resultados.append(ResultadoLote(item.documento_id, "ERROR_REINTENTABLE"))
    return resultados
