"""Liquidaciones de Gestores programadas exclusivamente por su Usuario."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import Expediente, Gestor, PagoGestor
from app.services import auditoria

router = APIRouter(prefix="/pagos-gestores", tags=["pagos-gestores"])


class SolicitudGestor(BaseModel):
    gestor_id: uuid.UUID
    desde: date
    hasta: date
    moneda: str = Field(pattern="^(PEN|USD)$")


def _gestor_propio(
    session: SessionDep, tenant_id: uuid.UUID, usuario_id: uuid.UUID, gestor_id: uuid.UUID
) -> Gestor:
    gestor = session.get(Gestor, gestor_id)
    if (
        gestor is None
        or gestor.tenant_id != tenant_id
        or gestor.usuario_id != usuario_id
        or gestor.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Gestor fuera del equipo")
    return gestor


def _calcular(
    session: SessionDep,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    gestor: Gestor,
    datos: SolicitudGestor,
) -> tuple[Decimal, Decimal, Decimal]:
    if datos.hasta < datos.desde:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Periodo inválido")
    if gestor.porcentaje_comision is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Administración debe configurar el porcentaje del Gestor",
        )
    produccion = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(Expediente.importe_total), 0)).where(
                Expediente.tenant_id == tenant_id,
                Expediente.usuario_id == usuario_id,
                Expediente.gestor_id == gestor.id,
                Expediente.deleted_at.is_(None),
                Expediente.moneda == datos.moneda,
                Expediente.fecha_emision >= datos.desde,
                Expediente.fecha_emision <= datos.hasta,
            )
        )
        or 0
    )
    tasa = Decimal(gestor.porcentaje_comision)
    bruto = (produccion * tasa / Decimal("100")).quantize(Decimal("0.01"))
    return produccion, tasa, bruto


@router.get("")
def listar(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[dict[str, str]]:
    if auth.rol != RolMiembro.USUARIO or auth.usuario_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Usuario")
    pagos = session.scalars(
        select(PagoGestor)
        .where(PagoGestor.tenant_id == tenant_id, PagoGestor.usuario_id == auth.usuario_id)
        .order_by(PagoGestor.created_at.desc())
    )
    return [
        {
            "id": str(p.id),
            "gestor_id": str(p.gestor_id),
            "desde": p.periodo_desde.isoformat(),
            "hasta": p.periodo_hasta.isoformat(),
            "moneda": p.moneda,
            "produccion": str(p.produccion_total),
            "porcentaje": str(p.porcentaje),
            "saldo": str(p.saldo),
            "estado": p.estado,
        }
        for p in pagos
    ]


@router.post("/cotizar")
def cotizar(
    datos: SolicitudGestor, session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> dict[str, str]:
    if auth.rol != RolMiembro.USUARIO or auth.usuario_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Usuario")
    gestor = _gestor_propio(session, tenant_id, auth.usuario_id, datos.gestor_id)
    produccion, tasa, bruto = _calcular(session, tenant_id, auth.usuario_id, gestor, datos)
    return {
        "produccion": str(produccion),
        "porcentaje": str(tasa),
        "bruto": str(bruto),
    }


@router.post("/programar", status_code=status.HTTP_201_CREATED)
def programar(
    datos: SolicitudGestor, session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> dict[str, str]:
    if auth.rol != RolMiembro.USUARIO or auth.usuario_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Usuario")
    gestor = _gestor_propio(session, tenant_id, auth.usuario_id, datos.gestor_id)
    if session.scalar(
        select(PagoGestor.id).where(
            PagoGestor.tenant_id == tenant_id,
            PagoGestor.gestor_id == gestor.id,
            PagoGestor.moneda == datos.moneda,
            PagoGestor.periodo_desde <= datos.hasta,
            PagoGestor.periodo_hasta >= datos.desde,
        )
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Periodo ya programado")
    produccion, tasa, bruto = _calcular(session, tenant_id, auth.usuario_id, gestor, datos)
    pago = PagoGestor(
        tenant_id=tenant_id,
        usuario_id=auth.usuario_id,
        gestor_id=gestor.id,
        creado_por_cuenta_id=auth.cuenta_id,
        periodo_desde=datos.desde,
        periodo_hasta=datos.hasta,
        moneda=datos.moneda,
        produccion_total=produccion,
        porcentaje=tasa,
        bruto=bruto,
        saldo=bruto,
        estado="PROGRAMADO",
    )
    session.add(pago)
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_GESTOR_PROGRAMADO",
        "pago_gestor",
        pago.id,
        {"gestor_id": str(gestor.id), "porcentaje": str(tasa), "saldo": str(bruto)},
    )
    session.commit()
    return {"id": str(pago.id), "saldo": str(bruto)}


@router.delete("/{pago_id}", status_code=status.HTTP_204_NO_CONTENT)
def anular(
    pago_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> None:
    if auth.rol != RolMiembro.USUARIO or auth.usuario_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Usuario")
    pago = session.get(PagoGestor, pago_id)
    if pago is None or pago.tenant_id != tenant_id or pago.usuario_id != auth.usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    if pago.estado != "PROGRAMADO":
        raise HTTPException(status.HTTP_409_CONFLICT, "No puede anularse un pago aplicado")
    auditoria.registrar(
        session,
        tenant_id,
        "PAGO_GESTOR_ANULADO",
        "pago_gestor",
        pago.id,
        {"gestor_id": str(pago.gestor_id), "saldo": str(pago.saldo)},
    )
    session.delete(pago)
    session.commit()
