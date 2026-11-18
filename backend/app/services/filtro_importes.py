"""Filtro monetario para los listados documentales."""

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import HTTPException, Query
from sqlalchemy import Select, case, func
from sqlalchemy.orm import aliased

from app.enums import Moneda
from app.models import Documento, Expediente
from app.services.orden_listados import campo_documento, importe_documento

LimiteImporte = Annotated[Decimal | None, Query(max_digits=14, decimal_places=2)]


def filtrar_importes[Fila: tuple[Any, ...]](
    consulta: Select[Fila],
    tenant_id: UUID,
    minimo: Decimal | None,
    maximo: Decimal | None,
    estricto: bool,
    moneda: Moneda,
    *,
    documento: bool = False,
) -> Select[Fila]:
    if minimo is None and maximo is None:
        return consulta
    if (
        minimo is not None
        and maximo is not None
        and (minimo > maximo or (estricto and minimo == maximo))
    ):
        raise HTTPException(422, "El rango de importes no es válido")

    if documento:
        expediente = aliased(Expediente)
        consulta = consulta.outerjoin(
            expediente,
            (expediente.id == Documento.expediente_id) & (expediente.tenant_id == tenant_id),
        )
        importe = importe_documento(expediente)
        moneda_fila = func.coalesce(
            case((Documento.tipo_documento.in_(("FACT", "RHE")), expediente.moneda)),
            campo_documento("moneda"),
        )
    else:
        importe = Expediente.importe_total
        moneda_fila = Expediente.moneda

    consulta = consulta.where(moneda_fila == moneda.value)
    if minimo is not None:
        consulta = consulta.where(importe > minimo if estricto else importe >= minimo)
    if maximo is not None:
        consulta = consulta.where(importe <= maximo)
    return consulta
