"""Consultas de líneas de comprobantes con alcance de Tenant y jerarquía de actor."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.enums import TipoDocumento
from app.item_models import LineaComprobanteItem
from app.models import Documento, Empresa, Expediente
from app.schemas import NexusChatOut
from app.security import ContextoAcceso
from app.services.nexus_context import condiciones_expedientes


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _contiene_termino(texto: str, termino: str) -> bool:
    """Evita falsos positivos como 'agua' dentro de 'aguardiente'."""
    return re.search(r"(?<!\w)" + re.escape(termino) + r"(?:s|es)?(?!\w)", texto) is not None


def consulta_items_solicitada(mensaje: str) -> tuple[str, str] | None:
    """Reconocer conceptos comerciales con tolerancia a errores frecuentes."""
    normal = _normalizar(mensaje)
    if any(p in normal for p in ("a que clientes", "a quienes les", "a quien le han emitido")):
        return ("clientes", "")
    if "de que son" in normal and any(x in normal for x in ("factura", "comprobante")):
        return ("resumen", "")
    conceptos = {
        "petroleo": ("petroleo", "petrpoleo", "diesel", "combustible"),
        "hielo": ("hielo",),
        "viveres": ("viveres", "abarrotes"),
        "cuadernos": ("cuaderno",),
        "llantas": ("llanta", "neumatico"),
        "agua": ("agua",),
        "sporade": ("sporade", "sporada"),
    }
    encontrados = [
        clave
        for clave, variantes in conceptos.items()
        if any(_contiene_termino(normal, v) for v in variantes)
    ]
    if encontrados:
        return ("producto", ",".join(encontrados))
    # Preguntas abiertas: extraer el concepto después de "de" o "contienen".
    coincide = re.search(
        r"(?:facturas? de|facrturas? de|comprobantes? de|contienen? |y de )"
        r"([a-z0-9 ]{3,55})",
        normal,
    )
    if coincide:
        termino = coincide.group(1).strip(" ?.")
        termino = re.sub(
            r"\s+(?:hay|tenemos|tienen|tiene|en\s+facturas|por\s+favor)$",
            "",
            termino,
        ).strip()
        if termino:
            return ("libre", termino)
    return None


def _grupos_coincidentes(
    descripcion: str, grupos: list[str], sinonimos: dict[str, tuple[str, ...]]
) -> list[str]:
    texto = _normalizar(descripcion)
    return [
        grupo
        for grupo in grupos
        if any(_contiene_termino(texto, termino) for termino in sinonimos.get(grupo, (grupo,)))
    ]


def _diesel_en_factura_procesada(datos: object) -> bool:
    """Solo evidencias de una línea de venta, nunca menciones aisladas de combustible."""
    if not isinstance(datos, dict):
        return False
    procesamiento = datos.get("procesamiento_documental")
    if not isinstance(procesamiento, dict):
        return False
    texto = procesamiento.get("texto")
    if not isinstance(texto, str):
        return False
    compacto = " ".join(_normalizar(texto).split())
    if "factura" not in compacto:
        return False
    return bool(
        re.search(
            r"\b(?:gll|gal|galones)\s+(?:[a-z0-9-]+\s+){0,3}diesel\s+b5\s+s50\b",
            compacto,
        )
    )


def seguimiento_proveedor(mensaje: str, historial: list[object]) -> tuple[str, str] | None:
    """Recupera el último filtro de producto del historial de esta solicitud."""
    normal = _normalizar(mensaje)
    coincide = re.search(r"(?:cuantas?|cuantos?|cuales?)\s+(?:son\s+)?de\s+([\w ]+)", normal)
    if not coincide:
        return None
    nombre = coincide.group(1).strip(" ?.!")
    if len(nombre) < 4:
        return None
    for entrada in reversed(historial[-20:]):
        if getattr(entrada, "autor", None) != "usuario":
            continue
        consulta = consulta_items_solicitada(str(getattr(entrada, "texto", "")))
        if consulta and consulta[0] in {"producto", "libre"}:
            return consulta[1], nombre
    return None


def _numero_visible(expediente: Expediente) -> str:
    serie = str(expediente.serie or "").strip()
    correlativo = str(expediente.correlativo or "").strip()
    if serie.startswith(("F", "B", "E")) and correlativo.isdigit():
        return f"{serie}-{correlativo}"
    return "número fiscal por verificar"


def responder_items(
    session: Session, auth: ContextoAcceso, tipo: str, busqueda: str, proveedor: str | None = None
) -> NexusChatOut:
    """Toda unión comprueba tenant_id y el ámbito de expedientes del actor."""
    condiciones = condiciones_expedientes(session, auth)
    Emisor = aliased(Empresa)
    filtro_emisor = [Emisor.razon_social.ilike(f"%{proveedor}%")] if proveedor else []
    consulta = (
        select(Expediente, Empresa.razon_social, LineaComprobanteItem.descripcion_original)
        .join(Documento, Documento.expediente_id == Expediente.id)
        .join(
            LineaComprobanteItem,
            LineaComprobanteItem.documento_id == Documento.id,
        )
        .join(Empresa, Empresa.id == Expediente.receptor_id)
        .join(Emisor, Emisor.id == Expediente.emisor_id)
        .where(
            Expediente.tenant_id == auth.tenant_id,
            Documento.tenant_id == auth.tenant_id,
            LineaComprobanteItem.tenant_id == auth.tenant_id,
            Empresa.tenant_id == auth.tenant_id,
            Emisor.tenant_id == auth.tenant_id,
            *filtro_emisor,
            Expediente.deleted_at.is_(None),
            Documento.deleted_at.is_(None),
            *condiciones,
        )
    )
    filas = session.execute(consulta).all()
    expedientes: dict[str, tuple[Expediente, str]] = {}
    conceptos: dict[str, set[str]] = defaultdict(set)
    por_grupo: dict[str, set[str]] = defaultdict(set)
    grupos = busqueda.split(",") if busqueda else []
    sinonimos = {
        "petroleo": ("petroleo", "diesel", "combustible"),
        "hielo": ("hielo",),
        "viveres": ("viveres", "abarrotes"),
        "cuadernos": ("cuaderno",),
        "llantas": ("llanta", "neumatico"),
        "agua": ("agua",),
        "sporade": ("sporade",),
    }
    for expediente, cliente, descripcion in filas:
        numero = str(expediente.id)
        expedientes[numero] = (expediente, cliente)
        if tipo in {"producto", "libre"}:
            coincidentes = _grupos_coincidentes(descripcion, grupos, sinonimos)
            if coincidentes:
                conceptos[numero].add(descripcion)
                for grupo in coincidentes:
                    por_grupo[grupo].add(numero)
        else:
            conceptos[numero].add(descripcion)

    evidencias_pdf: set[str] = set()
    if tipo == "producto" and "petroleo" in grupos:
        # Solo documentos FACT ya vinculados a expedientes autorizados.
        pendientes = (
            select(Expediente, Empresa.razon_social, Documento.datos_extraidos)
            .join(Documento, Documento.expediente_id == Expediente.id)
            .join(Empresa, Empresa.id == Expediente.receptor_id)
            .join(Emisor, Emisor.id == Expediente.emisor_id)
            .where(
                Expediente.tenant_id == auth.tenant_id,
                Documento.tenant_id == auth.tenant_id,
                Empresa.tenant_id == auth.tenant_id,
                Emisor.tenant_id == auth.tenant_id,
                *filtro_emisor,
                Documento.tipo_documento == TipoDocumento.FACT,
                Expediente.deleted_at.is_(None),
                Documento.deleted_at.is_(None),
                *condiciones,
            )
        )
        for expediente, cliente, datos in session.execute(pendientes):
            numero = str(expediente.id)
            if numero in por_grupo["petroleo"]:
                continue
            if _diesel_en_factura_procesada(datos):
                expedientes[numero] = (expediente, cliente)
                conceptos[numero].add("DIESEL B5 S50 (evidencia PDF/OCR)")
                por_grupo["petroleo"].add(numero)
                evidencias_pdf.add(numero)

    if tipo in {"producto", "libre"}:
        hallados = {k: v for k, v in conceptos.items() if v}
        ejemplos = [_numero_visible(expedientes[clave][0]) for clave in list(hallados)[:5]]
        texto = (
            f"Encontré {len(hallados)} comprobantes con líneas registradas relacionadas con "
            f"{busqueda.replace(',', ' o ')} dentro de tu ámbito."
        )
        if proveedor:
            texto += f" Filtro de proveedor: {proveedor}."
        if len(grupos) > 1:
            desglose = ", ".join(f"{grupo}: {len(por_grupo[grupo])}" for grupo in grupos)
            texto += f" Desglose por producto: {desglose}. Un comprobante puede contener varios."
        if evidencias_pdf:
            texto += (
                f" {len(evidencias_pdf)} coincidencia(s) provienen de texto PDF/OCR "
                "y requieren confirmar el ítem antes de consolidar contabilidad."
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
        datos={
            "comprobantes_con_items": len(expedientes),
            "coincidencias": len(conceptos),
            "evidencias_pdf_pendientes_confirmacion": len(evidencias_pdf),
            "coincidencias_por_producto": {k: len(v) for k, v in por_grupo.items()},
        },
    )
