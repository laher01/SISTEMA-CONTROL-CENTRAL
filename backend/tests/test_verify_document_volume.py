"""Pruebas aisladas del verificador documental del preflight."""

import hashlib
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "verify_document_volume.py"
SPEC = importlib.util.spec_from_file_location("verify_document_volume", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULO)


def test_archivo_correcto_del_tenant(tmp_path: Path) -> None:
    tenant = str(uuid4())
    contenido = b"documento de prueba"
    sha = hashlib.sha256(contenido).hexdigest()
    relativa = f"{tenant}/{sha[:2]}/{sha}"
    archivo = tmp_path / relativa
    archivo.parent.mkdir(parents=True)
    archivo.write_bytes(contenido)
    assert MODULO.verificar(tmp_path, [[tenant, relativa, sha]]) == (1, 0)


@pytest.mark.parametrize("alteracion", ["ausente", "corrupto", "tenant", "traversal"])
def test_detecta_documento_invalido(tmp_path: Path, alteracion: str) -> None:
    tenant = str(uuid4())
    contenido = b"original"
    sha = hashlib.sha256(contenido).hexdigest()
    relativa = f"{tenant}/{sha[:2]}/{sha}"
    archivo = tmp_path / relativa
    archivo.parent.mkdir(parents=True)
    archivo.write_bytes(contenido)
    if alteracion == "ausente":
        archivo.unlink()
    elif alteracion == "corrupto":
        archivo.write_bytes(b"modificado")
    elif alteracion == "tenant":
        tenant = str(uuid4())
    elif alteracion == "traversal":
        relativa = f"{tenant}/../fuera"
    assert MODULO.verificar(tmp_path, [[tenant, relativa, sha]]) == (0, 1)


def test_rechaza_rutas_absolutas_o_filas_incompletas(tmp_path: Path) -> None:
    assert MODULO.verificar(tmp_path, [["tenant", "/etc/passwd", "0" * 64]]) == (0, 1)
    assert MODULO.verificar(tmp_path, [["incompleta"]]) == (0, 1)


def test_rechaza_symlink_fuera_del_volumen(tmp_path: Path) -> None:
    raiz = tmp_path / "documentos"
    raiz.mkdir()
    archivo = tmp_path / "externo"
    archivo.write_bytes(b"externo")
    sha = hashlib.sha256(b"externo").hexdigest()
    tenant = str(uuid4())
    (raiz / tenant).mkdir()
    (raiz / tenant / "enlace").symlink_to(archivo)
    assert MODULO.verificar(raiz, [[tenant, f"{tenant}/enlace", sha]]) == (0, 1)
