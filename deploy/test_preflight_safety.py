"""Pruebas de comportamiento de preflight con un repositorio Git sintético."""
from pathlib import Path
import os
import subprocess
import tempfile


SOURCE = Path(__file__).with_name("preflight-secretaria.sh").read_text()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None, check: bool = True):
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=check)


def test_preflight() -> None:
    with tempfile.TemporaryDirectory() as base:
        root = Path(base)
        remote, server, author = (root / name for name in ("remote.git", "server", "author"))
        run("git", "init", "--bare", "-b", "main", str(remote), cwd=root)
        run("git", "clone", str(remote), str(server), cwd=root)
        run("git", "config", "user.name", "CI", cwd=server)
        run("git", "config", "user.email", "ci@example.test", cwd=server)
        (server / "tracked.txt").write_text("original")
        run("git", "add", ".", cwd=server)
        run("git", "commit", "-m", "Inicial", cwd=server)
        run("git", "push", "origin", "main", cwd=server)
        run("git", "clone", str(remote), str(author), cwd=root)
        run("git", "config", "user.name", "CI", cwd=author)
        run("git", "config", "user.email", "ci@example.test", cwd=author)
        (author / "incoming.txt").write_text("versionado futuro")
        run("git", "add", ".", cwd=author)
        run("git", "commit", "-m", "Siguiente", cwd=author)
        run("git", "push", "origin", "main", cwd=author)
        target = run("git", "rev-parse", "HEAD", cwd=author).stdout.strip()

        (server / "deploy").mkdir()
        (server / "deploy" / ".env.production").write_text("test=1")
        (server / "deploy" / "local-backups").mkdir()
        (server / "deploy" / "local-backups" / "backup.dump").write_bytes(b"BACKUP")
        (server / "deploy" / "private").mkdir()
        (server / "deploy" / "private" / "secreto.conf").write_text("privado")
        (server / "actualizar-fact-central.sh").write_text("# preservado")
        fakebin = root / "bin"
        fakebin.mkdir()
        for name in ("curl", "docker"):
            path = fakebin / name
            if name == "docker":
                path.write_text('#!/bin/sh\ncase "$*" in *"pg_database_size(current_database())"*) echo 1024;; esac\nexit 0\n')
            else:
                path.write_text("#!/bin/sh\nexit 0\n")
            path.chmod(0o755)
        env = dict(os.environ, EXPECTED_COMMIT=target, PATH=str(fakebin) + os.pathsep + os.environ["PATH"])

        def preflight():
            return subprocess.run(
                ["bash", "-s"], input=SOURCE, text=True, capture_output=True, cwd=server, env=env
            )

        first = preflight()
        assert first.returncode == 0, "Debe preservar archivos locales sin colisión: " + first.stdout + first.stderr
        assert (server / "deploy" / "private" / "secreto.conf").read_text() == "privado"
        assert (server / "deploy" / "local-backups" / "backup.dump").read_bytes() == b"BACKUP"

        (server / "tracked.txt").write_text("modificado localmente")
        assert preflight().returncode != 0, "Debe bloquear modificaciones versionadas"
        (server / "tracked.txt").write_text("original")

        (server / "incoming.txt").write_text("colisión local")
        result = preflight()
        assert result.returncode != 0, "Debe bloquear colisiones con el commit entrante"
        assert "Conflicto" in result.stdout, result.stdout + result.stderr
        assert (server / "incoming.txt").read_text() == "colisión local"


if __name__ == "__main__":
    test_preflight()
    print("Preflight: 3 pruebas de comportamiento aprobadas")
