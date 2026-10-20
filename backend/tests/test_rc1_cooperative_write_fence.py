"""Pruebas de candado cooperativo: escritor y captura no se solapan."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "rc1_cooperative_write_fence.py"
SPEC = importlib.util.spec_from_file_location("rc1_cooperative_write_fence", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_captura_bloquea_nuevo_escritor(tmp_path: Path) -> None:
    lock = tmp_path / "lock"
    documento = tmp_path / "documento"
    with MOD.candado(lock, exclusivo=True), pytest.raises(BlockingIOError):
        with MOD.candado(lock, exclusivo=False, no_bloquear=True):
            documento.write_bytes(b"indebido")
    MOD.escribir_fixture(lock, documento, b"permitido")
    assert documento.read_bytes() == b"permitido"


def test_escritor_impide_captura(tmp_path: Path) -> None:
    lock = tmp_path / "lock"
    with MOD.candado(lock, exclusivo=False), pytest.raises(BlockingIOError):
        with MOD.candado(lock, exclusivo=True, no_bloquear=True):
            pass


def test_rechaza_candado_simbolico(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.write_text("archivo")
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(ValueError, match="simbólico"), MOD.candado(link, exclusivo=True):
        pass
