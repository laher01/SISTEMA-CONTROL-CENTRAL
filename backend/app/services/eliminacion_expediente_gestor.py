"""Elimina expedientes completos únicamente cuando no deja referencias externas."""

import uuid

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.item_models import AuditoriaFacturaItem, LineaComprobanteItem
from app.models import (
    Alerta,
    AlertaManual,
    CorreccionIA,
    Documento,
    Expediente,
    PagoERP,
    ReferenciaGRE,
    RelacionDocumento,
)
from app.services import auditoria
from app.services.recuperacion_eliminaciones import (
    reconciliar_intento,
    registrar_intento,
    sincronizar_movimientos,
)
from app.storage import AlmacenLocal


class EliminacionNoSegura(ValueError):
    """Hay vínculos externos o falta titularidad verificable."""


def eliminar_expediente_del_gestor(
    session: Session,
    almacen: AlmacenLocal,
    tenant_id: uuid.UUID,
    expediente_id: uuid.UUID,
    gestor_id: uuid.UUID,
) -> None:
    """Borra un expediente y sus originales, bajo una única transacción DB.

    Rechaza vínculos externos, pagos ERP asociados y dueños desconocidos.
    No borra expedientes ajenos ni documentos de otros gestores.
    """
    expediente = session.scalar(
        select(Expediente)
        .where(Expediente.id == expediente_id, Expediente.tenant_id == tenant_id)
        .with_for_update()
    )
    if expediente is None or expediente.gestor_id != gestor_id:
        raise EliminacionNoSegura("El gestor no es propietario del expediente")
    documentos = list(
        session.scalars(
            select(Documento)
            .where(Documento.tenant_id == tenant_id, Documento.expediente_id == expediente_id)
            .order_by(Documento.id)
            .with_for_update()
        )
    )
    if not documentos or any(d.gestor_id != gestor_id for d in documentos):
        raise EliminacionNoSegura("Titularidad documental incompleta o incompatible")
    ids = [d.id for d in documentos]
    relaciones_externas = session.scalar(
        select(RelacionDocumento.id)
        .where(
            RelacionDocumento.tenant_id == tenant_id,
            or_(
                RelacionDocumento.origen_id.in_(ids),
                RelacionDocumento.destino_id.in_(ids),
            ),
            ~RelacionDocumento.origen_id.in_(ids) | ~RelacionDocumento.destino_id.in_(ids),
        )
        .limit(1)
    )
    if relaciones_externas is not None:
        raise EliminacionNoSegura("Existe relación con documentos fuera del expediente")
    pago = session.scalar(
        select(PagoERP.id)
        .where(
            PagoERP.tenant_id == tenant_id,
            PagoERP.voucher_documento_id.in_(ids),
        )
        .limit(1)
    )
    if pago is not None:
        raise EliminacionNoSegura("Existe un pago ERP vinculado")
    referencia_externa = session.scalar(
        select(ReferenciaGRE.id)
        .where(
            ReferenciaGRE.tenant_id == tenant_id,
            ReferenciaGRE.expediente_id == expediente_id,
            ~ReferenciaGRE.documento_id.in_(ids),
        )
        .limit(1)
    )
    if referencia_externa is not None:
        raise EliminacionNoSegura("Referencia GRE de otro documento")

    # Una referencia física compartida nunca debe borrarse junto con este expediente.
    # Restringir por tenant y comprobar además el resto de registros activos.
    rutas = [d.ruta_storage for d in documentos]
    if len(set(rutas)) != len(rutas):
        raise EliminacionNoSegura("Original compartido por documentos del expediente")
    referencia_archivo = session.scalar(
        select(Documento.id)
        .where(
            Documento.ruta_storage.in_(rutas),
            Documento.id.not_in(ids),
        )
        .limit(1)
    )
    if referencia_archivo is not None:
        raise EliminacionNoSegura("Original referenciado por otro documento")

    # Solo rutas por SHA bajo la raíz del tenant y sin vínculos físicos externos.
    pares = []
    for doc in documentos:
        ruta = doc.ruta_storage
        if not ruta.startswith(f"{tenant_id}/") or ".." in ruta.split("/"):
            raise EliminacionNoSegura("Ruta del original fuera del tenant")
        original = almacen.ruta_absoluta(ruta)
        raiz_tenant = (almacen.base / str(tenant_id)).resolve()
        if not original.is_relative_to(raiz_tenant) or not original.is_file():
            raise EliminacionNoSegura("Original no disponible o fuera del tenant")
        temporal = original.with_name(f".eliminando-{doc.id}")
        if temporal.exists():
            raise EliminacionNoSegura("Eliminación anterior pendiente de revisión")
        pares.append((original, temporal))

    diario = registrar_intento(
        almacen,
        tenant_id,
        [(d.id, orig, temp) for d, (orig, temp) in zip(documentos, pares, strict=True)],
    )
    movidos = []
    try:
        for original, temporal in pares:
            original.replace(temporal)
            movidos.append((original, temporal))
        sincronizar_movimientos(movidos)
        session.execute(
            delete(RelacionDocumento).where(
                RelacionDocumento.tenant_id == tenant_id,
                RelacionDocumento.origen_id.in_(ids),
                RelacionDocumento.destino_id.in_(ids),
            )
        )
        for modelo, columna in (
            (CorreccionIA, CorreccionIA.documento_id),
            (LineaComprobanteItem, LineaComprobanteItem.documento_id),
            (ReferenciaGRE, ReferenciaGRE.documento_id),
        ):
            session.execute(delete(modelo).where(modelo.tenant_id == tenant_id, columna.in_(ids)))
        for modelo_expediente in (Alerta, AlertaManual, AuditoriaFacturaItem):
            session.execute(
                delete(modelo_expediente).where(
                    modelo_expediente.tenant_id == tenant_id,
                    modelo_expediente.expediente_id == expediente_id,
                )
            )
        # Sincronizar colección ORM para evitar que el flush intente desvincular
        # documentos eliminados por DELETE a nivel SQL.
        session.execute(
            delete(Documento).where(Documento.tenant_id == tenant_id, Documento.id.in_(ids))
        )
        session.execute(
            delete(Expediente).where(
                Expediente.tenant_id == tenant_id, Expediente.id == expediente_id
            )
        )
        auditoria.registrar(
            session,
            tenant_id,
            "EXPEDIENTE_ELIMINADO_DEFINITIVAMENTE",
            "expediente",
            expediente_id,
            {"cantidad_documentos": len(ids)},
        )
        session.commit()
    except Exception:
        session.rollback()
        # Si falla la restauración, el diario queda para recuperación posterior.
        reconciliar_intento(session, almacen, tenant_id, diario)
        raise
    session.expire_all()
    reconciliar_intento(session, almacen, tenant_id, diario)
