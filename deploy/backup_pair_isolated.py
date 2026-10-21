#!/usr/bin/env python3
"""Prototipo offline: pareja PostgreSQL/documentos y verificación en BD restaurada.

SOLO localhost y bases de laboratorio. El operador debe detener TODAS las escrituras
antes de capturar el par; esta herramienta no puede demostrar esa condición.
No incorpora cifrado ni conectividad a VPS o Docker de producción.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from document_archive_isolated import respaldo, restaurar, huella
from verify_document_volume import verificar

LAB_SOURCE = re.compile(r"factcentral_fixture_[a-z0-9_]+\Z")
LAB_RESTORE = re.compile(r"factcentral_recovery_[a-z0-9_]+\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
QUERY = (
    "COPY (SELECT tenant_id::text, ruta_storage, sha256 "
    "FROM public.documentos ORDER BY tenant_id, ruta_storage) "
    "TO STDOUT WITH (FORMAT csv, DELIMITER E'\\t', HEADER false)"
)
COUNT = "SELECT count(*) FROM public.documentos"
EMPTY = (
    "SELECT count(*) FROM information_schema.tables "
    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
)


def ejecutar(argumentos: list[str], *, entrada: bytes | None = None) -> bytes:
    resultado = subprocess.run(
        argumentos, input=entrada, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=600,
    )
    if resultado.returncode:
        # No propagar mensajes de PostgreSQL ni rutas/credenciales en stdout.
        raise RuntimeError(f"Fallo en comando PostgreSQL (código {resultado.returncode})")
    return resultado.stdout


def conexion(db: str, usuario: str, restaurada: bool = False) -> list[str]:
    patron = LAB_RESTORE if restaurada else LAB_SOURCE
    if not patron.fullmatch(db):
        raise ValueError("Solo nombres de BD local de laboratorio permitidos")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", usuario):
        raise ValueError("Usuario PostgreSQL inválido")
    return ["-h", "127.0.0.1", "-U", usuario, "-d", db]


def _publicar_json(ruta: Path, datos: dict) -> None:
    with ruta.open("x", encoding="utf-8") as f:
        os.chmod(ruta, 0o600)
        json.dump(datos, f, sort_keys=True, indent=2)
        f.write("\n")


def capturar(db: str, usuario: str, documentos: Path, destino: Path) -> dict:
    """Captura una pareja SOLO sobre datos previamente quiescentes."""
    argumentos = conexion(db, usuario)
    if destino.exists():
        raise ValueError("El directorio de salida ya existe")
    if documentos.is_symlink() or not documentos.is_dir():
        raise ValueError("La instantánea documental debe ser un directorio real")
    destino.mkdir(mode=0o700, parents=False)
    dump = destino / "postgres.dump"
    tar = destino / "documentos.tar"
    try:
        # pg_dump es transaccional para PG, NO para el directorio documental.
        with tempfile.NamedTemporaryFile(dir=destino, delete=False) as temporal:
            temporal_path = Path(temporal.name)
        try:
            os.chmod(temporal_path, 0o600)
            ejecutar(["pg_dump", *argumentos, "-Fc", "-f", str(temporal_path)])
            if not temporal_path.stat().st_size:
                raise ValueError("Dump PostgreSQL vacío")
            temporal_path.rename(dump)
        finally:
            temporal_path.unlink(missing_ok=True)
        sha_tar = respaldo(documentos, tar)
        datos = {
            "formato": 1,
            "id": str(uuid.uuid4()),
            "consistencia": "QUIESCENCIA_EXTERNA_NO_VERIFICADA",
            "postgres": {"archivo": dump.name, "sha256": huella(dump), "bytes": dump.stat().st_size},
            "documentos": {"archivo": tar.name, "sha256": sha_tar, "bytes": tar.stat().st_size},
        }
        _publicar_json(destino / "pareja.json", datos)
        return datos
    except Exception:
        # Si falla, mantener evidencia de archivos incompletos para revisión manual.
        raise


def _leer_par(pareja: Path) -> tuple[Path, Path, str]:
    if pareja.is_symlink() or not pareja.is_file():
        raise ValueError("Metadatos no disponibles")
    datos = json.loads(pareja.read_text(encoding="utf-8"))
    if datos.get("formato") != 1 or datos.get("consistencia") != "QUIESCENCIA_EXTERNA_NO_VERIFICADA":
        raise ValueError("Formato de pareja desconocido")
    archivos = []
    for clave, nombre in (("postgres", "postgres.dump"), ("documentos", "documentos.tar")):
        item = datos[clave]
        if item["archivo"] != nombre or not HASH.fullmatch(item["sha256"]):
            raise ValueError("Metadatos del par inválidos")
        ruta = pareja.parent / nombre
        if ruta.is_symlink() or not ruta.is_file() or ruta.stat().st_size != item["bytes"]:
            raise ValueError("Falta un archivo o tamaño incorrecto")
        if huella(ruta) != item["sha256"]:
            raise ValueError("Huella incorrecta")
        archivos.append(ruta)
    return archivos[0], archivos[1], datos["documentos"]["sha256"]


def manifest_desde_restaurada(db: str, usuario: str) -> list[list[str]]:
    parametros = conexion(db, usuario, restaurada=True)
    total = ejecutar(["psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
                      *parametros, "-c", COUNT]).decode("ascii").strip()
    if not total.isdigit():
        raise ValueError("Recuento restaurado inválido")
    texto = ejecutar(["psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
                      *parametros, "-c", QUERY]).decode("utf-8")
    filas = list(csv.reader(io.StringIO(texto), delimiter="\t"))
    if len(filas) != int(total):
        raise ValueError("Recuento y manifiesto restaurados no coinciden")
    # La ruta escrita por AlmacenLocal es UUID / prefijo / sha256. Este
    # contrato evita ambigüedad TSV y colisiones de normalización.
    for fila in filas:
        if len(fila) != 3:
            raise ValueError("Fila documental no representable")
        tenant, ruta, sha = fila
        try:
            if str(uuid.UUID(tenant)) != tenant or not HASH.fullmatch(sha):
                raise ValueError("Identidad documental inválida")
        except (ValueError, AttributeError) as exc:
            raise ValueError("Identidad documental inválida") from exc
        if ruta != f"{tenant}/{sha[:2]}/{sha}":
            raise ValueError("Ruta documental no canónica")
    return filas


def probar(pareja: Path, db_restaurada: str, usuario: str, raiz: Path) -> int:
    """Restaura TAR y dump en laboratorio y coteja hashes; NO limpia ninguna BD."""
    parametros = conexion(db_restaurada, usuario, restaurada=True)
    dump, tar, sha_tar = _leer_par(pareja)
    if raiz.exists() or raiz.is_symlink() or not raiz.parent.is_dir():
        raise ValueError("Destino de documentos debe ser nuevo")
    tablas = ejecutar(["psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
                       *parametros, "-c", EMPTY]).decode("ascii").strip()
    if tablas != "0":
        raise ValueError("La BD de recuperación debe estar vacía")
    # No --clean, no --create, no superuser, no operación sobre producción.
    ejecutar(["pg_restore", "--no-owner", "--no-acl", "--exit-on-error",
             *parametros, str(dump)])
    restaurar(tar, raiz, sha_tar)
    filas = manifest_desde_restaurada(db_restaurada, usuario)
    validos, fallos = verificar(raiz, filas, esperados=len(filas))
    if fallos or validos != len(filas):
        raise ValueError(f"Falló verificación documental: {fallos} archivos")
    return validos


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="accion", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--db-fixture", required=True)
    b.add_argument("--usuario", required=True)
    b.add_argument("--documentos-offline", type=Path, required=True)
    b.add_argument("--destino-nuevo", type=Path, required=True)
    b.add_argument("--escrituras-detenidas", action="store_true")
    v = sub.add_parser("verify")
    v.add_argument("--pareja", type=Path, required=True)
    v.add_argument("--db-restaurada-vacia", required=True)
    v.add_argument("--usuario", required=True)
    v.add_argument("--documentos-destino-nuevo", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.accion == "backup":
            if not a.escrituras_detenidas:
                raise ValueError("Debe afirmar quiescencia externa; no es comprobable")
            capturar(a.db_fixture, a.usuario, a.documentos_offline, a.destino_nuevo)
            print("PAR_CAPTURADO_LABORATORIO: sí; consistencia externa NO verificada")
        else:
            numero = probar(a.pareja, a.db_restaurada_vacia, a.usuario,
                            a.documentos_destino_nuevo)
            print(f"DOCUMENTOS_RESTAURADOS_Y_VERIFICADOS: {numero}")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {type(exc).__name__}: operación de laboratorio fallida")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
