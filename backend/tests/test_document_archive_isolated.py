"""Validación aislada de backup documental sin Docker ni datos de producción."""

import hashlib
import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "document_archive_isolated.py"
SPEC = importlib.util.spec_from_file_location("document_archive_isolated", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULO)


def test_respaldo_restaurado_se_corresponde_con_documentos(tmp_path: Path) -> None:
    origen = tmp_path / "source"
    archivo = origen / "tenant-01" / "ab" / ("a" * 64)
    archivo.parent.mkdir(parents=True)
    archivo.write_bytes(b"factura ficticia de prueba")
    copia = tmp_path / "backup.tar"
    sha_archivo = MODULO.respaldo(origen, copia)
    restaurado = tmp_path / "restored"
    assert MODULO.restaurar(copia, restaurado, sha_archivo) == 1
    assert (restaurado / archivo.relative_to(origen)).read_bytes() == archivo.read_bytes()
    assert not (origen / "otro").exists()


def test_restaura_solo_en_directorio_inexistente(tmp_path: Path) -> None:
    origen = tmp_path / "source"
    origen.mkdir()
    copia = tmp_path / "backup.tar"
    digest = MODULO.respaldo(origen, copia)
    with pytest.raises(ValueError, match="ya existe"):
        MODULO.restaurar(copia, origen, digest)


def test_rechaza_respaldo_modificado(tmp_path: Path) -> None:
    origen = tmp_path / "source"
    origen.mkdir()
    copia = tmp_path / "backup.tar"
    digest = MODULO.respaldo(origen, copia)
    with copia.open("ab") as destino:
        destino.write(b"modificado")
    with pytest.raises(ValueError, match="huella"):
        MODULO.restaurar(copia, tmp_path / "restored", digest)


def test_rechaza_traversal_en_archivo(tmp_path: Path) -> None:
    copia = tmp_path / "unsafe.tar"
    with tarfile.open(copia, "w") as archivo:
        contenido = b"contenido"
        entrada = tarfile.TarInfo("../fuera")
        entrada.size = len(contenido)
        archivo.addfile(entrada, io.BytesIO(contenido))
    digest = hashlib.sha256(copia.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="insegura"):
        MODULO.restaurar(copia, tmp_path / "restored", digest)
    assert not (tmp_path / "fuera").exists()


def test_rechaza_symlink_del_origen(tmp_path: Path) -> None:
    origen = tmp_path / "source"
    origen.mkdir()
    (origen / "link").symlink_to(tmp_path / "externo")
    with pytest.raises(ValueError, match="simbólicos"):
        MODULO.respaldo(origen, tmp_path / "backup.tar")
