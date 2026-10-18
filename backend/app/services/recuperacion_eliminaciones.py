"""Diario durable y reconciliación conservadora de originales eliminados.

La recuperación se ejecuta explícitamente; nunca borra un archivo vigente.
"""
import json
import os
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Documento
from app.storage import AlmacenLocal


def registrar_intento(
    almacen: AlmacenLocal,
    tenant_id: uuid.UUID,
    pares: list[tuple[uuid.UUID, Path, Path]],
) -> Path:
    raiz = (almacen.base / str(tenant_id)).resolve()
    directorio = raiz / "_eliminaciones_pendientes"
    directorio.mkdir(parents=True, exist_ok=True)
    identificador = uuid.uuid4()
    destino = directorio / f"{identificador}.json"
    temporal = directorio / f".{identificador}.tmp"
    entradas = []
    for documento_id, original, cuarentena in pares:
        if not original.is_relative_to(raiz) or not cuarentena.is_relative_to(raiz):
            raise ValueError("Ruta fuera del tenant")
        entradas.append(
            {
                "documento_id": str(documento_id),
                "original": str(original.relative_to(raiz)),
                "cuarentena": str(cuarentena.relative_to(raiz)),
            }
        )
    with temporal.open("x", encoding="utf-8") as salida:
        json.dump({"tenant_id": str(tenant_id), "entradas": entradas}, salida)
        salida.flush()
        os.fsync(salida.fileno())
    temporal.replace(destino)
    _sincronizar_directorio(directorio)
    return destino


def _sincronizar_directorio(directorio: Path) -> None:
    fd = os.open(directorio, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def reconciliar_intento(
    session: Session, almacen: AlmacenLocal, tenant_id: uuid.UUID, manifiesto: Path
) -> str:
    """Usar presencia del registro SQL para restaurar o purgar la cuarentena.

    No sobreescribir originales existentes y no procesar diarios de otro tenant.
    """
    raiz = (almacen.base / str(tenant_id)).resolve()
    directorio = raiz / "_eliminaciones_pendientes"
    diario = manifiesto.resolve()
    if diario.parent != directorio or diario.suffix != ".json":
        raise ValueError("Manifiesto fuera del tenant")
    datos = json.loads(diario.read_text(encoding="utf-8"))
    if datos["tenant_id"] != str(tenant_id):
        raise ValueError("Manifiesto de tenant diferente")
    operaciones = []
    for entrada in datos["entradas"]:
        doc_id = uuid.UUID(entrada["documento_id"])
        original = (raiz / entrada["original"]).resolve()
        cuarentena = (raiz / entrada["cuarentena"]).resolve()
        if not original.is_relative_to(raiz) or not cuarentena.is_relative_to(raiz):
            raise ValueError("Ruta del manifiesto fuera del tenant")
        vigente = session.scalar(
            select(Documento.id).where(Documento.id == doc_id, Documento.tenant_id == tenant_id)
        )
        # Todas las validaciones antes de actuar: un conflicto requiere revisión.
        if vigente is not None and original.exists() and cuarentena.exists():
            raise ValueError("Conflicto entre original vigente y cuarentena")
        if vigente is not None and not original.exists() and not cuarentena.exists():
            raise ValueError("Falta original de documento vigente")
        operaciones.append((vigente is not None, original, cuarentena))
    for vigente, original, cuarentena in operaciones:
        if vigente:
            if cuarentena.exists():
                cuarentena.replace(original)
        elif cuarentena.exists():
            cuarentena.unlink()
    diario.unlink()
    _sincronizar_directorio(directorio)
    return "RECONCILIADO"


def listar_intentos(almacen: AlmacenLocal, tenant_id: uuid.UUID) -> list[Path]:
    directorio = (almacen.base / str(tenant_id)).resolve() / "_eliminaciones_pendientes"
    return sorted(directorio.glob("*.json")) if directorio.is_dir() else []


def reconciliar_pendientes(
    session: Session, almacen: AlmacenLocal, tenant_id: uuid.UUID
) -> tuple[int, list[str]]:
    """Reintentar diarios conservando para revisión cualquier fallo.

    Debe ejecutarse durante una ventana de mantenimiento sin ingestas
    concurrentes: no está permitido borrar a ciegas ni cambiar de tenant.
    """
    correctos = 0
    errores: list[str] = []
    for manifiesto in listar_intentos(almacen, tenant_id):
        try:
            reconciliar_intento(session, almacen, tenant_id, manifiesto)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            errores.append(f"{manifiesto.name}: {type(error).__name__}: {error}")
        else:
            correctos += 1
    return correctos, errores
