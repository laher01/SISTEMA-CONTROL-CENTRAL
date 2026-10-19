#!/usr/bin/env python3
"""Cotejo offline de manifiesto de BD restaurada y volumen documental restaurado.

No accede a PostgreSQL ni a Docker. El manifiesto debe exportarse por un operador
desde una BASE RESTAURADA, nunca desde producción.
"""
import argparse
import csv
import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("verify_document_volume.py")
SPEC = importlib.util.spec_from_file_location("verify_document_volume", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def cotejar(manifiesto: Path, volumen: Path, esperados: int) -> tuple[int, int]:
    if esperados < 0:
        raise ValueError("Recuento negativo")
    with manifiesto.open("r", newline="", encoding="utf-8") as entrada:
        filas = list(csv.reader(entrada, delimiter="\t"))
    return MOD.verificar(volumen, filas, esperados)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifiesto", required=True, type=Path)
    p.add_argument("--documentos", required=True, type=Path)
    p.add_argument("--esperados", required=True, type=int)
    a = p.parse_args()
    try:
        correctos, fallos = cotejar(a.manifiesto, a.documentos, a.esperados)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"VERIFICADOS={correctos} ERRORES={fallos} ESPERADOS={a.esperados}")
    return 0 if fallos == 0 and correctos == a.esperados else 1


if __name__ == "__main__":
    raise SystemExit(main())
