"""Metadatos del archivo individual, independientes del expediente asociado."""

import re
from contextlib import suppress
from datetime import date

from app.models import Documento


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


def metadatos_individuales(documento: Documento) -> dict[str, str | date | None]:
    """No atribuir la fecha de la factura a una guía o voucher sin extracción propia."""
    datos = documento.datos_extraidos or {}
    confirmado = datos.get("extraccion_confirmada")
    campos_confirmados = confirmado.get("campos") if isinstance(confirmado, dict) else None
    procesado = datos.get("procesamiento_documental")
    estructurado = (
        procesado.get("extraccion_estructurada") if isinstance(procesado, dict) else None
    )
    campos_extraidos = (
        estructurado.get("campos") if isinstance(estructurado, dict) else None
    )
    fuentes = (campos_confirmados, datos, campos_extraidos)
    serie = next((valor for fuente in fuentes if (valor := _valor(fuente, "serie"))), None)
    numero = next(
        (valor for fuente in fuentes if (valor := _valor(fuente, "correlativo"))), None
    )
    fecha_texto = next(
        (valor for fuente in fuentes if (valor := _valor(fuente, "fecha_emision"))), None
    )
    fecha: date | None = None
    if fecha_texto:
        with suppress(ValueError):
            fecha = date.fromisoformat(fecha_texto[:10])
    if documento.tipo_documento in ("FACT", "RHE") and documento.expediente is not None:
        serie = serie or documento.expediente.serie
        numero = numero or documento.expediente.correlativo
        fecha = fecha or documento.expediente.fecha_emision
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
