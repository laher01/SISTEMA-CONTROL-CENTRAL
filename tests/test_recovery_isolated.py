#!/usr/bin/env python3
"""Contrato de recuperación AISLADA, sin datos ni red de producción."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RecoveryFixtureTests(unittest.TestCase):
    def test_documents_snapshot_and_recovery_after_simulated_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live = root / "documents"
            live.mkdir()
            sample = live / "tenant-demo" / "comprobante.pdf"
            sample.parent.mkdir()
            sample.write_bytes(b"%PDF-1.4\nfixture-sintetico-sin-datos-reales\n")
            original = sha(sample)
            archive = root / "snapshot.tar"
            with tarfile.open(archive, "w") as tar:
                tar.add(live, arcname="documents")
            manifest = sha(archive)
            # Simular un despliegue fallido que modifica los archivos de prueba.
            sample.write_bytes(b"corrupted-by-simulated-deployment")
            self.assertNotEqual(sha(sample), original)
            self.assertEqual(sha(archive), manifest)
            restore_root = root / "isolated-restore"
            restore_root.mkdir()
            with tarfile.open(archive) as tar:
                for member in tar.getmembers():
                    if member.name.startswith("/") or ".." in Path(member.name).parts:
                        raise ValueError("unsafe archive")
                tar.extractall(restore_root, filter="data")
            recovered = restore_root / "documents" / "tenant-demo" / "comprobante.pdf"
            self.assertEqual(sha(recovered), original)
            # Nunca sobrescribir archivos supuestamente productivos en estas pruebas.
            self.assertNotEqual(sha(sample), original)

    def test_rejects_tampered_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "snapshot"
            artifact.write_bytes(b"backup")
            expected = sha(artifact)
            artifact.write_bytes(b"tampered")
            self.assertNotEqual(sha(artifact), expected)

    def test_shell_scripts_parse(self):
        repository = Path(__file__).resolve().parents[1]
        for script in ["deploy/deploy.sh", "deploy/bootstrap-main.sh",
                       "deploy/preflight-backup-restore-items.sh"]:
            result = subprocess.run(["bash", "-n", str(repository / script)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=f"{script}: {result.stderr}")

    def test_recovery_gate_stays_fail_closed_for_pr(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/deploy-staging.yml").read_text()
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("vars.ORACLE_AUTO_DEPLOY_ENABLED == 'true'", workflow)
        self.assertIn('test "$RECOVERY_READY" = "true"', workflow)
        self.assertIn("oracle-autodeploy", workflow)
        self.assertIn("needs: [verify-backend, verify-frontend, verify-recovery-isolated]", workflow)


if __name__ == "__main__":
    unittest.main()
