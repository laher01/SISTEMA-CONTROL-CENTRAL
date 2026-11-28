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
BASE_APIPERU = "https://api.apiperu.dev"
RUTAS_APIPERU = {
    "coactiva": "ruc-deuda-coactiva",
    "ssco": "ruc-ssco",
    "domicilio": "ruc-domicilio-fiscal",
    "sunat": "ruc-sunat",
}
ENDPOINTS = {tipo: f"{BASE_APIPERU}/{ruta}" for tipo, ruta in RUTAS_APIPERU.items()}
PERMITIDOS: dict[str, tuple[str, ...]] = {
    tipo: (ENDPOINTS[tipo], f"https://apiperu.dev/api/{ruta}")
    for tipo, ruta in RUTAS_APIPERU.items()
}
PERMITIDOS["coactiva"] += ("https://apiperu.dev/api/ruc_deuda_coactiva/",)
FICHA_RUC_LEGACY = "https://apiperu.dev/api/ruc/"
PERMITIDOS["sunat"] += (FICHA_RUC_LEGACY,)
FUENTE_COACTIVA = ENDPOINTS["coactiva"]


def _consultar_api(url: str, ruc: str, token: str) -> object:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if url == FICHA_RUC_LEGACY:
        respuesta = httpx.get(f"{url}{ruc}", headers=headers, timeout=12)
    else:
        respuesta = httpx.post(url, json={"ruc": ruc}, headers=headers, timeout=12)
    try:
        datos = respuesta.json()
    except ValueError:
        respuesta.raise_for_status()
        raise
    if (
        respuesta.status_code == 404
        and isinstance(datos, dict)
        and datos.get("success") is False
        and datos.get("code") == "document_not_found"
    ):
        return None
    respuesta.raise_for_status()
    if not isinstance(datos, dict) or datos.get("success") is not True or datos.get("data") is None:
        raise ValueError("Respuesta no confirmada")
    return datos["data"]


def consultar_coactiva(ruc: str, token: str, endpoint: str = FUENTE_COACTIVA) -> dict[str, object]:
    datos = _consultar_api(endpoint, ruc, token)
    registros = [] if datos is None else datos
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


def consultar_ficha(
    ruc: str, token: str, tipo: str, endpoint: str | None = None
) -> dict[str, object]:
    domicilio = tipo == "domicilio"
    datos = _consultar_api(endpoint or ENDPOINTS[tipo], ruc, token)
    if datos is None:
        return {"estado_consulta": "Sin resultados"}
    if not isinstance(datos, dict):
        raise ValueError("Ficha no válida")
    claves = (
        ("direccion_completa", "departamento", "provincia", "distrito", "actividad_economica")
        if domicilio
        else (
            "ruc",
            "nombre_o_razon_social",
            "estado",
            "condicion",
            "direccion_completa",
            "tipo_contribuyente",
            "actividades_economicas",
            "fecha_inscripcion",
        )
    )
    if not domicilio and str(datos.get("ruc")) != ruc:
        raise ValueError("La ficha no corresponde al RUC")
    ficha = {k: datos[k] for k in claves if k in datos}
    if endpoint == FICHA_RUC_LEGACY:
        if "direccion_completa" not in ficha and isinstance(datos.get("direccion"), str):
            ficha["direccion_completa"] = datos["direccion"]
        ficha["fuente"] = "Ficha básica de APIPERU"
    return ficha


def consultar_ssco_apiperu(ruc: str, token: str, endpoint: str | None = None) -> dict[str, object]:
    datos = _consultar_api(endpoint or ENDPOINTS["ssco"], ruc, token)
    if datos is None:
        return {"estado": "No figura en el padrón consultado", "fuente": "APIPERU"}
    if not isinstance(datos, dict) or str(datos.get("ruc")) != ruc:
        raise ValueError("Resultado SSCO no válido")
    return {
        "estado": "Figura en el padrón",
        "fuente": "APIPERU",
        "coincidencias": [
            {
                "razon_social": datos.get("razon_social"),
                "resolucion": datos.get("resolucion"),
                "firme": datos.get("fecha_firme"),
                "publicacion": datos.get("fecha_publicacion"),
            }
        ],
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
            "fuente": "Padrón SUNAT",
            "desactualizado": _desactualizado,
            "coincidencias": coincidencias,
        }
