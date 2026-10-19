#!/usr/bin/env python3
"""Respaldo y restauración OFFLINE en destino nuevo; no es snapshot transaccional."""

import argparse
import hashlib
import os
import re
import shutil
import stat
import tarfile
import tempfile
from pathlib import Path

BLOQUE = 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}")


def huella(archivo: Path) -> str:
    digest = hashlib.sha256()
    with archivo.open("rb") as entrada:
        for bloque in iter(lambda: entrada.read(BLOQUE), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _limites(entradas: int, bytes_totales: int) -> None:
    if entradas < 1 or bytes_totales < 0:
        raise ValueError("Los límites deben ser positivos")


def respaldo(
    origen: Path,
    archivo: Path,
    max_entradas: int = 100000,
    max_bytes: int = 10 * 1024**3,
) -> str:
    _limites(max_entradas, max_bytes)
    origen = origen.resolve(strict=True)
    if not origen.is_dir():
        raise ValueError("El origen no es directorio")
    archivo = archivo.absolute()
    if archivo.exists() or archivo.is_relative_to(origen):
        raise ValueError("El respaldo debe ser nuevo y estar fuera del origen")
    entradas = 0
    total = 0
    with tempfile.NamedTemporaryFile(dir=archivo.parent, delete=False) as temporal:
        parcial = Path(temporal.name)
    try:
        with tarfile.open(parcial, "w") as salida:
            for ruta in sorted(origen.rglob("*")):
                info = ruta.lstat()
                if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                    raise ValueError("Enlaces simbólicos y archivos especiales no admitidos")
                entradas += 1
                total += info.st_size if stat.S_ISREG(info.st_mode) else 0
                if entradas > max_entradas or total > max_bytes:
                    raise ValueError("Límites de respaldo superados")
                salida.add(ruta, arcname=ruta.relative_to(origen).as_posix(), recursive=False)
        digest = huella(parcial)
        with archivo.open("xb") as destino, parcial.open("rb") as entrada:
            for bloque in iter(lambda: entrada.read(BLOQUE), b""):
                destino.write(bloque)
        return digest
    finally:
        parcial.unlink(missing_ok=True)


def _validar(miembros: list[tarfile.TarInfo], max_entradas: int, max_bytes: int) -> None:
    _limites(max_entradas, max_bytes)
    if len(miembros) > max_entradas:
        raise ValueError("Límite de entradas superado")
    vistos: dict[str, bool] = {}
    total = 0
    for miembro in miembros:
        nombre = miembro.name
        ruta = Path(nombre)
        if (
            not nombre
            or nombre.startswith("/")
            or "\\x00" in nombre
            or ruta.as_posix() != nombre.rstrip("/")
            or any(parte in {"..", "."} for parte in nombre.split("/"))
            or not (miembro.isfile() or miembro.isdir())
            or nombre.rstrip("/") in vistos
        ):
            raise ValueError("Entrada insegura en archivo")
        llave = nombre.rstrip("/")
        vistos[llave] = miembro.isdir()
        total += miembro.size if miembro.isfile() else 0
        if total > max_bytes:
            raise ValueError("Límite de bytes superado")
    for nombre in vistos:
        partes = Path(nombre).parts
        for i in range(1, len(partes)):
            padre = "/".join(partes[:i])
            if padre in vistos and not vistos[padre]:
                raise ValueError("Colisión archivo/directorio")


def restaurar(
    archivo: Path,
    destino: Path,
    sha256: str,
    max_entradas: int = 100000,
    max_bytes: int = 10 * 1024**3,
) -> int:
    if not archivo.is_file() or not SHA.fullmatch(sha256):
        raise ValueError("Respaldo o huella inválidos")
    if huella(archivo) != sha256:
        raise ValueError("La huella del respaldo no coincide")
    if destino.exists() or destino.is_symlink():
        raise ValueError("El directorio destino ya existe: no se sobrescribe")
    with tarfile.open(archivo, "r") as origen:
        miembros = origen.getmembers()
        _validar(miembros, max_entradas, max_bytes)
        directorio = destino.parent
        if not directorio.is_dir():
            raise ValueError("El padre del destino no existe")
        privada = Path(tempfile.mkdtemp(prefix=".restore-", dir=directorio))
        try:
            for miembro in miembros:
                ruta = privada / miembro.name
                if miembro.isdir():
                    ruta.mkdir(mode=0o700, parents=True, exist_ok=True)
                else:
                    ruta.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    fuente = origen.extractfile(miembro)
                    if fuente is None:
                        raise ValueError("Contenido no disponible")
                    with fuente, ruta.open("xb") as salida:
                        os.chmod(ruta, 0o600)
                        escritos = 0
                        for bloque in iter(lambda: fuente.read(BLOQUE), b""):
                            escritos += len(bloque)
                            if escritos > miembro.size:
                                raise ValueError("Tamaño incorrecto")
                            salida.write(bloque)
                        if escritos != miembro.size:
                            raise ValueError("Tamaño incorrecto")
            if destino.exists() or destino.is_symlink():
                raise ValueError("Destino creado durante restauración")
            privada.rename(destino)
        except Exception:
            shutil.rmtree(privada)
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
    for comando in (b, v):
        comando.add_argument("--max-entradas", type=int, default=100000)
        comando.add_argument("--max-bytes", type=int, default=10 * 1024**3)
    a = parser.parse_args()
    if a.accion == "backup":
        print("SHA256_ARCHIVO:", respaldo(a.origen, a.archivo, a.max_entradas, a.max_bytes))
    else:
        print(
            "ARCHIVOS_RESTAURADOS:",
            restaurar(a.archivo, a.destino, a.sha256, a.max_entradas, a.max_bytes),
        )


if __name__ == "__main__":
    main()
