"""Inspección y recuperación manual de eliminaciones (nunca automática).

Desde backend: uv run python scripts/reconciliar_eliminaciones.py --tenant UUID
Para ejecutar: agregar --execute DURANTE MANTENIMIENTO SIN INGESTAS.
"""
import argparse
import uuid

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.services.recuperacion_eliminaciones import listar_intentos, reconciliar_pendientes
from app.storage import AlmacenLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Conciliar cuarentenas documentales por tenant")
    parser.add_argument("--tenant", required=True, type=uuid.UUID)
    parser.add_argument(
        "--execute", action="store_true", help="Aplicar recuperación; requiere ventana"
    )
    args = parser.parse_args()
    almacen = AlmacenLocal(get_settings().storage_dir)
    pendientes = listar_intentos(almacen, args.tenant)
    print(f"Diarios pendientes tenant {args.tenant}: {len(pendientes)}")
    if not args.execute:
        print("Solo inspección: no se han modificado archivos.")
        return
    with get_sessionmaker()() as session:
        completados, errores = reconciliar_pendientes(session, almacen, args.tenant)
    print(f"Reconciliados: {completados}; conflictos: {len(errores)}")
    for error in errores:
        print(f"PENDIENTE DE REVISION: {error}")
    if errores:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
