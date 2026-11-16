"""Metadatos del archivo individual, independientes del expediente asociado."""

import re
from collections.abc import Callable
from contextlib import suppress
from datetime import date

from app.models import Documento, Expediente

NUMERO_EN_ARCHIVO = re.compile(r"(?i)(?<![A-Z0-9])([A-Z]{1,4}[0-9]{2,3})-(\d{1,12})(?!\d)")


def _valor(datos: object, clave: str) -> str | None:
    if not isinstance(datos, dict):
        return None
    valor = datos.get(clave)
    if isinstance(valor, dict):
        valor = valor.get("valor")
    if not isinstance(valor, (str, int)):
        return None
    resultado = str(valor).strip()
    return resultado or None


def campos_individuales(documento: Documento) -> Callable[[str], str | None]:
    datos = documento.datos_extraidos or {}
    confirmado = datos.get("extraccion_confirmada")
    campos_confirmados = confirmado.get("campos") if isinstance(confirmado, dict) else None
    procesado = datos.get("procesamiento_documental")
    estructurado = procesado.get("extraccion_estructurada") if isinstance(procesado, dict) else None
    campos_extraidos = estructurado.get("campos") if isinstance(estructurado, dict) else None
    fuentes = (campos_confirmados, datos, campos_extraidos)

    partes = {"emisor": datos.get("emisor"), "receptor": datos.get("receptor")}

    def campo(clave: str) -> str | None:
        valor = next((valor for fuente in fuentes if (valor := _valor(fuente, clave))), None)
        nombre, _, parte = clave.rpartition("_")
        return valor or _valor(partes.get(parte), nombre)

    return campo


def metadatos_individuales(
    documento: Documento, *, expediente: Expediente | None = None, usar_relacion: bool = True
) -> dict[str, str | date | None]:
    """No atribuir la fecha de la factura a una guía o voucher sin extracción propia."""
    campo = campos_individuales(documento)
    serie = campo("serie")
    numero = campo("correlativo")
    fecha_texto = campo("fecha_emision")
    fecha: date | None = None
    if fecha_texto:
        with suppress(ValueError):
            fecha = date.fromisoformat(fecha_texto[:10])
    if documento.tipo_documento in ("FACT", "RHE"):
        ficha = documento.expediente if usar_relacion else expediente
        if ficha is not None:
            serie = serie or ficha.serie
            numero = numero or ficha.correlativo
            fecha = fecha or ficha.fecha_emision
    if not serie or not numero:
        coincidencia = NUMERO_EN_ARCHIVO.search(documento.nombre_original.upper())
        if coincidencia is not None:
            serie = serie or coincidencia.group(1).upper()
            numero = numero or coincidencia.group(2)
    return {
        "fecha_documento": fecha,
        "serie_documento": serie,
        "correlativo_documento": numero,
    }
