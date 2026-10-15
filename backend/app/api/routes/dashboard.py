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
from app.services.ambito_gerencia import alcance_expedientes_gerente
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
    empresa_emisora: str | None = None,
    empresa_receptora: str | None = None,
    estado: EstadoExpediente | None = None,
    correlativo: str | None = None,
    monto_desde: Decimal | None = None,
    monto_hasta: Decimal | None = None,
    guia_remitente: str | None = None,
    responsable_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
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
    if responsable_id is not None:
        responsables_usuarios = select(Miembro.id).where(
            Miembro.tenant_id == tenant_id,
            Miembro.rol == RolMiembro.USUARIO,
            Miembro.responsable_id == responsable_id,
        )
        consulta = consulta.where(Expediente.usuario_id.in_(responsables_usuarios))
    if usuario_id is not None:
        consulta = consulta.where(Expediente.usuario_id == usuario_id)
    if gestor_id is not None:
        consulta = consulta.where(Expediente.gestor_id == gestor_id)
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
    if empresa_emisora and empresa_emisora.strip():
        proveedor = aliased(Empresa)
        termino = empresa_emisora.strip().lower()
        consulta = consulta.join(proveedor, Expediente.emisor_id == proveedor.id).where(
            proveedor.tenant_id == tenant_id,
            (func.lower(proveedor.razon_social).contains(termino, autoescape=True))
            | (proveedor.ruc.contains(termino, autoescape=True)),
        )
    if empresa_receptora and empresa_receptora.strip():
        cliente = aliased(Empresa)
        termino = empresa_receptora.strip().lower()
        consulta = consulta.join(cliente, Expediente.receptor_id == cliente.id).where(
            cliente.tenant_id == tenant_id,
            (func.lower(cliente.razon_social).contains(termino, autoescape=True))
            | (cliente.ruc.contains(termino, autoescape=True)),
        )
    if estado is not None:
        consulta = consulta.where(Expediente.estado == estado)
    if correlativo:
        termino = correlativo.strip().lower()
        if termino:
            consulta = consulta.where(
                func.lower(Expediente.serie + "-" + Expediente.correlativo).contains(termino)
                | func.lower(Expediente.correlativo).contains(termino)
            )
    if monto_desde is not None:
        consulta = consulta.where(Expediente.importe_total >= monto_desde)
    if monto_hasta is not None:
        consulta = consulta.where(Expediente.importe_total <= monto_hasta)
    if guia_remitente:
        guia = guia_remitente.strip().lower()
        if guia:
            consulta = consulta.where(
                select(Documento.id)
                .where(
                    Documento.expediente_id == Expediente.id,
                    Documento.tenant_id == tenant_id,
                    Documento.deleted_at.is_(None),
                    func.lower(Documento.nombre_original).contains(guia),
                )
                .exists()
            )
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
        responsable = (
            usuarios.get(usuario.responsable_id)
            if usuario is not None and usuario.responsable_id is not None
            else None
        )
        faltantes = [tipo.value for tipo in documentos_faltantes(e, settings)]
        fechas_carga = [doc.created_at for doc in e.documentos if doc.deleted_at is None]
        primera_carga = min(fechas_carga) if fechas_carga else None
        filas.append(
            {
                "id": str(e.id),
                "serie": e.serie,
                "correlativo": e.correlativo,
                "tipo_comprobante": e.tipo_comprobante,
                "fecha_emision": e.fecha_emision.isoformat(),
                "fecha_registro": e.created_at.isoformat(),
                "fecha_carga": primera_carga.isoformat() if primera_carga else None,
                "moneda": e.moneda,
                "importe_total": str(e.importe_total),
                "estado": e.estado,
                "emisor": e.emisor.razon_social,
                "emisor_ruc": e.emisor.ruc,
                "receptor": e.receptor.razon_social,
                "receptor_ruc": e.receptor.ruc,
                "responsable": responsable.nombre if responsable else "Sin asignar",
                "responsable_codigo": responsable.codigo if responsable else "",
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
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso exclusivo de Secretaría")
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


def _alcance_dashboard(
    tenant_id: uuid.UUID,
    auth: OperativeAuthDep,
    responsable_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    mes: str | None = None,
) -> list[ColumnElement[bool]]:
    """Una única fuente de alcance para resumen, desglose y opciones."""
    from fastapi import HTTPException, status

    condiciones: list[ColumnElement[bool]] = [
        Expediente.tenant_id == tenant_id,
        Expediente.deleted_at.is_(None),
    ]
    if auth.rol == "GESTOR":
        condiciones.append(Expediente.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        condiciones.append(Expediente.usuario_id == auth.usuario_id)
    elif auth.rol == RolMiembro.RESPONSABLE:
        condiciones.append(
            Expediente.usuario_id.in_(
                select(Miembro.id).where(
                    Miembro.tenant_id == tenant_id,
                    Miembro.responsable_id == auth.miembro_id,
                    Miembro.deleted_at.is_(None),
                )
            )
        )
    elif auth.rol == RolMiembro.GERENTE:
        condiciones.append(alcance_expedientes_gerente(auth))
    if responsable_id is not None:
        condiciones.append(
            Expediente.usuario_id.in_(
                select(Miembro.id).where(
                    Miembro.tenant_id == tenant_id,
                    Miembro.responsable_id == responsable_id,
                    Miembro.deleted_at.is_(None),
                )
            )
        )
    if usuario_id is not None:
        condiciones.append(Expediente.usuario_id == usuario_id)
    if gestor_id is not None:
        condiciones.append(Expediente.gestor_id == gestor_id)
    if emisor_id is not None:
        condiciones.append(Expediente.emisor_id == emisor_id)
    if receptor_id is not None:
        condiciones.append(Expediente.receptor_id == receptor_id)
    if tipo_empresa is not None:
        condiciones.append(Expediente.emisor.has(Empresa.clasificacion_proveedor == tipo_empresa))
    if fecha_desde is not None:
        condiciones.append(Expediente.fecha_emision >= fecha_desde)
    if fecha_hasta is not None:
        condiciones.append(Expediente.fecha_emision <= fecha_hasta)
    if mes:
        try:
            inicio = date.fromisoformat(f"{mes}-01")
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Mes inválido") from exc
        if len(mes) != 7 or mes[4] != "-":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Mes inválido")
        siguiente = date(inicio.year + (inicio.month == 12), inicio.month % 12 + 1, 1)
        condiciones.extend(
            (Expediente.fecha_emision >= inicio, Expediente.fecha_emision < siguiente)
        )
    return condiciones


@router.get("/opciones")
def opciones_dashboard(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    responsable_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    mes: str | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Opciones exclusivas de expedientes accesibles bajo los mismos filtros."""
    condiciones = _alcance_dashboard(
        tenant_id,
        auth,
        responsable_id,
        usuario_id,
        gestor_id,
        emisor_id,
        receptor_id,
        tipo_empresa,
        fecha_desde,
        fecha_hasta,
        mes,
    )
    expedientes = session.scalars(select(Expediente).where(*condiciones)).all()
    usuarios_ids = {e.usuario_id for e in expedientes if e.usuario_id}
    gestores_ids = {e.gestor_id for e in expedientes if e.gestor_id}
    emisores_ids = {e.emisor_id for e in expedientes}
    receptores_ids = {e.receptor_id for e in expedientes}
    usuarios = list(
        session.scalars(
            select(Miembro).where(
                Miembro.tenant_id == tenant_id,
                Miembro.id.in_(usuarios_ids),
                Miembro.deleted_at.is_(None),
            )
        )
    )
    responsables_ids = {u.responsable_id for u in usuarios if u.responsable_id}
    responsables = session.scalars(
        select(Miembro).where(
            Miembro.tenant_id == tenant_id,
            Miembro.id.in_(responsables_ids),
            Miembro.deleted_at.is_(None),
        )
    ).all()
    gestores = session.scalars(
        select(Gestor).where(
            Gestor.tenant_id == tenant_id,
            Gestor.id.in_(gestores_ids),
            Gestor.deleted_at.is_(None),
        )
    ).all()
    empresas = session.scalars(
        select(Empresa).where(
            Empresa.tenant_id == tenant_id,
            Empresa.id.in_(emisores_ids | receptores_ids),
        )
    ).all()

    def miembros_opciones(items: list[Miembro]) -> list[dict[str, str]]:
        return sorted(
            [{"id": str(x.id), "nombre": f"{x.codigo} · {x.nombre}"} for x in items],
            key=lambda x: x["nombre"],
        )

    def empresas_opciones(ids: set[uuid.UUID]) -> list[dict[str, str]]:
        return sorted(
            [
                {"id": str(x.id), "nombre": f"{x.razon_social} · {x.ruc}"}
                for x in empresas
                if x.id in ids
            ],
            key=lambda x: x["nombre"],
        )

    return {
        "responsables": miembros_opciones(list(responsables)),
        "usuarios": miembros_opciones(usuarios),
        "gestores": sorted(
            [{"id": str(x.id), "nombre": f"{x.codigo} · {x.nombre}"} for x in gestores],
            key=lambda x: x["nombre"],
        ),
        "emisores": empresas_opciones(emisores_ids),
        "receptores": empresas_opciones(receptores_ids),
    }


@router.get("/resumen", response_model=DashboardResumen)
def resumen(
    session: SessionDep,
    settings: SettingsDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    responsable_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    mes: str | None = None,
) -> DashboardResumen:
    vigentes = _alcance_dashboard(
        tenant_id,
        auth,
        responsable_id,
        usuario_id,
        gestor_id,
        emisor_id,
        receptor_id,
        tipo_empresa,
        fecha_desde,
        fecha_hasta,
        mes,
    )

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
    # Los pendientes sin expediente no poseen emisor/receptor ni fecha de emisión
    # verificables: no atribuirlos a filtros de expedientes.
    if emisor_id or receptor_id or tipo_empresa or mes or fecha_desde or fecha_hasta:
        documentos_scope.append(Documento.id.is_(None))
    if responsable_id is not None:
        documentos_scope.append(
            Documento.usuario_id.in_(
                select(Miembro.id).where(
                    Miembro.tenant_id == tenant_id,
                    Miembro.responsable_id == responsable_id,
                    Miembro.deleted_at.is_(None),
                )
            )
        )
    if usuario_id is not None:
        documentos_scope.append(Documento.usuario_id == usuario_id)
    if gestor_id is not None:
        documentos_scope.append(Documento.gestor_id == gestor_id)
    if auth.rol == RolMiembro.RESPONSABLE:
        documentos_scope.append(
            Documento.usuario_id.in_(
                select(Miembro.id).where(
                    Miembro.tenant_id == tenant_id,
                    Miembro.responsable_id == auth.miembro_id,
                    Miembro.deleted_at.is_(None),
                )
            )
        )
    if auth.rol == "GESTOR":
        documentos_scope.append(Documento.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        documentos_scope.append(Documento.usuario_id == auth.usuario_id)
    elif auth.rol == RolMiembro.GERENTE:
        documentos_scope.append(
            Documento.expediente_id.in_(
                select(Expediente.id).where(
                    Expediente.tenant_id == tenant_id,
                    alcance_expedientes_gerente(auth),
                    Expediente.deleted_at.is_(None),
                )
            )
        )
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
    agrupar_por: Literal[
        "responsable",
        "usuario",
        "gestor",
        "emisor",
        "receptor",
        "tipo_empresa",
        "dia",
        "mes",
        "anio",
    ] = "usuario",
    orden: Literal["asc", "desc"] = "desc",
    responsable_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    mes: str | None = None,
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
    consulta = consulta.where(
        *_alcance_dashboard(
            tenant_id,
            auth,
            responsable_id,
            usuario_id,
            gestor_id,
            emisor_id,
            receptor_id,
            tipo_empresa,
            fecha_desde,
            fecha_hasta,
            mes,
        )
    )

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

    gestores = {
        gestor.id: gestor
        for gestor in session.scalars(
            select(Gestor).where(
                Gestor.tenant_id == tenant_id,
                Gestor.deleted_at.is_(None),
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
        elif agrupar_por == "responsable":
            miembro_usuario = usuarios.get(expediente.usuario_id) if expediente.usuario_id else None
            responsable = (
                usuarios.get(miembro_usuario.responsable_id)
                if miembro_usuario and miembro_usuario.responsable_id
                else None
            )
            clave = str(responsable.id) if responsable else "sin-responsable"
            etiqueta = (
                f"{responsable.codigo} · {responsable.nombre}"
                if responsable
                else "Sin responsable asignado"
            )
            ruc = None
        elif agrupar_por == "gestor":
            gestor = gestores.get(expediente.gestor_id) if expediente.gestor_id else None
            clave = str(expediente.gestor_id or "sin-gestor")
            etiqueta = (
                f"{gestor.codigo} · {gestor.nombre}"
                if gestor
                else "Sin gestor asignado"
            )
            ruc = None
        elif agrupar_por == "tipo_empresa":
            tipo = expediente.emisor.clasificacion_proveedor
            clave = str(tipo or "sin-clasificar")
            etiqueta = f"Tipo {tipo}" if tipo else "Sin clasificación"
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
