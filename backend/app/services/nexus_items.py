"""Consultas de líneas de comprobantes con alcance de Tenant y jerarquía de actor."""

from __future__ import annotations

import unicodedata
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem
from app.models import Documento, Empresa, Expediente
from app.schemas import NexusChatOut
from app.security import ContextoAcceso
from app.services.nexus_context import condiciones_expedientes


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def consulta_items_solicitada(mensaje: str) -> tuple[str, str] | None:
    """Identifica preguntas inequívocas de productos o destinos comerciales."""
    normal = _normalizar(mensaje)
    if any(p in normal for p in ("a que clientes", "a quienes les", "a quien le han emitido")):
        return ("clientes", "")
    if "de que son" in normal and any(x in normal for x in ("factura", "comprobante")):
        return ("resumen", "")
    if not any(
        x in normal
        for x in (
            "factura",
            "comprobante",
            "contiene",
            "contienen",
            "son de",
            "tiene",
            "tienen",
            "cuantos",
            "cuantas",
            "alguno",
            "alguna",
        )
    ):
        return None
    sinonimos = {
        "petroleo": ("petroleo", "diesel", "diésel", "combustible"),
        "hielo": ("hielo",),
        "viveres": ("viveres", "víveres", "abarrotes"),
        "cuadernos": ("cuaderno", "cuadernos"),
    }
    terminos = tuple(
        nombre for nombre, palabras in sinonimos.items() if any(p in normal for p in palabras)
    )
    if terminos:
        return ("producto", ",".join(terminos))
    return None


def responder_items(
    session: Session, auth: ContextoAcceso, tipo: str, busqueda: str
) -> NexusChatOut:
    """Toda unión comprueba tenant_id y el ámbito de expedientes del actor."""
    condiciones = condiciones_expedientes(session, auth)
    consulta = (
        select(Expediente, Empresa.razon_social, LineaComprobanteItem.descripcion_original)
        .join(Documento, Documento.expediente_id == Expediente.id)
        .join(
            LineaComprobanteItem,
            LineaComprobanteItem.documento_id == Documento.id,
        )
        .join(Empresa, Empresa.id == Expediente.receptor_id)
        .where(
            Expediente.tenant_id == auth.tenant_id,
            Documento.tenant_id == auth.tenant_id,
            LineaComprobanteItem.tenant_id == auth.tenant_id,
            Empresa.tenant_id == auth.tenant_id,
            Expediente.deleted_at.is_(None),
            Documento.deleted_at.is_(None),
            *condiciones,
        )
    )
    filas = session.execute(consulta).all()
    expedientes: dict[str, tuple[Expediente, str]] = {}
    conceptos: dict[str, set[str]] = defaultdict(set)
    grupos = busqueda.split(",") if busqueda else []
    sinonimos = {
        "petroleo": ("petroleo", "diesel", "combustible"),
        "hielo": ("hielo",),
        "viveres": ("viveres", "abarrotes"),
        "cuadernos": ("cuaderno",),
    }
    for expediente, cliente, descripcion in filas:
        numero = str(expediente.id)
        expedientes[numero] = (expediente, cliente)
        texto = _normalizar(descripcion)
        if tipo == "producto":
            if any(p in texto for grupo in grupos for p in sinonimos[grupo]):
                conceptos[numero].add(descripcion)
        else:
            conceptos[numero].add(descripcion)

    if tipo == "producto":
        hallados = {k: v for k, v in conceptos.items() if v}
        ejemplos = [
            f"{expedientes[clave][0].serie}-{expedientes[clave][0].correlativo}"
            for clave in list(hallados)[:5]
        ]
        texto = (
            f"Encontré {len(hallados)} comprobantes con líneas registradas relacionadas con "
            f"{busqueda.replace(',', ' o ')} dentro de tu ámbito."
        )
        if ejemplos:
            texto += " Ejemplos: " + ", ".join(ejemplos) + "."
        if not hallados:
            texto += " Esto no descarta facturas sin detalle de ítems extraído."
    elif tipo == "clientes":
        clientes = sorted(
            {cliente for clave, (_, cliente) in expedientes.items() if conceptos[clave]}
        )
        texto = (
            f"En los comprobantes con ítems registrados figuran {len(clientes)} clientes: "
            + (", ".join(clientes[:12]) if clientes else "ninguno identificado")
            + ". No incluye comprobantes sin ítems extraídos."
        )
    else:
        texto = (
            f"Tengo detalle de ítems para {len(conceptos)} comprobantes de tu ámbito. "
            "Puedes preguntarme cuántos contienen petróleo, hielo, víveres o cuadernos. "
            "Los comprobantes sin detalle extraído no pueden clasificarse con seguridad."
        )
    return NexusChatOut(
        respuesta=texto,
        accion="CONSULTAR_ITEMS",
        motor="ESPECIALISTA_ITEMS",
        datos={"comprobantes_con_items": len(expedientes), "coincidencias": len(conceptos)},
    )
