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


def test_rechaza_cuotas_antes_de_crear_destino(tmp_path: Path) -> None:
    origen = tmp_path / "source"
    origen.mkdir()
    (origen / "a").write_bytes(b"123456")
    copia = tmp_path / "backup.tar"
    digest = MODULO.respaldo(origen, copia)
    with pytest.raises(ValueError, match="bytes"):
        MODULO.restaurar(copia, tmp_path / "restored", digest, max_bytes=3)
    assert not (tmp_path / "restored").exists()
    with pytest.raises(ValueError, match="límites"):
        MODULO.restaurar(copia, tmp_path / "restored", digest, max_entradas=0)


def test_rechaza_colision_archivo_directorio(tmp_path: Path) -> None:
    copia = tmp_path / "collision.tar"
    with tarfile.open(copia, "w") as archivo:
        for nombre in ("a", "a/b"):
            datos = b"x"
            entrada = tarfile.TarInfo(nombre)
            entrada.size = len(datos)
            archivo.addfile(entrada, io.BytesIO(datos))
    digest = hashlib.sha256(copia.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Colisión"):
        MODULO.restaurar(copia, tmp_path / "restored", digest)
    assert not (tmp_path / "restored").exists()


def test_rechaza_nombre_duplicado(tmp_path: Path) -> None:
    copia = tmp_path / "duplicate.tar"
    with tarfile.open(copia, "w") as archivo:
        for _ in range(2):
            entrada = tarfile.TarInfo("duplicado")
            entrada.size = 1
            archivo.addfile(entrada, io.BytesIO(b"x"))
    digest = hashlib.sha256(copia.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="insegura"):
        MODULO.restaurar(copia, tmp_path / "restored", digest)


def test_asegura_permisos_privados(tmp_path: Path) -> None:
    origen = tmp_path / "source"
    origen.mkdir()
    (origen / "archivo").write_bytes(b"privado")
    copia = tmp_path / "backup.tar"
    digest = MODULO.respaldo(origen, copia)
    destino = tmp_path / "restored"
    MODULO.restaurar(copia, destino, digest)
    assert destino.stat().st_mode & 0o077 == 0
    assert (destino / "archivo").stat().st_mode & 0o077 == 0


def test_destino_concurrente_no_se_reemplaza(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    origen = tmp_path / "source"
    origen.mkdir()
    (origen / "archivo").write_bytes(b"origen")
    copia = tmp_path / "backup.tar"
    digest = MODULO.respaldo(origen, copia)
    destino = tmp_path / "restored"
    original = MODULO._publicar_sin_sobrescribir

    def competir(privada: Path, objetivo: Path) -> None:
        objetivo.mkdir()
        (objetivo / "testigo").write_bytes(b"intacto")
        original(privada, objetivo)

    monkeypatch.setattr(MODULO, "_publicar_sin_sobrescribir", competir)
    with pytest.raises(OSError):
        MODULO.restaurar(copia, destino, digest)
    assert (destino / "testigo").read_bytes() == b"intacto"


def test_rechaza_archivo_tar_excesivo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    origen = tmp_path / "source"
    origen.mkdir()
    copia = tmp_path / "backup.tar"
    digest = MODULO.respaldo(origen, copia)
    monkeypatch.setattr(MODULO, "MAX_ARCHIVO", 50)
    with pytest.raises(ValueError, match="físico"):
        MODULO.restaurar(copia, tmp_path / "restored", digest)


def test_falta_espacio_no_publica(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil
    from collections import namedtuple

    origen = tmp_path / "source"
    origen.mkdir()
    (origen / "archivo").write_bytes(b"contenido")
    copia = tmp_path / "backup.tar"
    digest = MODULO.respaldo(origen, copia)
    uso = namedtuple("Uso", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda _: uso(100, 100, 0))
    with pytest.raises(OSError, match="Espacio"):
        MODULO.restaurar(copia, tmp_path / "restored", digest)
    assert not (tmp_path / "restored").exists()


def test_tar_truncado_no_publica(tmp_path: Path) -> None:
    origen = tmp_path / "source"
    origen.mkdir()
    (origen / "archivo").write_bytes(b"contenido")
    copia = tmp_path / "backup.tar"
    MODULO.respaldo(origen, copia)
    copia.write_bytes(copia.read_bytes()[:300])
    digest_truncado = hashlib.sha256(copia.read_bytes()).hexdigest()
    destino = tmp_path / "restored"
    with pytest.raises((tarfile.TarError, EOFError, OSError, ValueError)):
        MODULO.restaurar(copia, destino, digest_truncado)
    assert not destino.exists()
