"""La relación N:M depende de las referencias GRE y las fórmulas NEXUS."""

import ast
from pathlib import Path

VERSIONES = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _revisiones(archivo: str) -> tuple[str, str | None]:
    fuente = (VERSIONES / archivo).read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    asignaciones = {}
    for nodo in arbol.body:
        if (
            isinstance(nodo, ast.AnnAssign)
            and isinstance(nodo.target, ast.Name)
            and nodo.target.id in {"revision", "down_revision"}
        ):
            asignaciones[nodo.target.id] = ast.literal_eval(nodo.value)
    return asignaciones["revision"], asignaciones["down_revision"]


def test_cadena_referencias_y_relaciones_documentales() -> None:
    referencias = _revisiones("20261012_0030_referencias_gre.py")
    nexus = _revisiones("20261013_0031_nexus_formulas.py")
    relaciones = _revisiones("20261013_0032_relaciones_documentos.py")
    assert referencias == ("0030", "0029")
    assert nexus == ("0031", "0030")
    assert relaciones == ("0032", "0031")
