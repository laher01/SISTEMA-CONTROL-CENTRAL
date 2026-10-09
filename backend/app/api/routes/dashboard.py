import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter
from sqlalchemy import case, func, select
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.api.deps import OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.enums import EstadoDocumento, EstadoExpediente, Moneda, RolMiembro, TipoAlerta
from app.models import Alerta, Documento, Empresa, Expediente, Gestor, Miembro
from app.schemas import DashboardDesglose, DashboardDesgloseFila, DashboardResumen, MontosMoneda
from app.services.expedientes import documentos_faltantes

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/secretaria-expedientes")
def detalle_secretaria(
    session: SessionDep,
    settings: SettingsDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    desde: date,
    hasta: date,
    emisor_ruc: str | None = None,
    receptor_ruc: str | None = None,
    estado: EstadoExpediente | None = None,
) -> dict[str, object]:
    """Consulta transversal de Secretaría sin exponer pagos ni comisiones."""
    from fastapi import HTTPException, status

    if auth.rol not in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.SECRETARIA,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso exclusivo de Secretaría")
    if hasta < desde:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Periodo inválido")

    consulta = (
        select(Expediente)
        .options(
            selectinload(Expediente.emisor),
            selectinload(Expediente.receptor),
            selectinload(Expediente.documentos),
        )
        .where(
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
            Expediente.fecha_emision >= desde,
            Expediente.fecha_emision <= hasta,
        )
        .order_by(Expediente.fecha_emision.desc(), Expediente.id)
    )
    if emisor_ruc:
        emisor_empresa = aliased(Empresa)
        consulta = consulta.join(emisor_empresa, Expediente.emisor_id == emisor_empresa.id).where(
            emisor_empresa.ruc == emisor_ruc
        )
    if receptor_ruc:
        receptor_empresa = aliased(Empresa)
        consulta = consulta.join(
            receptor_empresa, Expediente.receptor_id == receptor_empresa.id
        ).where(receptor_empresa.ruc == receptor_ruc)
    if estado is not None:
        consulta = consulta.where(Expediente.estado == estado)
    expedientes = list(session.scalars(consulta))
    usuarios = {
        item.id: item
        for item in session.scalars(
            select(Miembro).where(Miembro.tenant_id == tenant_id, Miembro.deleted_at.is_(None))
        )
    }
    gestores = {
        item.id: item
        for item in session.scalars(
            select(Gestor).where(Gestor.tenant_id == tenant_id, Gestor.deleted_at.is_(None))
        )
    }
    totales = {"PEN": Decimal("0"), "USD": Decimal("0")}
    filas: list[dict[str, object]] = []
    for e in expedientes:
        totales[e.moneda] = totales.get(e.moneda, Decimal("0")) + e.importe_total
        usuario = usuarios.get(e.usuario_id) if e.usuario_id is not None else None
        gestor = gestores.get(e.gestor_id) if e.gestor_id is not None else None
        faltantes = [tipo.value for tipo in documentos_faltantes(e, settings)]
        filas.append(
            {
                "id": str(e.id),
                "serie": e.serie,
                "correlativo": e.correlativo,
                "tipo_comprobante": e.tipo_comprobante,
                "fecha_emision": e.fecha_emision.isoformat(),
                "moneda": e.moneda,
                "importe_total": str(e.importe_total),
                "estado": e.estado,
                "emisor": e.emisor.razon_social,
                "emisor_ruc": e.emisor.ruc,
                "receptor": e.receptor.razon_social,
                "receptor_ruc": e.receptor.ruc,
                "usuario": usuario.nombre if usuario else "Sin asignar",
                "usuario_codigo": usuario.codigo if usuario else "",
                "gestor": gestor.nombre if gestor else "Sin asignar",
                "gestor_codigo": gestor.codigo if gestor else "",
                "faltantes": faltantes,
                "documentos": sum(d.deleted_at is None for d in e.documentos),
            }
        )
    return {
        "total_expedientes": len(filas),
        "total_pen": str(totales["PEN"]),
        "total_usd": str(totales["USD"]),
        "filas": filas,
    }


