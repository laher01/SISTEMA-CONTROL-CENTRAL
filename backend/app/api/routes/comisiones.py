"""Tarifas contractuales de comisión por Receptor, para Usuarios y Gestores."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import Empresa, Expediente, Gestor, Miembro
from app.services.comisiones import calcular_comisiones_por_receptor

router = APIRouter(prefix="/comisiones", tags=["comisiones"])


class ConsultaComision(BaseModel):
    usuario_id: uuid.UUID
    gestor_id: uuid.UUID | None = None
    desde: date
    hasta: date
    moneda: Literal["PEN", "USD"] = "PEN"
    porcentajes_por_receptor: dict[uuid.UUID, Decimal] = Field(default_factory=dict)
    porcentaje_global: Decimal | None = None


@router.post("/simular")
def simular(
    datos: ConsultaComision,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    if auth.rol not in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.RESPONSABLE,
        RolMiembro.USUARIO,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede consultar comisiones subordinadas")
    if auth.rol == RolMiembro.USUARIO and auth.usuario_id != datos.usuario_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario fuera de alcance")
    usuario = session.get(Miembro, datos.usuario_id)
    if usuario is None or usuario.tenant_id != tenant_id or usuario.rol != RolMiembro.USUARIO:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Usuario inválido")
    if auth.rol == RolMiembro.RESPONSABLE:
        if usuario.responsable_id != auth.miembro_id or datos.gestor_id is not None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Responsable solo puede calcular el resultado de sus Usuarios",
            )
    if datos.gestor_id is not None:
        gestor = session.get(Gestor, datos.gestor_id)
        if gestor is None or gestor.tenant_id != tenant_id or gestor.usuario_id != usuario.id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Gestor fuera del Usuario")
    if datos.hasta < datos.desde:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Periodo inválido")
    if datos.porcentaje_global is not None and datos.porcentajes_por_receptor:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Elija tasa global o tasas por receptor"
        )
    if datos.porcentaje_global is not None and not (0 <= datos.porcentaje_global <= 100):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Tasa inválida")
    for receptor_id, tasa in datos.porcentajes_por_receptor.items():
        receptor = session.get(Empresa, receptor_id)
        if receptor is None or receptor.tenant_id != tenant_id or not (0 <= tasa <= 100):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Receptor o tasa inválidos")
    filtros = [
        Expediente.tenant_id == tenant_id,
        Expediente.deleted_at.is_(None),
        Expediente.usuario_id == datos.usuario_id,
        Expediente.fecha_emision >= datos.desde,
        Expediente.fecha_emision <= datos.hasta,
        Expediente.moneda == datos.moneda,
    ]
    if datos.gestor_id is not None:
        filtros.append(Expediente.gestor_id == datos.gestor_id)
    filas = session.execute(
        select(Expediente.receptor_id, func.sum(Expediente.importe_total))
        .where(*filtros)
        .group_by(Expediente.receptor_id)
    )
    try:
        resultado = calcular_comisiones_por_receptor(
            {receptor: Decimal(total) for receptor, total in filas},
            porcentajes_por_receptor=datos.porcentajes_por_receptor,
            porcentaje_global=datos.porcentaje_global,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return {
        "usuario_id": str(datos.usuario_id),
        "gestor_id": str(datos.gestor_id) if datos.gestor_id else None,
        "moneda": datos.moneda,
        "total_produccion": str(resultado["total_produccion"]),
        "comision_total": str(resultado["comision_total"]),
        "detalle": resultado["detalle"],
        "simulacion": True,
        "aviso": (
            "No registra, aprueba ni realiza pagos. Validar producción y tarifas antes de liquidar."
        ),
    }
