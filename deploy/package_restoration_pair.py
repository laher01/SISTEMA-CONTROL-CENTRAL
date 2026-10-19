#!/usr/bin/env python3
"""Empaqueta un dump de PostgreSQL y una copia documental YA ESTABLES.

No detiene procesos ni consulta producción. El operador debe garantizar por
separado que ningún escritor modifica la BD o documentos durante la captura.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("document_archive_isolated.py")
SPEC = importlib.util.spec_from_file_location("document_archive_isolated", SCRIPT)
assert SPEC and SPEC.loader
ARCHIVO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARCHIVO)


def _copiar_com_hash(origen: Path, destino: Path) -> str:
    digest = hashlib.sha256()
    with origen.open("rb") as entrada, destino.open("xb") as salida:
        os.chmod(destino, 0o600)
        for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
            digest.update(bloque)
            salida.write(bloque)
    return digest.hexdigest()


def crear_par(dump: Path, documentos: Path, salida: Path, *, escritores_detenidos: bool) -> dict:
    if not escritores_detenidos:
        raise ValueError("Falta certificación del operador: escritores detenidos")
    if not dump.is_file() or dump.is_symlink():
        raise ValueError("El dump debe ser un archivo regular estable")
    if not documentos.is_dir() or documentos.is_symlink():
        raise ValueError("El origen documental debe ser directorio estable")
    if salida.exists() or salida.is_symlink() or not salida.parent.is_dir():
        raise ValueError("El destino debe ser nuevo y su padre debe existir")
    if salida.is_relative_to(documentos.resolve(strict=True)):
        raise ValueError("La salida no puede estar dentro del volumen documental")
    privada = Path(tempfile.mkdtemp(prefix=".rc1-pair-", dir=salida.parent))
    try:
        original = ARCHIVO.huella(dump)
        copiado = _copiar_com_hash(dump, privada / "postgres.dump")
        if original != copiado or ARCHIVO.huella(dump) != copiado:
            raise ValueError("Dump inestable durante copia")
        tar = privada / "documentos.tar"
        sha_tar = ARCHIVO.respaldo(documentos, tar)
        evidencia = {
            "schema": "factcentral-rc1-pair-v1",
            "postgres_sha256": copiado,
            "documentos_sha256": sha_tar,
            "consistencia": "declaracion_operador_no_verificada",
        }
        (privada / "evidencia.json").write_text(
            json.dumps(evidencia, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.chmod(privada / "evidencia.json", 0o600)
        ARCHIVO._publicar_sin_sobrescribir(privada, salida)
        return evidencia
    except Exception:
        shutil.rmtree(privada)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump-restaurable", type=Path, required=True)
    parser.add_argument("--documentos-estables", type=Path, required=True)
    parser.add_argument("--salida-nueva", type=Path, required=True)
    parser.add_argument(
        "--escritores-detenidos",
        action="store_true",
        help="Declaración manual: incluye API, trabajadores y otros escritores",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            crear_par(
                args.dump_restaurable,
                args.documentos_estables,
                args.salida_nueva,
                escritores_detenidos=args.escritores_detenidos,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