@router.get("/secretaria-clientes")
def resumen_secretaria_clientes(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    desde: date,
    hasta: date,
) -> list[dict[str, str | int]]:
    """Producción transversal por receptor sin exponer liquidaciones."""
    from fastapi import HTTPException, status

    if auth.rol not in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.SECRETARIA,
        RolMiembro.GERENTE,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso exclusivo de Secretaría y Gerencia")
    if hasta < desde:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Periodo inválido")
    consulta = (
        select(
            Empresa.ruc,
            Empresa.razon_social,
            Expediente.moneda,
            func.count(Expediente.id),
            func.coalesce(func.sum(Expediente.importe_total), 0),
        )
        .join(Empresa, Expediente.receptor_id == Empresa.id)
        .where(
            Expediente.tenant_id == tenant_id,
            Empresa.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
            Expediente.fecha_emision >= desde,
            Expediente.fecha_emision <= hasta,
        )
        .group_by(Empresa.ruc, Empresa.razon_social, Expediente.moneda)
        .order_by(Empresa.razon_social, Expediente.moneda)
    )
    return [
        {
            "receptor_ruc": ruc,
            "receptor": nombre,
            "moneda": moneda,
            "expedientes": cantidad,
            "total": str(importe),
        }
        for ruc, nombre, moneda, cantidad, importe in session.execute(consulta)
    ]


@router.get("/resumen", response_model=DashboardResumen)
def resumen(
    session: SessionDep,
    settings: SettingsDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> DashboardResumen:
    vigentes: list[ColumnElement[bool]] = [
        Expediente.tenant_id == tenant_id,
        Expediente.deleted_at.is_(None),
    ]
    if auth.rol == "GESTOR":
        vigentes.append(Expediente.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        vigentes.append(Expediente.usuario_id == auth.usuario_id)

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
    alertas_query = (
        select(Alerta.tipo, func.count())
        .join(Expediente, Alerta.expediente_id == Expediente.id)
        .where(Alerta.tenant_id == tenant_id, Alerta.resuelta.is_(False), *vigentes)
        .group_by(Alerta.tipo)
    )
    for tipo, total in session.execute(alertas_query):
        alertas[TipoAlerta(tipo)] = total

    pendientes = {
        EstadoDocumento.PENDIENTE_CLASIFICACION: 0,
        EstadoDocumento.PENDIENTE_RELACION: 0,
    }
    documentos_scope: list[ColumnElement[bool]] = [
        Documento.tenant_id == tenant_id,
        Documento.deleted_at.is_(None),
        Documento.estado.in_(list(pendientes)),
    ]
    if auth.rol == "GESTOR":
        documentos_scope.append(Documento.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        documentos_scope.append(Documento.usuario_id == auth.usuario_id)
    for estado, total in session.execute(
        select(Documento.estado, func.count()).where(*documentos_scope).group_by(Documento.estado)
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
    auth: OperativeAuthDep,
    agrupar_por: Literal["usuario", "emisor", "receptor", "dia", "mes", "anio"] = "usuario",
    orden: Literal["asc", "desc"] = "desc",
    usuario_id: uuid.UUID | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
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
    if auth.rol == "GESTOR":
        consulta = consulta.where(Expediente.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        consulta = consulta.where(Expediente.usuario_id == auth.usuario_id)
    elif usuario_id is not None:
        consulta = consulta.where(Expediente.usuario_id == usuario_id)
    if emisor_id is not None:
        consulta = consulta.where(Expediente.emisor_id == emisor_id)
    if receptor_id is not None:
        consulta = consulta.where(Expediente.receptor_id == receptor_id)
    if tipo_empresa is not None:
        consulta = consulta.where(
            Expediente.emisor.has(Empresa.clasificacion_proveedor == tipo_empresa)
        )
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
            miembro = None
            if expediente.usuario_id is not None:
                miembro = usuarios.get(expediente.usuario_id)
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
