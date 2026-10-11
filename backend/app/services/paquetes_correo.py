"""Extracción acotada de XML desde contenedores ZIP y correos.

No escribe archivos en disco: evita traversal, zip bombs y anidados.
El reconocimiento de PDF multipágina y RAR se implementará por separado.
"""

import io
import zipfile
from pathlib import PurePosixPath

MAX_ENTRADAS = 100
MAX_XML_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 25 * 1024 * 1024


class PaqueteNoSeguro(ValueError):
    """El paquete excede límites o contiene entradas no admitidas."""


def extraer_xml_zip(contenido: bytes) -> list[tuple[str, bytes]]:
    if len(contenido) > MAX_TOTAL_BYTES:
        raise PaqueteNoSeguro("ZIP demasiado grande")
    resultado: list[tuple[str, bytes]] = []
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
            entradas = paquete.infolist()
            if len(entradas) > MAX_ENTRADAS:
                raise PaqueteNoSeguro("Demasiadas entradas en ZIP")
            for entrada in entradas:
                ruta = PurePosixPath(entrada.filename.replace("\\", "/"))
                if (
                    entrada.is_dir()
                    or ruta.is_absolute()
                    or ".." in ruta.parts
                    or entrada.flag_bits & 0x1
                ):
                    raise PaqueteNoSeguro("Entrada ZIP no admitida")
                if ruta.suffix.lower() != ".xml":
                    continue
                if entrada.file_size > MAX_XML_BYTES:
                    raise PaqueteNoSeguro("XML demasiado grande")
                total += entrada.file_size
                if total > MAX_TOTAL_BYTES:
                    raise PaqueteNoSeguro("ZIP excede el límite de extracción")
                with paquete.open(entrada) as archivo:
                    datos = archivo.read(MAX_XML_BYTES + 1)
                if len(datos) != entrada.file_size:
                    raise PaqueteNoSeguro("Tamaño XML inconsistente")
                resultado.append((ruta.name, datos))
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise PaqueteNoSeguro("ZIP inválido o no compatible") from exc
    return resultado
