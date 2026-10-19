#!/usr/bin/env python3
"""Exportar manifiesto TSV únicamente de PostgreSQL RESTAURADO, transacción consistente.

Requiere psycopg instalado y una base con nombre factcentral_restore_*.
No realiza backups ni toma snapshots del almacenamiento documental.
"""
import argparse
import os
from pathlib import Path


def exportar(dsn: str, destino: Path) -> int:
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    nombre = conninfo_to_dict(dsn).get("dbname", "")
    if not nombre.startswith("factcentral_restore_"):
        raise ValueError("Solo bases aisladas factcentral_restore_*")
    if destino.exists() or destino.is_symlink():
        raise ValueError("El manifiesto ya existe")
    try:
        with psycopg.connect(dsn, autocommit=False) as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cursor.execute("SELECT count(*) FROM documentos")
                cantidad = cursor.fetchone()[0]
                with destino.open("xb") as salida:
                    os.chmod(destino, 0o600)
                    with cursor.copy(
                        "COPY (SELECT tenant_id::text, ruta_storage, sha256 "
                        "FROM documentos ORDER BY tenant_id, ruta_storage) "
                        "TO STDOUT WITH (FORMAT csv, DELIMITER E'\\t', HEADER false)"
                    ) as copia:
                        for bloque in copia:
                            salida.write(bloque)
                conexion.rollback()
        return cantidad
    except Exception:
        destino.unlink(missing_ok=True)
        raise


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dsn", required=True, help="DSN de la base RESTAURADA")
    p.add_argument("--salida", required=True, type=Path)
    a = p.parse_args()
    print("REGISTROS_RESTAURADOS:", exportar(a.dsn, a.salida))


if __name__ == "__main__":
    main()
