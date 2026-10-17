"""Protección del deploy frente a carreras de main."""

from pathlib import Path


def test_deploy_fija_sha_validado_antes_de_actualizar() -> None:
    script = (Path(__file__).resolve().parents[2] / "deploy" / "deploy.sh").read_text()
    assert 'if [ -n "${EXPECTED_COMMIT:-}" ]; then' in script
    assert 'git rev-parse origin/main' in script
    assert 'git merge --ff-only "$EXPECTED_COMMIT"' in script
    assert 'current_commit="$(git rev-parse HEAD)"' in script
    assert (
        'if [ -n "${EXPECTED_COMMIT:-}" ] && [ "$current_commit" != "$EXPECTED_COMMIT" ]; then'
        in script
    )

    protected, fallback = script.split(
        "else\n  # Compatibilidad con ejecuciones operativas anteriores", 1
    )
    assert "git pull --ff-only origin main" not in protected
    assert "git pull --ff-only origin main" in fallback
