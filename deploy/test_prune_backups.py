#!/usr/bin/env python3
"""Pruebas aisladas, sin Docker ni acceso a VPS, de retención conservadora."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import subprocess
import time

SOURCE = Path(__file__).with_name("prune-backups.sh").read_text()

def touch(path: Path, days: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"BACKUP_FICTICIO")
    t = time.time() - days * 86400
    os.utime(path, (t, t))

with TemporaryDirectory() as root:
    dep = Path(root) / "deploy"
    dep.mkdir()
    script = dep / "prune-backups.sh"
    script.write_text(SOURCE)
    base = dep / "backups"
    base.mkdir()
    old = [base / f"fact_central_2026090{i}T000000Z.dump" for i in range(1, 5)]
    for f in old:
        touch(f, 30)
    recent = base / "audit" / "factcentral_predeploy_20261020T000000Z.dump"
    touch(recent, 1)
    companion = old[0].with_suffix(".dump.sha256")
    companion.write_text("prueba")
    unrelated = base / "documento_fiscal_importante.dump"
    touch(unrelated, 60)
    subprocess.run(["bash", str(script)], check=True)
    assert recent.exists(), "Respaldo reciente eliminado"
    assert unrelated.exists(), "Archivo fuera del patrón eliminado"
    assert sum(f.exists() for f in old) == 1, "Deben quedar los 2 más recientes"
    assert not companion.exists(), "Checksum huérfano tras eliminar dump"
    # Repetibilidad: ejecutar nuevamente no debe modificar los respaldos restantes.
    subprocess.run(["bash", str(script)], check=True)
    assert recent.exists()
print("Retención segura: reciente protegido, otros archivos intactos, limpieza selectiva y repetibilidad OK")
