"""Bloquear cadenas Alembic con identificadores duplicados o padres ausentes."""

import ast
from pathlib import Path

VERSIONES = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _identidad(path: Path) -> tuple[str, str | tuple[str, ...] | None]:
    arbol = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    datos = {}
    for nodo in arbol.body:
        if (
            isinstance(nodo, ast.AnnAssign)
            and isinstance(nodo.target, ast.Name)
            and nodo.target.id in {"revision", "down_revision"}
        ):
            datos[nodo.target.id] = ast.literal_eval(nodo.value)
    return datos["revision"], datos.get("down_revision")


def test_revisiones_alembic_no_se_duplican() -> None:
    identificadores: dict[str, str] = {}
    for ruta in sorted(VERSIONES.glob("*.py")):
        if ruta.name == "__init__.py":
            continue
        revision, _ = _identidad(ruta)
        assert revision not in identificadores, (
            f"Identificador Alembic repetido {revision}: "
            f"{identificadores.get(revision)} y {ruta.name}"
        )
        identificadores[revision] = ruta.name


def test_padres_alembic_existen() -> None:
    revisiones = {
        revision: padre
        for ruta in VERSIONES.glob("*.py")
        if ruta.name != "__init__.py"
        for revision, padre in [_identidad(ruta)]
    }
    for revision, padre in revisiones.items():
        padres = padre if isinstance(padre, tuple) else (padre,)
        for anterior in padres:
            if anterior is not None:
                assert anterior in revisiones, f"{revision}: falta padre {anterior}"
