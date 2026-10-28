"""Preflight y borrado seguro de archivos fiscales."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import item_models as _item_models  # noqa: F401 - registra sus claves foráneas.
from app.models import Base, Documento, EliminacionArchivoPendiente
from app.storage import AlmacenLocal


def bloquear_clave_archivo(session: Session, tenant_id: UUID, sha256: str) -> None:
    """Serializa ingesta y borrado físico por tenant/SHA en PostgreSQL."""
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:clave, 0))"),
            {"clave": f"factcentral:{tenant_id}:{sha256}"},
        )


def procesar_archivo_pendiente(
    session: Session,
    almacen: AlmacenLocal,
    pendiente: EliminacionArchivoPendiente,
) -> bool:
    """Borra bytes solo después de bloquear y comprobar que no queda referencia."""
    pendiente.intentos += 1
    bloquear_clave_archivo(session, pendiente.tenant_id, Path(pendiente.ruta_storage).name)
    referenciado = session.scalar(
        select(Documento.id)
        .where(
            Documento.tenant_id == pendiente.tenant_id,
            Documento.ruta_storage == pendiente.ruta_storage,
            Documento.deleted_at.is_(None),
        )
        .limit(1)
    )
    if referenciado is not None:
        pendiente.estado = "BLOQUEADO"
        pendiente.ultimo_error = "Archivo todavía referenciado por un documento"
        return False
    try:
        almacen.ruta_absoluta(pendiente.ruta_storage).unlink(missing_ok=True)
        pendiente.estado = "COMPLETADO"
        pendiente.ultimo_error = None
        pendiente.completado_at = datetime.now(UTC)
        return True
    except (OSError, ValueError) as exc:
        pendiente.estado = "PENDIENTE"
        pendiente.ultimo_error = str(exc)[:500]
        return False


def tablas_que_referencian(
    session: Session,
    *,
    documento_ids: set[object],
    expediente_id: object | None = None,
) -> list[str]:
    """Devuelve tablas dependientes; no modifica datos ni permite borrados parciales."""
    objetivos: dict[str, set[object]] = {}
    if documento_ids:
        objetivos["documentos"] = documento_ids
    if expediente_id is not None:
        objetivos["expedientes"] = {expediente_id}

    bloqueadas: set[str] = set()
    for tabla in Base.metadata.tables.values():
        if tabla.name in {"documentos", "expedientes"}:
            continue
        for columna in tabla.columns:
            if not columna.foreign_keys:
                continue
            for clave in columna.foreign_keys:
                ids = objetivos.get(clave.column.table.name)
                if not ids:
                    continue
                if (
                    expediente_id is not None
                    and clave.column.table.name == "expedientes"
                    and tabla.name in {"alertas", "alertas_manuales"}
                ):
                    continue
                existe = session.scalar(select(tabla.c["id"]).where(columna.in_(ids)).limit(1))
                if existe is not None:
                    bloqueadas.add(tabla.name)
                    break
    return sorted(bloqueadas)
