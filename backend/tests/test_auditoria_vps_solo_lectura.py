"""Seguridad del diagnóstico remoto: no mutar ni revelar producción."""

from pathlib import Path


def test_auditoria_vps_solo_lectura() -> None:
    raiz = Path(__file__).resolve().parents[2]
    script = (raiz / "deploy" / "auditar-vps-solo-lectura.sh").read_text(encoding="utf-8")
    assert "git rev-parse HEAD" in script
    assert "alembic current" in script
    assert "curl --fail" in script
    assert "docker compose" in script
    assert "AUDITORIA_COMPLETADA_SOLO_LECTURA" in script

    # Comandos prohibidos: ejecutar migraciones, modificar ramas o contenedores.
    for comando in (
        "alembic upgrade",
        "alembic downgrade",
        "git pull",
        "git fetch",
        "git reset",
        "git checkout",
        "docker compose up",
        "docker compose down",
        "docker compose build",
        "docker restart",
        "pg_restore",
        "pg_dump",
    ):
        assert comando not in script
