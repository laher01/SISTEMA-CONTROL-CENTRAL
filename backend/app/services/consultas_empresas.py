"""Consultas externas de solo lectura por RUC."""

import re
from decimal import Decimal
from io import BytesIO
from threading import Lock
from time import monotonic
from zipfile import BadZipFile, ZipFile

import httpx
from openpyxl import load_workbook  # type: ignore[import-untyped]
from openpyxl.utils.exceptions import InvalidFileException  # type: ignore[import-untyped]

FUENTE_SSCO = "https://www.sunat.gob.pe/padronesnotificaciones/sujeSinCapacidadOperativa.html"
ARCHIVO_SSCO = "https://www.sunat.gob.pe/padronesnotificaciones/ssco/sujesincapacidadOperativa.xlsx"
FUENTE_COACTIVA = "https://apiperu.dev/api/ruc_deuda_coactiva/"


def consultar_coactiva(ruc: str, token: str) -> dict[str, object]:
    respuesta = httpx.post(
        FUENTE_COACTIVA,
        json={"ruc": ruc},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=12,
    )
    respuesta.raise_for_status()
    datos = respuesta.json()
    if not isinstance(datos, dict) or datos.get("success") is not True:
        raise ValueError("Respuesta de deuda no confirmada")
    registros = datos.get("data")
    if not isinstance(registros, list):
        raise ValueError("Respuesta de deuda incompleta")
    total = Decimal(0)
    for registro in registros:
        if not isinstance(registro, dict):
            raise ValueError("Registro de deuda inválido")
        monto = Decimal(str(registro.get("monto")))
        if not monto.is_finite() or monto < 0:
            raise ValueError("Monto de deuda inválido")
        total += monto
    return {
        "estado": "Con deuda" if total > 0 else "Sin deuda",
        "monto": format(total, "f"),
        "registros": len(registros),
    }


def consultar_razon_social(ruc: str, token: str) -> str | None:
    try:
        respuesta = httpx.get(
            f"https://apiperu.dev/api/ruc/{ruc}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=8,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
        if isinstance(datos, dict) and isinstance(datos.get("data"), dict):
            nombre = datos["data"].get("nombre_o_razon_social")
            if isinstance(nombre, str) and nombre.strip():
                return nombre.strip()
    except (httpx.HTTPError, ValueError):
        return None
    return None


def leer_padron(contenido: bytes) -> dict[str, list[dict[str, str]]]:
    archivo = BytesIO(contenido)
    with ZipFile(archivo) as zip_xlsx:
        if sum(e.file_size for e in zip_xlsx.infolist()) > 32 * 1024 * 1024:
            raise ValueError("Padrón descomprimido demasiado grande")
    libro = load_workbook(archivo, read_only=True, data_only=True, keep_links=False)
    try:
        filas = libro["Hoja1"].iter_rows(max_col=9, values_only=True)
        cabecera = [str(c or "").casefold() for c in next(filas, ())]
        if (
            len(cabecera) != 9
            or cabecera[0].strip() != "ruc"
            or "razón social" not in cabecera[1]
            or "resolución" not in cabecera[3]
            or "publicación" not in cabecera[8]
        ):
            raise ValueError("Formato de padrón desconocido")
        padron: dict[str, list[dict[str, str]]] = {}
        for fila in filas:
            if not any(c is not None for c in fila):
                continue
            ruc = str(fila[0]).strip()
            if not re.fullmatch(r"[0-9]{11}", ruc) or not all(fila[i] for i in (1, 3, 5, 8)):
                raise ValueError("Fila incompleta en el padrón")
            padron.setdefault(ruc, []).append(
                dict(
                    razon_social=str(fila[1]),
                    resolucion=str(fila[3]),
                    firme=str(fila[5]).split(" ")[0],
                    publicacion=str(fila[8]).split(" ")[0],
                )
            )
        if not padron:
            raise ValueError("Padrón vacío")
        return padron
    finally:
        libro.close()


def descargar(url: str) -> bytes:
    contenido = bytearray()
    with httpx.stream("GET", url, timeout=12) as respuesta:
        respuesta.raise_for_status()
        for bloque in respuesta.iter_bytes():
            contenido.extend(bloque)
            if len(contenido) > 16 * 1024 * 1024:
                raise ValueError("Padrón demasiado grande")
    return bytes(contenido)


_lock = Lock()
_padron: tuple[str, dict[str, list[dict[str, str]]]] | None = None
_proxima_revision = 0.0
_desactualizado = False


def consultar_ssco(ruc: str) -> dict[str, object]:
    global _padron, _proxima_revision, _desactualizado
    with _lock:
        if monotonic() >= _proxima_revision:
            try:
                pagina = descargar(FUENTE_SSCO).decode("utf-8")
                corte_publicado = re.search(
                    r"Información actualizada al\s+(\d{1,2}\s+de\s+[a-záéíóú]+\s+del?\s+\d{4})",
                    pagina,
                    re.I,
                )
                if corte_publicado is None:
                    raise ValueError("Padrón sin fecha de corte")
                _padron = corte_publicado[1], leer_padron(descargar(ARCHIVO_SSCO))
                _desactualizado = False
                _proxima_revision = monotonic() + 3600
            except (httpx.HTTPError, ValueError, BadZipFile, InvalidFileException, KeyError):
                _desactualizado = True
                _proxima_revision = monotonic() + 60
        if _padron is None:
            raise ValueError("Padrón no disponible")
        corte, padron = _padron
        coincidencias = padron.get(ruc, [])
        return {
            "estado": "Figura en el padrón"
            if coincidencias
            else "No figura en el padrón consultado",
            "corte": corte,
            "desactualizado": _desactualizado,
            "coincidencias": coincidencias,
        }
