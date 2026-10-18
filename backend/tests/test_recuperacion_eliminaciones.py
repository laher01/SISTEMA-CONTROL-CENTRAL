"""Recuperación durable de archivos tras interrupción de eliminación."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Documento, Tenant
from app.services.recuperacion_eliminaciones import (
    listar_intentos,
    reconciliar_intento,
    reconciliar_pendientes,
    registrar_intento,
)
from app.storage import AlmacenLocal


def test_recupera_original_si_documento_permanece_en_bd(session: Session, tmp_path) -> None:
    tenant = Tenant(nombre="tenant_recuperacion_280")
    session.add(tenant)
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    contenido = b"%PDF prueba de restauracion"
    sha = "a" * 64
    ruta = almacen.guardar(tenant.id, sha, contenido)
    documento = Documento(
        tenant_id=tenant.id,
        sha256=sha,
        nombre_original="restaurar.pdf",
        ruta_storage=ruta,
        mime_type="application/pdf",
        tamano_bytes=len(contenido),
        tipo_documento="OTRO",
        estado="PENDIENTE_CLASIFICACION",
    )
    session.add(documento)
    session.commit()
    original = almacen.ruta_absoluta(ruta)
    temporal = original.with_name(f".eliminando-{documento.id}")
    diario = registrar_intento(almacen, tenant.id, [(documento.id, original, temporal)])
    original.replace(temporal)
    assert reconciliar_intento(session, almacen, tenant.id, diario) == "RECONCILIADO"
    assert original.read_bytes() == contenido
    assert not temporal.exists()
    assert listar_intentos(almacen, tenant.id) == []


def test_limpia_cuarentena_si_documento_ya_no_existe(session: Session, tmp_path) -> None:
    tenant_id = uuid.uuid4()
    almacen = AlmacenLocal(tmp_path)
    contenido = b"%PDF prueba eliminada"
    ruta = almacen.guardar(tenant_id, "b" * 64, contenido)
    original = almacen.ruta_absoluta(ruta)
    documento_id = uuid.uuid4()
    temporal = original.with_name(f".eliminando-{documento_id}")
    diario = registrar_intento(almacen, tenant_id, [(documento_id, original, temporal)])
    original.replace(temporal)
    assert reconciliar_intento(session, almacen, tenant_id, diario) == "RECONCILIADO"
    assert not temporal.exists()
    assert not diario.exists()


def test_no_sobrescribe_original_si_hay_conflicto(session: Session, tmp_path) -> None:
    tenant = Tenant(nombre="tenant_conflicto_280")
    session.add(tenant)
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    sha = "c" * 64
    ruta = almacen.guardar(tenant.id, sha, b"original nuevo")
    documento = Documento(
        tenant_id=tenant.id,
        sha256=sha,
        nombre_original="original.pdf",
        ruta_storage=ruta,
        mime_type="application/pdf",
        tamano_bytes=len(b"original nuevo"),
        tipo_documento="OTRO",
        estado="PENDIENTE_CLASIFICACION",
    )
    session.add(documento)
    session.commit()
    original = almacen.ruta_absoluta(ruta)
    temporal = original.with_name(f".eliminando-{documento.id}")
    temporal.write_bytes(b"original previo")
    diario = registrar_intento(almacen, tenant.id, [(documento.id, original, temporal)])
    with pytest.raises(ValueError, match="Conflicto"):
        reconciliar_intento(session, almacen, tenant.id, diario)
    assert original.read_bytes() == b"original nuevo"
    assert temporal.read_bytes() == b"original previo"
    assert diario.exists()


def test_reintento_no_procesa_dos_veces(session: Session, tmp_path) -> None:
    tenant_id = uuid.uuid4()
    almacen = AlmacenLocal(tmp_path)
    ruta = almacen.guardar(tenant_id, "d" * 64, b"historico")
    original = almacen.ruta_absoluta(ruta)
    documento_id = uuid.uuid4()
    temporal = original.with_name(f".eliminando-{documento_id}")
    registrar_intento(almacen, tenant_id, [(documento_id, original, temporal)])
    original.replace(temporal)

    primera = reconciliar_pendientes(session, almacen, tenant_id)
    segunda = reconciliar_pendientes(session, almacen, tenant_id)
    assert primera == (1, [])
    assert segunda == (0, [])
    assert listar_intentos(almacen, tenant_id) == []


def test_reingesta_mismo_sha_impide_purgar_cuarentena_antigua(session: Session, tmp_path) -> None:
    tenant = Tenant(nombre="tenant_reingesta_concurrente_280")
    session.add(tenant)
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    contenido = b"reingreso con igual contenido"
    ruta = almacen.guardar(tenant.id, "e" * 64, contenido)
    original = almacen.ruta_absoluta(ruta)
    antiguo_id = uuid.uuid4()
    cuarentena = original.with_name(f".eliminando-{antiguo_id}")
    diario = registrar_intento(almacen, tenant.id, [(antiguo_id, original, cuarentena)])
    original.replace(cuarentena)
    original.write_bytes(contenido)
    nuevo = Documento(
        tenant_id=tenant.id,
        sha256="e" * 64,
        nombre_original="reingresado.pdf",
        mime_type="application/pdf",
        tamano_bytes=len(contenido),
        ruta_storage=ruta,
        tipo_documento="OTRO",
        estado="PENDIENTE_CLASIFICACION",
    )
    session.add(nuevo)
    session.commit()

    with pytest.raises(ValueError, match="reingresado"):
        reconciliar_intento(session, almacen, tenant.id, diario)
    assert original.read_bytes() == contenido
    assert cuarentena.exists()
    assert diario.exists()


def test_reconciliacion_no_borra_cuarentena_con_ruta_ocupada_sin_commit(
    session: Session, tmp_path
) -> None:
    tenant_id = uuid.uuid4()
    almacen = AlmacenLocal(tmp_path)
    ruta = almacen.guardar(tenant_id, "f" * 64, b"archivo original")
    original = almacen.ruta_absoluta(ruta)
    antiguo_id = uuid.uuid4()
    cuarentena = original.with_name(f".eliminando-{antiguo_id}")
    diario = registrar_intento(almacen, tenant_id, [(antiguo_id, original, cuarentena)])
    original.replace(cuarentena)
    original.write_bytes(b"ingesta en progreso")
    with pytest.raises(ValueError, match="Ruta ocupada"):
        reconciliar_intento(session, almacen, tenant_id, diario)
    assert original.read_bytes() == b"ingesta en progreso"
    assert cuarentena.read_bytes() == b"archivo original"
    assert diario.exists()
