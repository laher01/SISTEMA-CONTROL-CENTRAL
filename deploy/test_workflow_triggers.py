"""Regression guard: no workflow may connect to the VPS on a push to main.

CI-only workflows may run on push. Remote workflows must remain manually
triggered; this prevents an innocent merge from updating the VPS.
"""
from pathlib import Path
import re


WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
EVENT_LINE = re.compile(r"^  ([A-Za-z_][A-Za-z_0-9]*):(?:\s|$)", re.MULTILINE)


def events(source: str) -> set[str]:
    match = re.search(r"^on:\s*\n(?P<body>(?:^[ \t].*\n|^\s*\n)*)", source, re.MULTILINE)
    if match is None:
        raise AssertionError("El workflow debe declarar un bloque on: explícito")
    return set(EVENT_LINE.findall(match.group("body")))


def test_no_remote_workflow_runs_on_push() -> None:
    workflows = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    assert workflows, "No se encontraron workflows"
    remote = []
    for path in workflows:
        source = path.read_text(encoding="utf-8")
        triggers = events(source)
        assert triggers, f"{path.name}: sin disparadores reconocibles"
        if "VPS_SSH_PRIVATE_KEY" in source:
            remote.append(path.name)
            assert "push" not in triggers, f"{path.name}: acceso SSH automático por push"
            assert "workflow_dispatch" in triggers, (
                f"{path.name}: acceso SSH sin activación manual"
            )
    assert "deploy-staging.yml" in remote
    deploy = (WORKFLOWS / "deploy-staging.yml").read_text(encoding="utf-8")
    assert events(deploy) == {"workflow_dispatch"}, (
        "El despliegue debe permanecer exclusivamente manual"
    )
    assert "github.ref == 'refs/heads/main'" in deploy, (
        "El despliegue debe exigir main"
    )
    assert "needs: [verify-backend, verify-frontend]" in deploy, (
        "El despliegue debe esperar a las pruebas"
    )


if __name__ == "__main__":
    test_no_remote_workflow_runs_on_push()
    print("Seguridad CI: ningún workflow remoto se ejecuta por push")
