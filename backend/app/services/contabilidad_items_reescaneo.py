"""Vista previa paginada y de solo lectura para el reescaneo histórico UBL.

No modifica originales, catálogos, líneas ni estados de auditoría.
La ejecución persistente se habilitará solo tras pruebas de aislamiento y reintentos.
"""

import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Documento
from app.services.contabilidad_items_ubl import extraer_items_ubl
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
        try:
            ruta = almacen.ruta_absoluta(documento.ruta_storage)
            if ruta.stat().st_size > MAX_XML_BYTES:
                resultados.append(ResultadoVistaPrevia(documento.id, "EXCEDE_LIMITE"))
                continue
            contenido = ruta.read_bytes()
            if hashlib.sha256(contenido).hexdigest() != documento.sha256:
                resultados.append(ResultadoVistaPrevia(documento.id, "HASH_DIFERENTE"))
                continue
            items = extraer_items_ubl(contenido)
            resultados.append(ResultadoVistaPrevia(documento.id, "XML_REVISADO", len(items)))
        except (OSError, ValueError):
            resultados.append(ResultadoVistaPrevia(documento.id, "ARCHIVO_NO_DISPONIBLE"))
    return resultados
