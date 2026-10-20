"""Pruebas del control de estabilidad offline RC1."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "check_quiescence_offline.py"
SPEC = importlib.util.spec_from_file_location("check_quiescence_offline", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_acepta_copias_estables(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "f").write_bytes(b"documento")
    dump = tmp_path / "dump"
    dump.write_bytes(b"postgres-ficticio")
    assert MOD.verificar_estabilidad(docs, dump)


def test_detecta_cambio_entre_lecturas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    contenido = docs / "f"
    contenido.write_bytes(b"antes")
    dump = tmp_path / "dump"
    dump.write_bytes(b"fixture")

    def alterar(_: float) -> None:
        contenido.write_bytes(b"despues")

    monkeypatch.setattr(MOD.time, "sleep", alterar)
    assert not MOD.verificar_estabilidad(docs, dump, 0.01)


def test_rechaza_symlink_y_espera_invalida(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    dump = tmp_path / "dump"
    dump.write_bytes(b"fixture")
    (docs / "enlace").symlink_to(dump)
    with pytest.raises(ValueError, match="simbólico"):
        MOD.verificar_estabilidad(docs, dump)
    with pytest.raises(ValueError, match="Espera"):
        MOD.verificar_estabilidad(docs, dump, -1)
