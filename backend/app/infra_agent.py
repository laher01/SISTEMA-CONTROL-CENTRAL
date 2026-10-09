"""Agente Linux con operaciones fijas; nunca interpreta shell recibido por API."""

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path, PurePosixPath
from typing import IO, cast
from urllib.parse import urlsplit

Json = dict[str, object]


def empaquetar_backup(dump: Path, documentos: Path, destino: Path) -> None:
    hashes: dict[str, str] = {}
    for nombre, archivo in (("database.dump", dump), ("documentos.tar.gz", documentos)):
        with archivo.open("rb") as entrada:
            hashes[nombre] = hashlib.file_digest(entrada, "sha256").hexdigest()
    manifest = destino.parent / "manifest.json"
    manifest.write_text(json.dumps({"formato": 1, "hashes": hashes}))
    with tarfile.open(destino, "w") as bundle:
        for nombre, archivo in (
            ("database.dump", dump),
            ("documentos.tar.gz", documentos),
            ("manifest.json", manifest),
        ):
            bundle.add(archivo, arcname=nombre)


def extraer_backup(bundle: Path, destino: Path) -> Path:
    permitidos = {"database.dump", "documentos.tar.gz", "manifest.json"}
    with tarfile.open(bundle, "r:") as archivo:
        miembros = archivo.getmembers()
        if (
            {m.name for m in miembros} != permitidos
            or len(miembros) != 3
            or any(not m.isfile() for m in miembros)
        ):
            raise ValueError("Formato de backup inválido")
        for miembro in miembros:
            entrada = archivo.extractfile(miembro)
            if entrada is None:
                raise ValueError("Archivo de backup inválido")
            with entrada, (destino / miembro.name).open("xb") as salida:
                shutil.copyfileobj(entrada, salida)
            os.chmod(destino / miembro.name, 0o600)
    manifest = json.loads((destino / "manifest.json").read_text())
    for nombre in ("database.dump", "documentos.tar.gz"):
        with (destino / nombre).open("rb") as entrada:
            if hashlib.file_digest(entrada, "sha256").hexdigest() != manifest["hashes"][nombre]:
                raise ValueError("Integridad interna del backup incorrecta")
    documentos = destino / "documentos"
    documentos.mkdir(mode=0o700)
    with tarfile.open(destino / "documentos.tar.gz", "r:gz") as archivo:
        for miembro in archivo:
            partes = PurePosixPath(miembro.name)
            if (
                partes.is_absolute()
                or ".." in partes.parts
                or not (miembro.isdir() or miembro.isfile())
            ):
                raise ValueError("Ruta insegura en respaldo documental")
            objetivo = documentos.joinpath(*partes.parts)
            if miembro.isdir():
                objetivo.mkdir(parents=True, exist_ok=True, mode=0o700)
            else:
                objetivo.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                entrada = archivo.extractfile(miembro)
                if entrada is None:
                    raise ValueError("Archivo documental inválido")
                with entrada, objetivo.open("xb") as salida:
                    shutil.copyfileobj(entrada, salida)
                os.chmod(objetivo, 0o600)
    return destino / "database.dump"


class SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


