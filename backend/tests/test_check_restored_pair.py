"""Pruebas offline del cotejo conjunto sin conexión a bases reales."""
import hashlib
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "check_restored_pair.py"
SPEC = importlib.util.spec_from_file_location("check_restored_pair", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_par_restaurado_coincide(tmp_path: Path) -> None:
    tenant = "tenant-ficticio"
    contenido = b"documento-test"
    digest = hashlib.sha256(contenido).hexdigest()
    documentos = tmp_path / "documentos"
    ruta = documentos / tenant / digest[:2] / digest
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(contenido)
    manifiesto = tmp_path / "manifest.tsv"
    manifiesto.write_text(
        f"{tenant}\t{tenant}/{digest[:2]}/{digest}\t{digest}\n", encoding="utf-8"
    )
    assert MOD.cotejar(manifiesto, documentos, 1) == (1, 0)
    assert MOD.cotejar(manifiesto, documentos, 2)[1] > 0
    ruta.write_bytes(b"alterado")
    assert MOD.cotejar(manifiesto, documentos, 1) == (0, 1)


def test_rechaza_manifiesto_con_ruta_fuera_tenant(tmp_path: Path) -> None:
    volumen = tmp_path / "volumen"
    volumen.mkdir()
    manifiesto = tmp_path / "manifest.tsv"
    manifiesto.write_text("a\t../b/documento\t" + "a" * 64 + "\n", encoding="utf-8")
    assert MOD.cotejar(manifiesto, volumen, 1) == (0, 1)
