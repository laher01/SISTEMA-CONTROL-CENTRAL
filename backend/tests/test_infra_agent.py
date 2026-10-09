import hashlib
import io
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

from app.infra_agent import (
    Agente,
    empaquetar_backup,
    extraer_backup,
    imagen_valida,
    restaurar_aislado,
)


def bundle_prueba(tmp_path: Path, nombre: str = "tenant/documento.xml") -> Path:
    dump = tmp_path / "database.dump"
    dump.write_bytes(b"dump de prueba")
    documentos = tmp_path / "documentos.tar.gz"
    with tarfile.open(documentos, "w:gz") as tar:
        dato = b"documento original"
        info = tarfile.TarInfo(nombre)
        info.size = len(dato)
        tar.addfile(info, io.BytesIO(dato))
    bundle = tmp_path / "backup.tar"
    empaquetar_backup(dump, documentos, bundle)
    return bundle


def test_agente_rechaza_imagenes_no_inmutables_y_shell() -> None:
    for imagen in ("latest", "ghcr.io/example/app:latest", "$(touch /tmp/pwn)", "--privileged"):
        with pytest.raises(ValueError):
            imagen_valida(imagen)
    imagen = "ghcr.io/laher01/backend@sha256:" + "a" * 64
    assert imagen_valida(imagen) == imagen


def test_hash_incorrecto_impide_restauracion_antes_de_docker(tmp_path: Path) -> None:
    archivo = tmp_path / "backup.age"
    archivo.write_bytes(b"contenido distinto")
    with pytest.raises(ValueError, match="hash"):
        restaurar_aislado(archivo, tmp_path / "key", "a" * 64)


def test_restauracion_solo_en_contenedor_temporal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archivo = tmp_path / "backup.age"
    archivo.write_bytes(b"cifrado de prueba")
    llamadas: list[list[str]] = []
    bundle = bundle_prueba(tmp_path)

    def ejecutar(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        llamadas.append(args)
        if args[0] == "age":
            shutil.copyfile(bundle, Path(args[args.index("--output") + 1]))
        return subprocess.CompletedProcess(args, 0, stdout=b"")

    monkeypatch.setattr(subprocess, "run", ejecutar)
    restaurar_aislado(
        archivo, tmp_path / "private-key", hashlib.sha256(archivo.read_bytes()).hexdigest()
    )
    arranque = next(c for c in llamadas if c[:2] == ["docker", "run"])
    contenedor = arranque[arranque.index("--name") + 1]
    assert contenedor.startswith("factcentral-restore-")
    assert arranque[arranque.index("--network") + 1] == "none"
    restauracion = next(c for c in llamadas if "pg_restore" in c)
    assert contenedor in restauracion
    assert "restore_check" in restauracion
    assert llamadas[-1] == ["docker", "rm", "--force", "--volumes", contenedor]
    assert all("fact-central-staging" not in c for c in llamadas)


def test_bundle_recupera_documentos_y_rechaza_rutas_inseguras(tmp_path: Path) -> None:
    bundle = bundle_prueba(tmp_path)
    destino = tmp_path / "verificacion"
    destino.mkdir()
    dump = extraer_backup(bundle, destino)
    assert dump.read_bytes() == b"dump de prueba"
    assert (destino / "documentos/tenant/documento.xml").read_bytes() == b"documento original"
    inseguro = tmp_path / "inseguro"
    inseguro.mkdir()
    bundle = bundle_prueba(inseguro, "../escape.xml")
    otro_destino = tmp_path / "otro-destino"
    otro_destino.mkdir()
    with pytest.raises(ValueError, match="Ruta insegura"):
        extraer_backup(bundle, otro_destino)
    assert not (tmp_path / "escape.xml").exists()


def test_configuracion_impide_reutilizar_compose_productivo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    valores = {
        "FC_INFRA_AGENT_NODO_ID": "00000000-0000-0000-0000-000000000001",
        "FC_INFRA_AGENT_TOKEN": "x" * 64,
        "FC_INFRA_AGENT_BASE_URL": "https://central.example",
        "FC_INFRA_AGENT_STATE_DIR": str(tmp_path / "state"),
        "FC_INFRA_AGENT_COMPOSE": str(tmp_path / "docker-compose.production.yml"),
        "FC_INFRA_AGENT_ENV_FILE": str(tmp_path / ".env.production"),
    }
    for nombre, valor in valores.items():
        monkeypatch.setenv(nombre, valor)
    with pytest.raises(ValueError, match="staging aislado"):
        Agente()
    monkeypatch.setenv("FC_INFRA_AGENT_COMPOSE", str(tmp_path / "docker-compose.agent-staging.yml"))
    monkeypatch.setenv("FC_INFRA_AGENT_ENV_FILE", str(tmp_path / ".env.agent-staging"))
    monkeypatch.setenv("FC_INFRA_AGENT_PROJECT", "fact-central-staging")
    with pytest.raises(ValueError, match="proyecto Docker aislado"):
        Agente()
