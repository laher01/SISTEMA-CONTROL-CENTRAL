"""Prueba integral aislada: empaquetar copias ficticias, restaurar TAR y cotejar manifiesto.

No simula pg_restore ni certifica snapshots de producción.
"""

import hashlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "deploy"


def cargar(nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, BASE / f"{nombre}.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_par_ficticio_restaurado_y_cotejado(tmp_path: Path) -> None:
    empaquetar = cargar("package_restoration_pair")
    archivos = cargar("document_archive_isolated")
    cotejo = cargar("check_restored_pair")
    dump = tmp_path / "db.dump"
    dump.write_bytes(b"solo fixture; no es dump de PostgreSQL")
    tenant = "tenant-demo"
    contenido = b"documento de ejemplo"
    sha = hashlib.sha256(contenido).hexdigest()
    original = tmp_path / "volumen"
    ruta = original / tenant / sha[:2] / sha
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(contenido)
    pareja = tmp_path / "pareja"
    evidencia = empaquetar.crear_par(dump, original, pareja, escritores_detenidos=True)
    recuperado = tmp_path / "volumen-recuperado"
    assert (
        archivos.restaurar(pareja / "documentos.tar", recuperado, evidencia["documentos_sha256"])
        == 1
    )
    manifiesto = tmp_path / "restored-db-manifest.tsv"
    manifiesto.write_text(f"{tenant}\t{tenant}/{sha[:2]}/{sha}\t{sha}\n", encoding="utf-8")
    assert cotejo.cotejar(manifiesto, recuperado, 1) == (1, 0)
    assert (pareja / "postgres.dump").read_bytes() == dump.read_bytes()
    (recuperado / tenant / sha[:2] / sha).write_bytes(b"alterado")
    assert cotejo.cotejar(manifiesto, recuperado, 1) == (0, 1)
