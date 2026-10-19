#!/usr/bin/env python3
"""Compara un manifiesto de documentos de una BD restaurada con un volumen local.

Entrada TSV por stdin: tenant_id, ruta_storage, sha256. No modifica archivos.
No certifica que exista un backup del volumen: valida únicamente los archivos
visibles desde el montaje entregado.
"""

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

DIGEST = re.compile(r"[0-9a-f]{64}")


def verificar(base: Path, filas: list[list[str]]) -> tuple[int, int]:
    """Devuelve (verificados, errores). Rechaza rutas fuera del volumen."""
    raiz = base.resolve(strict=True)
    if not raiz.is_dir():
        raise ValueError("El origen documental no es un directorio")
    verificados = 0
    errores = 0
    for fila in filas:
        if len(fila) != 3:
            errores += 1
            continue
        tenant, ruta, sha = fila
        relativa = Path(ruta)
        if (
            not tenant
            or not DIGEST.fullmatch(sha)
            or relativa.is_absolute()
            or ".." in relativa.parts
            or not relativa.parts
            or relativa.parts[0] != tenant
        ):
            errores += 1
            continue
        archivo = (raiz / relativa).resolve()
        if not archivo.is_relative_to(raiz) or not archivo.is_file():
            errores += 1
            continue
        digest = hashlib.sha256()
        with archivo.open("rb") as entrada:
            for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
                digest.update(bloque)
        if digest.hexdigest() != sha:
            errores += 1
            continue
        verificados += 1
    return verificados, errores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documentos", type=Path, required=True)
    args = parser.parse_args()
    filas = list(csv.reader(sys.stdin, delimiter="\t"))
    try:
        correctos, fallos = verificar(args.documentos, filas)
    except (OSError, ValueError) as exc:
        print(f"ERROR: volumen documental inaccesible: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"DOCUMENTOS_VERIFICADOS: {correctos}")
    print(f"DOCUMENTOS_CON_ERROR: {fallos}")
    if fallos:
        print("ERROR: archivos documentales ausentes, corruptos o fuera del tenant", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
