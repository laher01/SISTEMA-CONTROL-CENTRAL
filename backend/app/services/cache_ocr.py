"""Cache persistente de resultados OCR; aislada por tenant y version de procesamiento."""

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path

VERSION_CACHE = "ocr-core-v1"


def procesar_con_cache(
    contenido: bytes,
    tenant_id: str,
    carpeta: Path,
    limite_caracteres: int,
    max_paginas_ocr: int,
    extractor: Callable[[], dict[str, object]],
    forzar: bool = False,
) -> dict[str, object]:
    """Almacena solo extracción técnica; nunca aprobación o vinculación fiscal."""
    if not tenant_id or "/" in tenant_id or "\\" in tenant_id or tenant_id in {".", ".."}:
        raise ValueError("Identificador de tenant inválido")
    if forzar:
        return extractor()
    huella = hashlib.sha256(contenido).hexdigest()
    clave = hashlib.sha256(
        f"{VERSION_CACHE}:{huella}:{limite_caracteres}:{max_paginas_ocr}".encode()
    ).hexdigest()
    destino = carpeta / tenant_id / clave[:2] / f"{clave}.json"
    try:
        dato = json.loads(destino.read_text(encoding="utf-8"))
        if isinstance(dato, dict) and dato.get("_cache_version") == VERSION_CACHE:
            return {k: v for k, v in dato.items() if k != "_cache_version"}
    except (FileNotFoundError, ValueError, OSError, UnicodeError):
        pass
    resultado = extractor()
    if not resultado.get("requiere_ocr", False):
        temporal = None
        try:
            destino.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=destino.parent, delete=False
            ) as salida:
                temporal = Path(salida.name)
                os.chmod(temporal, 0o600)
                json.dump({"_cache_version": VERSION_CACHE, **resultado}, salida)
                salida.flush()
                os.fsync(salida.fileno())
            os.replace(temporal, destino)
        except OSError:
            pass  # La indisponibilidad de cache no debe impedir el OCR.
        finally:
            if temporal is not None:
                temporal.unlink(missing_ok=True)
    return resultado
