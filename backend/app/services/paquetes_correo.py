"""Extracción acotada de adjuntos documentales desde ZIP y RAR."""

import io
import zipfile
from pathlib import PurePosixPath

import rarfile  # type: ignore[import-untyped]

MAX_ENTRADAS = 100
MAX_XML_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 25 * 1024 * 1024
MAX_RELACION_COMPRESION = 200
FORMATOS = {
    ".xml": "application/xml",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
}


class PaqueteNoSeguro(ValueError):
    """El paquete excede límites o contiene entradas no admitidas."""


def extraer_xml_zip(contenido: bytes) -> list[tuple[str, bytes]]:
    return extraer_documentos_paquete(contenido, ".zip", solo_xml=True)


def extraer_documentos_paquete(
    contenido: bytes,
    extension: str,
    *,
    solo_xml: bool = False,
) -> list[tuple[str, bytes]]:
    if len(contenido) > MAX_TOTAL_BYTES:
        raise PaqueteNoSeguro("ZIP demasiado grande")
    resultado: list[tuple[str, bytes]] = []
    total = 0
    try:
        abrir = rarfile.RarFile if extension == ".rar" else zipfile.ZipFile
        with abrir(io.BytesIO(contenido)) as paquete:
            if isinstance(paquete, rarfile.RarFile) and paquete.needs_password():
                raise PaqueteNoSeguro("RAR protegido")
            entradas = paquete.infolist()
            if len(entradas) > MAX_ENTRADAS:
                raise PaqueteNoSeguro("Demasiadas entradas en ZIP")
            for entrada in entradas:
                ruta = PurePosixPath(entrada.filename.replace("\\", "/"))
                if (
                    entrada.is_dir()
                    or (isinstance(entrada, rarfile.RarInfo) and entrada.is_symlink())
                    or ruta.is_absolute()
                    or ".." in ruta.parts
                    or entrada.flag_bits & 0x1
                ):
                    raise PaqueteNoSeguro("Entrada ZIP no admitida")
                if entrada.file_size > MAX_TOTAL_BYTES:
                    raise PaqueteNoSeguro("Entrada ZIP demasiado grande")
                if entrada.file_size and (
                    not entrada.compress_size
                    or entrada.file_size > entrada.compress_size * MAX_RELACION_COMPRESION
                ):
                    raise PaqueteNoSeguro("Relación de compresión ZIP no segura")
                sufijo = ruta.suffix.lower()
                if sufijo not in FORMATOS or (solo_xml and sufijo != ".xml"):
                    continue
                limite = MAX_XML_BYTES if sufijo == ".xml" else MAX_TOTAL_BYTES
                if entrada.file_size > limite:
                    raise PaqueteNoSeguro("XML demasiado grande")
                total += entrada.file_size
                if total > MAX_TOTAL_BYTES:
                    raise PaqueteNoSeguro("ZIP excede el límite de extracción")
                with paquete.open(entrada) as archivo:
                    datos = archivo.read(limite + 1)
                if len(datos) != entrada.file_size:
                    raise PaqueteNoSeguro("Tamaño XML inconsistente")
                resultado.append((ruta.name, datos))
    except (OSError, zipfile.BadZipFile, rarfile.Error, RuntimeError) as exc:
        raise PaqueteNoSeguro("ZIP inválido o no compatible") from exc
    return resultado
