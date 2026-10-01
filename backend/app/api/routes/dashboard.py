from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import case, func, select

from app.api.deps import SessionDep, SettingsDep, TenantDep
from app.enums import EstadoDocumento, EstadoExpediente, Moneda, TipoAlerta
from app.models import Alerta, Documento, Expediente
from app.schemas import DashboardResumen, MontosMoneda

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=DashboardResumen)
def resumen(session: SessionDep, settings: SettingsDep, tenant_id: TenantDep) -> DashboardResumen:
    vigentes = (Expediente.tenant_id == tenant_id, Expediente.deleted_at.is_(None))

    por_estado = {e: 0 for e in EstadoExpediente}
    for estado, total in session.execute(
        select(Expediente.estado, func.count()).where(*vigentes).group_by(Expediente.estado)
    ):
        por_estado[EstadoExpediente(estado)] = total

    pendientes_aprobacion = (
        session.scalar(
            select(func.count()).where(*vigentes, Expediente.pendiente_aprobacion.is_(True))
        )
        or 0
    )

    umbrales = {
        Moneda.PEN: settings.umbral_bancarizacion_pen,
        Moneda.USD: settings.umbral_bancarizacion_usd,
    }
    montos: list[MontosMoneda] = []
    for moneda, umbral in umbrales.items():
        es_bancarizable = Expediente.importe_total >= umbral
        fila = session.execute(
            select(
                func.coalesce(func.sum(case((es_bancarizable, Expediente.importe_total))), 0),
                func.coalesce(func.sum(case((~es_bancarizable, Expediente.importe_total))), 0),
            ).where(*vigentes, Expediente.moneda == moneda)
        ).one()
        montos.append(
            MontosMoneda(
                moneda=moneda, bancarizable=Decimal(fila[0]), no_bancarizable=Decimal(fila[1])
            )
        )

    alertas = {t: 0 for t in TipoAlerta}
    for tipo, total in session.execute(
        select(Alerta.tipo, func.count())
        .where(Alerta.tenant_id == tenant_id, Alerta.resuelta.is_(False))
        .group_by(Alerta.tipo)
    ):
        alertas[TipoAlerta(tipo)] = total

    pendientes = {
        EstadoDocumento.PENDIENTE_CLASIFICACION: 0,
        EstadoDocumento.PENDIENTE_RELACION: 0,
    }
    for estado, total in session.execute(
        select(Documento.estado, func.count())
        .where(
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
            Documento.estado.in_(list(pendientes)),
        )
        .group_by(Documento.estado)
    ):
        pendientes[EstadoDocumento(estado)] = total

    return DashboardResumen(
        expedientes_total=sum(por_estado.values()),
        por_estado=por_estado,
        pendientes_aprobacion=pendientes_aprobacion,
        montos=montos,
        alertas_abiertas=alertas,
        documentos_pendientes=pendientes,
    )
