import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter
from sqlalchemy import case, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import SessionDep, SettingsDep, TenantDep
from app.enums import EstadoDocumento, EstadoExpediente, Moneda, TipoAlerta
from app.models import Alerta, Documento, Expediente, Miembro
from app.schemas import DashboardDesglose, DashboardDesgloseFila, DashboardResumen, MontosMoneda

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


@router.get("/desglose", response_model=DashboardDesglose)
def desglose(
    session: SessionDep,
    tenant_id: TenantDep,
    agrupar_por: Literal["usuario", "emisor", "receptor", "dia", "mes", "anio"] = "usuario",
    orden: Literal["asc", "desc"] = "desc",
    usuario_id: uuid.UUID | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> DashboardDesglose:
    consulta = (
        select(Expediente)
        .options(
            selectinload(Expediente.emisor),
            selectinload(Expediente.receptor),
        )
        .where(
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
        )
    )
    if usuario_id is not None:
        consulta = consulta.where(Expediente.usuario_id == usuario_id)
    if emisor_id is not None:
        consulta = consulta.where(Expediente.emisor_id == emisor_id)
    if receptor_id is not None:
        consulta = consulta.where(Expediente.receptor_id == receptor_id)
    if fecha_desde is not None:
        consulta = consulta.where(Expediente.fecha_emision >= fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.where(Expediente.fecha_emision <= fecha_hasta)

    expedientes = list(session.scalars(consulta))
    usuarios = {
        miembro.id: miembro
        for miembro in session.scalars(
            select(Miembro).where(
                Miembro.tenant_id == tenant_id,
                Miembro.deleted_at.is_(None),
            )
        )
    }

    acumulado: dict[str, DashboardDesgloseFila] = {}
    for expediente in expedientes:
        if agrupar_por == "usuario":
            miembro = (
                usuarios.get(expediente.usuario_id)
                if expediente.usuario_id is not None
                else None
            )
            clave = str(expediente.usuario_id or "sin-usuario")
            etiqueta = (
                f"{miembro.codigo} · {miembro.nombre}"
                if miembro is not None
                else "Sin usuario asignado"
            )
            ruc = None
        elif agrupar_por == "emisor":
            clave = str(expediente.emisor_id)
            etiqueta = expediente.emisor.razon_social
            ruc = expediente.emisor.ruc
        elif agrupar_por == "receptor":
            clave = str(expediente.receptor_id)
            etiqueta = expediente.receptor.razon_social
            ruc = expediente.receptor.ruc
        else:
            fecha = expediente.fecha_emision
            if agrupar_por == "dia":
                clave = fecha.isoformat()
                etiqueta = fecha.strftime("%d/%m/%Y")
            elif agrupar_por == "mes":
                clave = fecha.strftime("%Y-%m")
                etiqueta = fecha.strftime("%m/%Y")
            else:
                clave = str(fecha.year)
                etiqueta = str(fecha.year)
            ruc = None

        fila = acumulado.get(clave)
        if fila is None:
            fila = DashboardDesgloseFila(
                clave=clave,
                etiqueta=etiqueta,
                ruc=ruc,
                expedientes=0,
                total_pen=Decimal("0"),
                total_usd=Decimal("0"),
            )
            acumulado[clave] = fila
        fila.expedientes += 1
        if expediente.moneda == Moneda.PEN:
            fila.total_pen += expediente.importe_total
        elif expediente.moneda == Moneda.USD:
            fila.total_usd += expediente.importe_total

    filas = list(acumulado.values())
    if agrupar_por in {"dia", "mes", "anio"}:
        filas.sort(key=lambda fila: fila.clave, reverse=orden == "desc")
    else:
        filas.sort(
            key=lambda fila: (fila.expedientes, fila.etiqueta.casefold()),
            reverse=orden == "desc",
        )
    return DashboardDesglose(agrupar_por=agrupar_por, filas=filas)
