#!/usr/bin/env python3
"""Respaldo y restauración OFFLINE de un árbol documental aislado.

No conecta con la VPS ni Docker. Requiere directorios suministrados explícitamente.
No es un snapshot consistente frente a escrituras concurrentes.
"""

import argparse
import hashlib
import io
import os
import tarfile
import tempfile
from pathlib import Path


def respaldo(origen: Path, archivo: Path) -> str:
    origen = origen.resolve(strict=True)
    if not origen.is_dir():
        raise ValueError("El origen no es directorio")
    archivo = archivo.absolute()
    if archivo.exists() or archivo.is_relative_to(origen):
        raise ValueError("El archivo de respaldo debe ser nuevo y estar fuera del origen")
    with tempfile.NamedTemporaryFile(dir=archivo.parent, delete=False) as temporal:
        parcial = Path(temporal.name)
    try:
        with tarfile.open(parcial, "w") as salida:
            for ruta in sorted(origen.rglob("*")):
                if ruta.is_symlink():
                    raise ValueError("No se admiten enlaces simbólicos")
                if not ruta.is_file() and not ruta.is_dir():
                    raise ValueError("Tipo de archivo no admitido")
                salida.add(ruta, arcname=ruta.relative_to(origen).as_posix(), recursive=False)
        digest = hashlib.sha256(parcial.read_bytes()).hexdigest()
        with archivo.open("xb") as destino, parcial.open("rb") as entrada:
            for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
                destino.write(bloque)
        return digest
    finally:
        parcial.unlink(missing_ok=True)


def restaurar(archivo: Path, destino: Path, sha256: str) -> int:
    if not archivo.is_file() or not sha256 or len(sha256) != 64:
        raise ValueError("Respaldo o huella inválidos")
    digest = hashlib.sha256()
    with archivo.open("rb") as entrada:
        for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
            digest.update(bloque)
    if digest.hexdigest() != sha256:
        raise ValueError("La huella del respaldo no coincide")
    if destino.exists():
        raise ValueError("El directorio destino ya existe: no se sobrescribe")
    with tarfile.open(archivo, "r") as origen:
        miembros = origen.getmembers()
        nombres = set()
        for miembro in miembros:
            ruta = Path(miembro.name)
            if (
                not ruta.parts
                or ruta.is_absolute()
                or ".." in ruta.parts
                or miembro.name in nombres
                or not (miembro.isfile() or miembro.isdir())
            ):
                raise ValueError("Entrada insegura en archivo")
            nombres.add(miembro.name)
        destino.mkdir(mode=0o700)
        try:
            for miembro in miembros:
                ruta = destino / miembro.name
                if miembro.isdir():
                    ruta.mkdir(parents=True, exist_ok=True)
                else:
                    ruta.parent.mkdir(parents=True, exist_ok=True)
                    with origen.extractfile(miembro) as fuente, ruta.open("xb") as salida:
                        if fuente is None:
                            raise ValueError("Contenido no disponible")
                        for bloque in iter(lambda: fuente.read(1024 * 1024), b""):
                            salida.write(bloque)
        except Exception:
            # Se conserva el destino parcial para análisis; nunca se borra información.
            raise
    return sum(m.isfile() for m in miembros)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="accion", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--origen", type=Path, required=True)
    b.add_argument("--archivo", type=Path, required=True)
    v = sub.add_parser("restore")
    v.add_argument("--archivo", type=Path, required=True)
    v.add_argument("--destino", type=Path, required=True)
    v.add_argument("--sha256", required=True)
    a = parser.parse_args()
    if a.accion == "backup":
        print("SHA256_ARCHIVO:", respaldo(a.origen, a.archivo))
    else:
        print("ARCHIVOS_RESTAURADOS:", restaurar(a.archivo, a.destino, a.sha256))


if __name__ == "__main__":
    main()
