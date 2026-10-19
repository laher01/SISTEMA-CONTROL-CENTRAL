"""Contrato de lectura MISD: una liquidación generada bloquea el retiro.

No altera producción ni pagos. La comprobación es conservadora: cualquier
liquidación coincidente con período, moneda y ámbito congela el expediente.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Expediente, Miembro, PagoERP, PagoGestor, PagoResponsableERP


def motivo_bloqueo_liquidacion(session: Session, expediente: Expediente) -> str | None:
    filtros = (
        lambda modelo: (
            modelo.tenant_id == expediente.tenant_id,
            modelo.periodo_desde <= expediente.fecha_emision,
            modelo.periodo_hasta >= expediente.fecha_emision,
            modelo.moneda == expediente.moneda,
        )
    )
    if expediente.usuario_id is not None:
        pago_usuario = session.scalar(
            select(PagoERP.id)
            .where(*filtros(PagoERP), PagoERP.usuario_id == expediente.usuario_id)
            .limit(1)
        )
        if pago_usuario is not None:
            return "Liquidación de USUARIO generada para este período"

    if expediente.gestor_id is not None:
        pago_gestor = session.scalar(
            select(PagoGestor.id)
            .where(*filtros(PagoGestor), PagoGestor.gestor_id == expediente.gestor_id)
            .limit(1)
        )
        if pago_gestor is not None:
            return "Liquidación de GESTOR generada para este período"

    if expediente.usuario_id is not None:
        responsable_id = session.scalar(
            select(Miembro.responsable_id).where(
                Miembro.id == expediente.usuario_id,
                Miembro.tenant_id == expediente.tenant_id,
            )
        )
        if responsable_id is not None:
            pago_responsable = session.scalar(
                select(PagoResponsableERP.id)
                .where(
                    *filtros(PagoResponsableERP),
                    PagoResponsableERP.responsable_id == responsable_id,
                )
                .limit(1)
            )
            if pago_responsable is not None:
                return "Liquidación de RESPONSABLE generada para este período"
    return None


def motivo_bloqueo_voucher(session: Session, tenant_id: uuid.UUID, documento_id: uuid.UUID) -> str | None:
    """Un voucher ya vinculado a liquidación no puede eliminarse individualmente."""
    pago_id = session.scalar(
        select(PagoERP.id).where(
            PagoERP.tenant_id == tenant_id,
            PagoERP.voucher_documento_id == documento_id,
        ).limit(1)
    )
    if pago_id is not None:
        return "Voucher vinculado a liquidación generada"
    return None