def api_json(url: str, token: str, datos: Json | None = None) -> Json:
    request = urllib.request.Request(
        url,
        data=json.dumps(datos).encode() if datos is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(SinRedirecciones())
    with opener.open(request, timeout=10) as response:
        cuerpo = response.read(65537)
        if len(cuerpo) > 65536:
            raise ValueError("Respuesta de agente demasiado grande")
        dato = json.loads(cuerpo)
        if not isinstance(dato, dict):
            raise ValueError("Respuesta de agente inválida")
        return cast(Json, dato)


def imagen_valida(valor: object) -> str:
    if not isinstance(valor, str) or not re.fullmatch(
        r"[a-z0-9./_-]+@sha256:[0-9a-f]{64}",
        valor,
    ):
        raise ValueError("Imagen no fijada por digest")
    return valor


class Agente:
    def __init__(self) -> None:
        self.nodo_id = str(uuid.UUID(os.environ["FC_INFRA_AGENT_NODO_ID"]))
        self.token = os.environ["FC_INFRA_AGENT_TOKEN"]
        self.base = os.environ["FC_INFRA_AGENT_BASE_URL"].rstrip("/")
        partes = urlsplit(self.base)
        if (
            partes.scheme != "https"
            or not partes.hostname
            or partes.username
            or partes.password
            or partes.query
            or partes.fragment
        ):
            raise ValueError("La API de administración debe usar HTTPS sin credenciales en URL")
        self.ruta = f"{self.base}/api/v1/infraestructura/agentes/{self.nodo_id}"
        self.directorio = Path(
            os.environ.get("FC_INFRA_AGENT_STATE_DIR", "/var/lib/factcentral-agent")
        )
        self.directorio.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.operaciones = os.environ.get("FC_INFRA_AGENT_OPERACIONES", "false").lower() == "true"
        self.entorno = os.environ.get("FC_INFRA_AGENT_ENTORNO", "staging")
        if self.entorno not in {"development", "staging", "canary"}:
            raise ValueError("Este agente todavía no autoriza operaciones productivas")
        self.compose_file = Path(os.environ["FC_INFRA_AGENT_COMPOSE"]).resolve()
        self.env_file = Path(os.environ["FC_INFRA_AGENT_ENV_FILE"]).resolve()
        if (
            self.compose_file.name != "docker-compose.agent-staging.yml"
            or self.env_file.name != ".env.agent-staging"
        ):
            raise ValueError("Se exige Compose y entorno específicos de staging aislado")
        self.proyecto = os.environ.get("FC_INFRA_AGENT_PROJECT", "fact-central-agent-staging")
        if not re.fullmatch(r"fact-central-agent-[a-z0-9-]+", self.proyecto):
            raise ValueError("Se exige un proyecto Docker aislado del despliegue Oracle existente")
        self.health_url = os.environ.get(
            "FC_INFRA_AGENT_HEALTH_URL", "http://127.0.0.1:18081/health"
        )
        salud = urlsplit(self.health_url)
        if salud.hostname not in {"127.0.0.1", "localhost", "::1"} or salud.scheme != "http":
            raise ValueError("El healthcheck de contenedor debe ser loopback HTTP")
        self.ultimo_cpu: tuple[int, int] | None = None

    def comando(
        self, args: list[str], *, env: dict[str, str] | None = None, tiempo: int = 30
    ) -> bytes:
        resultado = subprocess.run(
            args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=tiempo,
            env=env,
        )
        return resultado.stdout

    def compose(self) -> list[str]:
        return [
            "docker",
            "compose",
            "--project-name",
            self.proyecto,
            "--env-file",
            str(self.env_file),
            "-f",
            str(self.compose_file),
        ]

    def revision_local(self) -> str:
        codigo = (
            "from app.core.db import get_engine\nfrom sqlalchemy import text\n"
            "with get_engine().connect() as c:\n"
            " print(c.execute(text('SELECT version_num FROM alembic_version')).scalar_one())"
        )
        revision = (
            self.comando(
                [*self.compose(), "exec", "-T", "backend", "uv", "run", "python", "-c", codigo]
            )
            .decode()
            .strip()
        )
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", revision):
            raise ValueError("Revisión Alembic inválida")
        return revision

    def salud_backend(self) -> bool:
        try:
            with urllib.request.build_opener(SinRedirecciones()).open(
                self.health_url,
                timeout=5,
            ) as response:
                return bool(response.status == 200)
        except (OSError, urllib.error.URLError):
            return False

    def version_local(self) -> str | None:
        try:
            contenedor = self.comando([*self.compose(), "ps", "-q", "backend"]).decode().strip()
            if not re.fullmatch(r"[0-9a-f]{12,64}", contenedor):
                return None
            version = (
                self.comando(
                    [
                        "docker",
                        "inspect",
                        "--format",
                        '{{index .Config.Labels "org.opencontainers.image.version"}}',
                        contenedor,
                    ]
                )
                .decode()
                .strip()
            )
            return version if version and version != "<no value>" else None
        except (subprocess.SubprocessError, OSError):
            return None

    def metricas(self) -> Json:
        cpu = None
        ram = None
        total_ram = None
        proc = Path("/proc")
        if (proc / "stat").exists():
            campos = [int(v) for v in (proc / "stat").read_text().splitlines()[0].split()[1:9]]
            actual = (sum(campos), campos[3] + campos[4])
            if self.ultimo_cpu and actual[0] > self.ultimo_cpu[0]:
                cpu = round(
                    100 * (1 - (actual[1] - self.ultimo_cpu[1]) / (actual[0] - self.ultimo_cpu[0])),
                    2,
                )
            self.ultimo_cpu = actual
        if (proc / "meminfo").exists():
            memoria = {
                line.split(":")[0]: int(line.split()[1])
                for line in (proc / "meminfo").read_text().splitlines()
            }
            ram = round(100 * (1 - memoria["MemAvailable"] / memoria["MemTotal"]), 2)
            total_ram = memoria["MemTotal"] * 1024
        uso = shutil.disk_usage(self.directorio)
        migracion = None
        db = "FALLO"
        try:
            migracion = self.revision_local()
            db = "OK"
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
        return {
            "reporte_id": str(uuid.uuid4()),
            "cpu_porcentaje": cpu,
            "ram_porcentaje": ram,
            "disco_porcentaje": round(100 * uso.used / uso.total, 2),
            "servicios": {
                "backend": "OK" if self.salud_backend() else "FALLO",
                "postgresql": db,
                "redis": "NO_CONFIGURADO",
                "storage": "OK",
            },
            "version": self.version_local(),
            "migracion": migracion,
            "cpu_nucleos": os.cpu_count(),
            "ram_bytes": total_ram,
            "disco_bytes": uso.total,
        }

    def desplegar(self, parametros: Json) -> Json:
        backend = imagen_valida(parametros["backend"])
        frontend = imagen_valida(parametros["frontend"])
        if self.revision_local() != parametros["migracion_anterior"]:
            raise ValueError("La revisión real cambió antes de ejecutar")
        if self.version_local() != parametros["version_anterior"]:
            raise ValueError("La versión real cambió antes de ejecutar")
        env = {**os.environ, "FC_INFRA_BACKEND_IMAGE": backend, "FC_INFRA_FRONTEND_IMAGE": frontend}
        self.comando([*self.compose(), "pull", "backend", "frontend"], env=env, tiempo=600)
        self.comando([*self.compose(), "up", "-d", "--no-deps", "backend", "frontend"], env=env)
        for _ in range(30):
            if self.salud_backend():
                break
            time.sleep(2)
        revision = self.revision_local()
        imagenes_ok = True
        for servicio, imagen in (("backend", backend), ("frontend", frontend)):
            contenedor = (
                self.comando([*self.compose(), "ps", "-q", servicio], env=env).decode().strip()
            )
            if not re.fullmatch(r"[0-9a-f]{12,64}", contenedor):
                imagenes_ok = False
                continue
            instalado = (
                self.comando(
                    ["docker", "inspect", "--format", "{{.Config.Image}}", contenedor], env=env
                )
                .decode()
                .strip()
            )
            imagenes_ok = imagenes_ok and instalado == imagen
        correcto = self.salud_backend() and imagenes_ok and revision == parametros["migracion"]
        return {
            "estado": "EXITO" if correcto else "FALLO",
            "backend_ok": self.salud_backend(),
            "base_datos_ok": True,
            "imagen_verificada": imagenes_ok,
            "migracion": revision,
            "codigo_error": None if correcto else "HEALTHCHECK",
        }

    def backup(self, operacion_id: str) -> Json:
        destino = Path(os.environ["FC_INFRA_BACKUP_DIR"]).resolve()
        if not destino.is_mount():
            raise ValueError("El backup requiere un montaje separado configurado")
        receptor = os.environ["FC_INFRA_BACKUP_AGE_RECIPIENT"]
        if not re.fullmatch(r"age1[0-9a-z]{58}", receptor):
            raise ValueError("Se exige receptor público age válido")
        destino.mkdir(parents=True, exist_ok=True, mode=0o700)
        objeto = f"factcentral-{uuid.UUID(operacion_id)}.backup.tar.age"
        archivo = destino / objeto
        if archivo.exists():
            raise ValueError("El objeto de backup ya existe; revisar antes de reintentar")
        with tempfile.TemporaryDirectory(dir=self.directorio) as temporal:
            dump = Path(temporal) / "database.dump"
            documentos = Path(temporal) / "documentos.tar.gz"
            bundle = Path(temporal) / "backup.tar"
            try:
                self.comando([*self.compose(), "stop", "backend", "frontend"])
                with dump.open("xb") as salida:
                    os.chmod(dump, 0o600)
                    subprocess.run(
                        [
                            *self.compose(),
                            "exec",
                            "-T",
                            "db",
                            "sh",
                            "-c",
                            'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
                            "-Fc --no-owner --no-acl",
                        ],
                        check=True,
                        stdout=salida,
                        stderr=subprocess.DEVNULL,
                        timeout=600,
                    )
                with documentos.open("xb") as salida:
                    os.chmod(documentos, 0o600)
                    subprocess.run(
                        [
                            *self.compose(),
                            "run",
                            "--rm",
                            "--no-deps",
                            "--entrypoint",
                            "tar",
                            "backend",
                            "-C",
                            "/data/documentos",
                            "-czf",
                            "-",
                            ".",
                        ],
                        check=True,
                        stdout=salida,
                        stderr=subprocess.DEVNULL,
                        timeout=600,
                    )
            finally:
                self.comando([*self.compose(), "start", "backend", "frontend"])
            with dump.open("rb") as entrada:
                subprocess.run(
                    [*self.compose(), "exec", "-T", "db", "pg_restore", "--list"],
                    stdin=entrada,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=60,
                    check=True,
                )
            empaquetar_backup(dump, documentos, bundle)
            self.comando(
                ["age", "--recipient", receptor, "--output", str(archivo), str(bundle)], tiempo=600
            )
        os.chmod(archivo, 0o600)
        with archivo.open("rb") as entrada:
            sha = hashlib.file_digest(entrada, "sha256").hexdigest()
        return {
            "estado": "EXITO",
            "objeto": objeto,
            "sha256": sha,
            "bytes": archivo.stat().st_size,
            "dump_verificado": True,
        }

    def ciclo(self) -> None:
        identidad = api_json(f"{self.ruta}/identidad", self.token)
        if identidad.get("entorno") != self.entorno:
            raise ValueError("El entorno del nodo no coincide con el agente aislado")
        reporte_path = self.directorio / "reporte.json"
        if not reporte_path.exists():
            reporte_path.write_text(json.dumps(self.metricas()))
        reporte = cast(Json, json.loads(reporte_path.read_text()))
        api_json(f"{self.ruta}/reportes", self.token, reporte)
        reporte_path.unlink()
        if not self.operaciones:
            return
        pendiente = self.directorio / "resultado.json"
        if pendiente.exists():
            registro = cast(Json, json.loads(pendiente.read_text()))
            resultado = cast(Json, registro["resultado"])
            api_json(f"{self.ruta}/operaciones/{registro['id']}/resultado", self.token, resultado)
            pendiente.unlink()
            return
        # Un proceso muerto después de reclamar requiere intervención; nunca se reejecuta.
        en_curso = self.directorio / "en-curso.json"
        if en_curso.exists():
            raise ValueError("Hay operación sin resultado: verificar Docker antes de continuar")
        respuesta = api_json(f"{self.ruta}/reclamar", self.token, {})
        operacion = respuesta.get("operacion")
        if not isinstance(operacion, dict):
            return
        en_curso.write_text(json.dumps(operacion))
        os.chmod(en_curso, 0o600)
        parametros = cast(Json, operacion["parametros"])
        try:
            if operacion["tipo"] == "BACKUP":
                resultado = self.backup(str(operacion["id"]))
            elif operacion["tipo"] in {"DESPLIEGUE", "ROLLBACK_IMAGEN"}:
                resultado = self.desplegar(parametros)
            else:
                raise ValueError("Operación no autorizada")
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            resultado = {"estado": "FALLO", "codigo_error": "AGENTE"}
        resultado["lease"] = operacion["lease"]
        pendiente.write_text(json.dumps({"id": operacion["id"], "resultado": resultado}))
        os.chmod(pendiente, 0o600)
        en_curso.unlink()
        api_json(f"{self.ruta}/operaciones/{operacion['id']}/resultado", self.token, resultado)
        pendiente.unlink()


def restaurar_aislado(archivo: Path, identidad: Path, sha256: str) -> None:
    """Restaura exclusivamente en un contenedor temporal nuevo; jamás en el Compose existente."""
    with archivo.open("rb") as entrada:
        if hashlib.file_digest(entrada, "sha256").hexdigest() != sha256:
            raise ValueError("El hash del backup no coincide")
    contenedor = f"factcentral-restore-{uuid.uuid4().hex}"
    clave = secrets.token_urlsafe(32)
    creado = False
    try:
        with tempfile.TemporaryDirectory() as temporal:
            bundle = Path(temporal) / "restore.tar"
            subprocess.run(
                [
                    "age",
                    "--decrypt",
                    "--identity",
                    str(identidad),
                    "--output",
                    str(bundle),
                    str(archivo),
                ],
                check=True,
                timeout=600,
                stderr=subprocess.DEVNULL,
            )
            os.chmod(bundle, 0o600)
            dump = extraer_backup(bundle, Path(temporal))
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--detach",
                    "--rm",
                    "--name",
                    contenedor,
                    "--network",
                    "none",
                    "--label",
                    "factcentral.restore=isolated",
                    "-e",
                    "POSTGRES_DB=restore_check",
                    "-e",
                    "POSTGRES_USER=restore_check",
                    "-e",
                    "POSTGRES_PASSWORD",
                    "postgres:17-bookworm",
                ],
                env={**os.environ, "POSTGRES_PASSWORD": clave},
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
            )
            creado = True
            for _ in range(30):
                listo = subprocess.run(
                    ["docker", "exec", contenedor, "pg_isready", "-U", "restore_check"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=False,
                )
                if listo.returncode == 0:
                    break
                time.sleep(2)
            with dump.open("rb") as entrada:
                subprocess.run(
                    [
                        "docker",
                        "exec",
                        "-i",
                        contenedor,
                        "pg_restore",
                        "-U",
                        "restore_check",
                        "-d",
                        "restore_check",
                        "--exit-on-error",
                        "--no-owner",
                        "--no-acl",
                    ],
                    stdin=entrada,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=600,
                )
            subprocess.run(
                [
                    "docker",
                    "exec",
                    contenedor,
                    "psql",
                    "-U",
                    "restore_check",
                    "-d",
                    "restore_check",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    "SELECT version_num FROM alembic_version",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
    finally:
        if creado:
            subprocess.run(
                ["docker", "rm", "--force", "--volumes", contenedor],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--restore-isolated", type=Path)
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args()
    if os.name != "posix":
        raise SystemExit("El agente de operaciones requiere Linux")
    if args.restore_isolated:
        if not args.identity or not args.sha256:
            raise SystemExit("Se requiere identidad age y hash esperado")
        restaurar_aislado(args.restore_isolated, args.identity, args.sha256)
        print("Restauración aislada verificada; ningún contenedor existente fue modificado")
        return
    import fcntl

    agente = Agente()
    with (agente.directorio / "agent.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            try:
                agente.ciclo()
                print("Ciclo de agente completado", flush=True)
            except (OSError, ValueError, urllib.error.URLError):
                print("Ciclo fallido; se conserva estado para recuperación segura", flush=True)
            if args.once:
                break
            time.sleep(60)


if __name__ == "__main__":
    main()
