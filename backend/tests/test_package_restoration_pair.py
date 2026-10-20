"""Pruebas de empaquetado RC1 con dump ficticio y documentos aislados."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "package_restoration_pair.py"
SPEC = importlib.util.spec_from_file_location("package_restoration_pair", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_paquete_contiene_dos_resguardos_con_hash(tmp_path: Path) -> None:
    dump = tmp_path / "ficticio.dump"
    dump.write_bytes(b"dump de prueba, no PostgreSQL real")
    documentos = tmp_path / "docs"
    documentos.mkdir()
    (documentos / "archivo").write_bytes(b"ejemplo")
    salida = tmp_path / "paquete"
    evidencia = MOD.crear_par(dump, documentos, salida, escritores_detenidos=True)
    assert evidencia["postgres_sha256"] == hashlib.sha256(dump.read_bytes()).hexdigest()
    assert evidencia["documentos_sha256"] == MOD.ARCHIVO.huella(salida / "documentos.tar")
    assert (salida / "postgres.dump").read_bytes() == dump.read_bytes()
    assert json.loads((salida / "evidencia.json").read_text()) == evidencia


def test_exige_detener_escritores(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escritores"):
        MOD.crear_par(
            tmp_path / "ausente",
            tmp_path / "docs",
            tmp_path / "salida",
            escritores_detenidos=False,
        )


def test_no_sobrescribe_destino(tmp_path: Path) -> None:
    dump = tmp_path / "dump"
    dump.write_bytes(b"datos")
    documentos = tmp_path / "docs"
    documentos.mkdir()
    salida = tmp_path / "paquete"
    salida.mkdir()
    with pytest.raises(ValueError, match="nuevo"):
        MOD.crear_par(dump, documentos, salida, escritores_detenidos=True)


def test_rechaza_salida_dentro_del_volumen(tmp_path: Path) -> None:
    dump = tmp_path / "dump"
    dump.write_bytes(b"datos")
    documentos = tmp_path / "docs"
    documentos.mkdir()
    with pytest.raises(ValueError, match="dentro"):
        MOD.crear_par(dump, documentos, documentos / "salida", escritores_detenidos=True)
