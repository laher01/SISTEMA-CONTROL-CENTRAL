"""Reglas puras de Contabilidad de Ítems: fase lógica, sin efectos sobre producción.

El registro íntegro de comprobantes debe permanecer inalterado. Este módulo
solo decide la inclusión en reportes operativos y la revisión administrativa.
"""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class EstadoAuditoria(StrEnum):
    VIGENTE = "VIGENTE"
    OBSERVADA = "OBSERVADA"
    INVALIDADA_PENDIENTE = "INVALIDADA_PENDIENTE"
    INVALIDADA_CONFIRMADA = "INVALIDADA_CONFIRMADA"


class Accion(StrEnum):
    OBSERVAR = "OBSERVAR"
    DESACTIVAR = "DESACTIVAR"
    REACTIVAR = "REACTIVAR"
    APROBAR = "APROBAR"
    REVERTIR = "REVERTIR"


ROLES_REVISORES = frozenset({"ADMINISTRACION", "ADMINISTRADOR", "GERENCIA", "GERENTE"})
ROLES_SECRETARIA = frozenset({"SECRETARIA"})
ROLES_CON_DECISION = ROLES_REVISORES | ROLES_SECRETARIA


def texto_normalizado(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", texto))


def sugerir_categoria(descripcion: str) -> str:
    """Sugerencia no vinculante: sin coincidencias => POR_CATEGORIZAR."""
    s = f" {texto_normalizado(descripcion)} "
    # Exigir palabras completas: evita confundir 'aguaje' con 'agua'.
    if " leche " in s:
        return "LACTEOS"
    if " agua " in s:
        return "BEBIDAS"
    if any(f" {palabra} " in s for palabra in ("pescado", "pota", "bonito", "caballa")):
        return "PRODUCTOS_PESQUEROS"
    return "POR_CATEGORIZAR"


@dataclass(frozen=True)
class LineaFactura:
    factura_id: str
    item_id: str
    tenant_id: str
    producto_id: str
    cantidad: Decimal
    unidad: str


@dataclass(frozen=True)
class DecisionAuditoria:
    accion: Accion
    actor_id: str
    actor_rol: str
    aprobador_id: str | None = None
    aprobador_rol: str | None = None


def validar_decision(decision: DecisionAuditoria) -> None:
    rol = decision.actor_rol.upper()
    if rol not in ROLES_CON_DECISION:
        raise PermissionError("El rol no puede cambiar el estado de auditoría")
    if decision.accion in (Accion.APROBAR, Accion.REVERTIR):
        if rol not in ROLES_REVISORES:
            raise PermissionError("Solo administración o gerencia pueden conciliar")
        if not decision.aprobador_id or not decision.aprobador_rol:
            raise ValueError("Se requiere el actor original de la decisión")
        if decision.actor_id == decision.aprobador_id:
            raise PermissionError("No se permite aprobar o revertir la propia decisión")
        if decision.aprobador_rol.upper() not in ROLES_SECRETARIA:
            raise ValueError("La conciliación requiere una decisión originada en secretaría")


def acumulados_validos(
    lineas: list[LineaFactura],
    estados_factura: dict[str, EstadoAuditoria],
    tenant_id: str,
) -> dict[tuple[str, str], Decimal]:
    """Suma por producto/unidad, excluye toda factura invalidada o en revisión.

    Evita duplicar el mismo ítem del mismo comprobante en reprocesamientos.
    La extracción y persistencia real deben tener una restricción única adicional.
    """
    acumulados: dict[tuple[str, str], Decimal] = {}
    vistos: set[tuple[str, str, str]] = set()
    for linea in lineas:
        if linea.tenant_id != tenant_id:
            continue
        llave_linea = (linea.tenant_id, linea.factura_id, linea.item_id)
        if llave_linea in vistos:
            continue
        vistos.add(llave_linea)
        if estados_factura.get(linea.factura_id) != EstadoAuditoria.VIGENTE:
            continue
        if linea.cantidad < 0:
            raise ValueError("Cantidades negativas requieren regla de notas de crédito")
        llave_producto = (linea.producto_id, linea.unidad)
        acumulados[llave_producto] = acumulados.get(llave_producto, Decimal("0")) + linea.cantidad
    return acumulados


@dataclass(frozen=True)
class ProductoReconocido:
    """Identidad verificable: no adivina presentaciones o variedades omitidas."""

    marca: str | None
    familia: str
    variante: str | None
    presentacion: str | None


def posible_mismo_producto(a: ProductoReconocido, b: ProductoReconocido) -> bool:
    """Solo fusionar cuando todos los discriminadores estén completos e iguales."""
    if not all(
        (
            a.marca,
            b.marca,
            a.familia,
            b.familia,
            a.variante,
            b.variante,
            a.presentacion,
            b.presentacion,
        )
    ):
        return False
    return all(
        texto_normalizado(x or "") == texto_normalizado(y or "")
        for x, y in (
            (a.marca, b.marca),
            (a.familia, b.familia),
            (a.variante, b.variante),
            (a.presentacion, b.presentacion),
        )
    )


def factura_incluida_en_acumulados(estado: EstadoAuditoria) -> bool:
    """No contabilizar documentos invalidos; pendiente requiere total provisional separado."""
    return estado == EstadoAuditoria.VIGENTE
