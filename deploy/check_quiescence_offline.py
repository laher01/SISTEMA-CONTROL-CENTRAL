#!/usr/bin/env python3
"""Gate offline RC1: bloquea captura si cambia el árbol documental o el dump.

La estabilidad medida NO sustituye detener todos los escritores ni coordinar
la instantánea transaccional de PostgreSQL y el volumen documental.
"""
import hashlib
import os
import stat
import time
from pathlib import Path


def inventario(root: Path) -> tuple[tuple[str, int, str], ...]:
    """Inventario y SHA-256 de archivos regulares. Rechaza symlinks."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Raíz documental no válida")
    filas: list[tuple[str, int, str]] = []
    for carpeta, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            if (Path(carpeta) / name).is_symlink():
                raise ValueError("Directorio simbólico prohibido")
        for name in files:
            path = Path(carpeta) / name
            if path.is_symlink():
                raise ValueError("Archivo simbólico prohibido")
            digest = hashlib.sha256()
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(fd, "rb") as entrada:
                if not stat.S_ISREG(os.fstat(entrada.fileno()).st_mode):
                    raise ValueError("Archivo no regular")
                size = 0
                for chunk in iter(lambda: entrada.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
            filas.append((path.relative_to(root).as_posix(), size, digest.hexdigest()))
    return tuple(sorted(filas))


def verificar_estabilidad(documentos: Path, dump: Path, espera: float = 0) -> bool:
    if espera < 0 or espera > 60:
        raise ValueError("Espera inválida")
    if dump.is_symlink() or not dump.is_file():
        raise ValueError("Dump inválido")
    def snapshot():
        h = hashlib.sha256()
        with dump.open("rb") as entrada:
            for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
                h.update(bloque)
        return h.hexdigest(), inventario(documentos)
    inicio = snapshot()
    time.sleep(espera)
    return inicio == snapshot()
