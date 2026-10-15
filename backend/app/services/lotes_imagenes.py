"""Planificación determinista para lotes de imágenes y decisión fiscal conservadora.

No almacena archivos ni ejecuta OCR: se integra antes de encolar trabajos.
"""

from dataclasses import dataclass
from enum import StrEnum

MAX_IMAGENES_POR_SUBLOTE = 10


def dividir_sublotes[T](
    elementos: list[T], limite: int = MAX_IMAGENES_POR_SUBLOTE
) -> list[list[T]]:
    """Preserva orden y evita grupos vacíos sin mutar el lote original."""
    if limite < 1 or limite > MAX_IMAGENES_POR_SUBLOTE:
        raise ValueError("El límite debe estar entre 1 y 10")
    return [elementos[i : i + limite] for i in range(0, len(elementos), limite)]


class DecisionFiscal(StrEnum):
    CREAR = "CREATED"
    RECHAZAR_DUPLICADO = "REJECTED_DUPLICATE"
    REVISAR_CONFLICTO = "CONFLICT_REVIEW"
    REVISION_REQUERIDA = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class IdentidadFactura:
    tenant_id: str
    ruc_emisor: str
    tipo: str
    serie: str
    correlativo: str
    ruc_receptor: str
    importe: str
    fecha_emision: str


def _completa(factura: IdentidadFactura) -> bool:
    return (
        bool(factura.tenant_id.strip())
        and factura.ruc_emisor.isdigit()
        and len(factura.ruc_emisor) == 11
        and factura.ruc_receptor.isdigit()
        and len(factura.ruc_receptor) == 11
        and all(
            valor.strip()
            for valor in (
                factura.tipo,
                factura.serie,
                factura.correlativo,
                factura.importe,
                factura.fecha_emision,
            )
        )
    )


def decidir_factura(
    nueva: IdentidadFactura, existente: IdentidadFactura | None, *, confianza_suficiente: bool
) -> DecisionFiscal:
    """Solo toma decisiones con identidad ya normalizada y OCR verificado.

    La unicidad real debe ser transaccional en BD; esta función no sustituye locks
    ni restricciones únicas ni validación de pertenencia del tenant.
    """
    if not confianza_suficiente or not _completa(nueva):
        return DecisionFiscal.REVISION_REQUERIDA
    if existente is None:
        return DecisionFiscal.CREAR
    if not _completa(existente):
        return DecisionFiscal.REVISION_REQUERIDA
    clave_nueva = (nueva.tenant_id, nueva.ruc_emisor, nueva.tipo, nueva.serie, nueva.correlativo)
    clave_existente = (
        existente.tenant_id,
        existente.ruc_emisor,
        existente.tipo,
        existente.serie,
        existente.correlativo,
    )
    if clave_nueva != clave_existente:
        return DecisionFiscal.REVISION_REQUERIDA
    if (
        nueva.ruc_receptor != existente.ruc_receptor
        or nueva.importe != existente.importe
        or nueva.fecha_emision != existente.fecha_emision
    ):
        return DecisionFiscal.REVISAR_CONFLICTO
    return DecisionFiscal.RECHAZAR_DUPLICADO
