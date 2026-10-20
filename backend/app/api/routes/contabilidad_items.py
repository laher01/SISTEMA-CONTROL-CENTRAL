"""Consultas de solo lectura: Contabilidad de Ítems, aislada por tenant."""

import csv
import io
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, select, true
from sqlalchemy.sql.elements import ColumnElement

from app.api.deps import OperativeAuthDep, SessionDep
from app.item_models import AuditoriaFacturaItem, LineaComprobanteItem, ProductoItem
from app.models import Auditoria, Documento, Empresa, Expediente, Miembro
from app.services.ambito_gerencia import alcance_expedientes_gerente
from app.services.contabilidad_items_auditoria import registrar_decision, resolver_propuesta

router = APIRouter(prefix="/contabilidad-items", tags=["contabilidad-items"])


def _alcance(auth: OperativeAuthDep) -> ColumnElement[bool]:
    if auth.rol in ("ADMINISTRADOR", "SECRETARIA"):
        return true()
    if auth.rol == "GERENTE":
        return alcance_expedientes_gerente(auth)
    if auth.rol == "RESPONSABLE":
        if auth.miembro_id is None:
            raise HTTPException(403, "Responsable sin identidad asignada")
        usuarios_equipo = select(Miembro.id).where(
            Miembro.tenant_id == auth.tenant_id,
            Miembro.responsable_id == auth.miembro_id,
            Miembro.deleted_at.is_(None),
        )
        return Expediente.usuario_id.in_(usuarios_equipo)
    if auth.rol == "USUARIO":
        return Expediente.usuario_id == auth.usuario_id
    if auth.rol == "GESTOR":
        return Expediente.gestor_id == auth.gestor_id
    raise HTTPException(403, "Rol sin acceso al módulo")


class CategoriaItemIn(BaseModel):
    categoria: str = Field(min_length=2, max_length=80)


@router.post("/productos/{producto_id}/categoria")
def clasificar_producto(
    producto_id: uuid.UUID,
    datos: CategoriaItemIn,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    """La clasificación es metadato del catálogo, sin alterar originales ni liquidaciones."""
    if auth.rol != "ADMINISTRADOR":
        raise HTTPException(403, "Solo Administración puede clasificar el catálogo")
    categoria = datos.categoria.strip()
    if len(categoria) < 2:
        raise HTTPException(422, "Categoría insuficiente")
    producto = session.scalar(
        select(ProductoItem)
        .where(
            ProductoItem.id == producto_id,
            ProductoItem.tenant_id == auth.tenant_id,
            ProductoItem.activo.is_(True),
        )
        .with_for_update()
    )
    if producto is None:
        raise HTTPException(404, "Producto no encontrado")
    anterior = producto.categoria
    producto.categoria = categoria
    producto.clasificacion_confirmada = True
    session.add(
        Auditoria(
            tenant_id=auth.tenant_id,
            accion="ITEMS_CATEGORIA_CONFIRMADA",
            entidad="producto_item",
            entidad_id=producto.id,
            datos={"anterior": anterior, "nueva": categoria, "cuenta_id": str(auth.cuenta_id)},
        )
    )
    session.commit()
    return {"producto_id": str(producto.id), "categoria": categoria}


@router.get("/empresas-vinculadas")
def empresas_vinculadas(
    session: SessionDep,
    auth: OperativeAuthDep,
    tipo: Literal["proveedor", "cliente"],
    buscar: Annotated[str | None, Query(max_length=150)] = None,
    limite: int = Query(100, ge=1, le=200),
) -> list[dict[str, str]]:
    """Empresas que aparecen en líneas visibles; no expone cartera ajena."""
    empresa_id = Expediente.emisor_id if tipo == "proveedor" else Expediente.receptor_id
    ultimo_estado = (
        select(AuditoriaFacturaItem.estado)
        .where(
            AuditoriaFacturaItem.expediente_id == Expediente.id,
            AuditoriaFacturaItem.tenant_id == auth.tenant_id,
        )
        .order_by(AuditoriaFacturaItem.created_at.desc(), AuditoriaFacturaItem.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    stmt = (
        select(Empresa.id, Empresa.ruc, Empresa.razon_social)
        .join(Expediente, empresa_id == Empresa.id)
        .join(Documento, Documento.expediente_id == Expediente.id)
        .join(LineaComprobanteItem, LineaComprobanteItem.documento_id == Documento.id)
        .join(ProductoItem, ProductoItem.id == LineaComprobanteItem.producto_id)
        .where(
            Empresa.tenant_id == auth.tenant_id,
            Empresa.deleted_at.is_(None),
            Expediente.tenant_id == auth.tenant_id,
            Expediente.deleted_at.is_(None),
            Documento.tenant_id == auth.tenant_id,
            Documento.deleted_at.is_(None),
            LineaComprobanteItem.tenant_id == auth.tenant_id,
            ProductoItem.tenant_id == auth.tenant_id,
            ProductoItem.activo.is_(True),
            _alcance(auth),
            or_(
                ultimo_estado.is_(None),
                ultimo_estado.not_in(
                    [
                        "OBSERVADA",
                        "INVALIDADA_CONFIRMADA",
                        "INVALIDADA_PENDIENTE",
                        "REACTIVACION_PENDIENTE",
                    ]
                ),
            ),
        )
        .distinct()
        .order_by(Empresa.razon_social, Empresa.id)
        .limit(limite)
    )
    if buscar and buscar.strip():
        termino = f"%{buscar.strip()}%"
        stmt = stmt.where(or_(Empresa.ruc.ilike(termino), Empresa.razon_social.ilike(termino)))
    return [
        {"id": str(row.id), "ruc": row.ruc, "razon_social": row.razon_social}
        for row in session.execute(stmt)
    ]


@router.get("")
def resumen(
    session: SessionDep,
    auth: OperativeAuthDep,
    desde: date | None = None,
    hasta: date | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    limite: int = Query(100, ge=1, le=500),
    buscar: Annotated[str | None, Query(max_length=150)] = None,
    categoria: Annotated[str | None, Query(max_length=80)] = None,
) -> list[dict[str, str]]:
    """No mezcla unidades ni incluye facturas pendientes de auditoría."""
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(422, "La fecha inicial no puede ser posterior a la final")
    alcance = _alcance(auth)
    ultimo_estado = (
        select(AuditoriaFacturaItem.estado)
        .where(
            AuditoriaFacturaItem.expediente_id == Expediente.id,
            AuditoriaFacturaItem.tenant_id == auth.tenant_id,
        )
        .order_by(AuditoriaFacturaItem.created_at.desc(), AuditoriaFacturaItem.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    stmt = (
        select(
            ProductoItem.id,
            ProductoItem.categoria,
            ProductoItem.descripcion,
            LineaComprobanteItem.unidad,
            Expediente.moneda,
            func.sum(LineaComprobanteItem.cantidad).label("cantidad"),
            func.sum(LineaComprobanteItem.importe_linea).label("importe"),
        )
        .join(LineaComprobanteItem, LineaComprobanteItem.producto_id == ProductoItem.id)
        .join(Documento, Documento.id == LineaComprobanteItem.documento_id)
        .join(Expediente, Expediente.id == Documento.expediente_id)
        .where(
            ProductoItem.tenant_id == auth.tenant_id,
            LineaComprobanteItem.tenant_id == auth.tenant_id,
            Documento.tenant_id == auth.tenant_id,
            Expediente.tenant_id == auth.tenant_id,
            Documento.deleted_at.is_(None),
            Expediente.deleted_at.is_(None),
            ProductoItem.activo.is_(True),
            alcance,
            or_(
                ultimo_estado.is_(None),
                ultimo_estado.not_in(
                    [
                        "OBSERVADA",
                        "INVALIDADA_CONFIRMADA",
                        "INVALIDADA_PENDIENTE",
                        "REACTIVACION_PENDIENTE",
                    ]
                ),
            ),
        )
    )
    if buscar and buscar.strip():
        termino = f"%{buscar.strip()}%"
        stmt = stmt.where(
            or_(
                ProductoItem.descripcion.ilike(termino),
                LineaComprobanteItem.descripcion_original.ilike(termino),
            )
        )
    if categoria and categoria.strip():
        stmt = stmt.where(ProductoItem.categoria == categoria.strip())
    if desde:
        stmt = stmt.where(Expediente.fecha_emision >= desde)
    if hasta:
        stmt = stmt.where(Expediente.fecha_emision <= hasta)
    if emisor_id:
        stmt = stmt.where(Expediente.emisor_id == emisor_id)
    if receptor_id:
        stmt = stmt.where(Expediente.receptor_id == receptor_id)
    stmt = (
        stmt.group_by(
            ProductoItem.id,
            ProductoItem.categoria,
            ProductoItem.descripcion,
            LineaComprobanteItem.unidad,
            Expediente.moneda,
        )
        .order_by(ProductoItem.descripcion)
        .limit(limite)
    )
    return [
        {
            "producto_id": str(r.id),
            "categoria": r.categoria,
            "descripcion": r.descripcion,
            "unidad": r.unidad,
            "moneda": r.moneda,
            "cantidad": str(Decimal(r.cantidad)),
            "importe": str(Decimal(r.importe)) if r.importe is not None else "",
        }
        for r in session.execute(stmt)
    ]


@router.get("/productos/{producto_id}/facturas")
def facturas_por_producto(
    producto_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
    desde: date | None = None,
    hasta: date | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    limite: int = Query(100, ge=1, le=500),
) -> list[dict[str, str]]:
    """Documentos originales que contienen el producto; solo ámbito autorizado."""
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(422, "La fecha inicial no puede ser posterior a la final")
    producto = session.scalar(
        select(ProductoItem).where(
            ProductoItem.id == producto_id,
            ProductoItem.tenant_id == auth.tenant_id,
            ProductoItem.activo.is_(True),
        )
    )
    if producto is None:
        raise HTTPException(404, "Producto no encontrado")
    ultimo_estado = (
        select(AuditoriaFacturaItem.estado)
        .where(
            AuditoriaFacturaItem.expediente_id == Expediente.id,
            AuditoriaFacturaItem.tenant_id == auth.tenant_id,
        )
        .order_by(AuditoriaFacturaItem.created_at.desc(), AuditoriaFacturaItem.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    consulta = (
        select(
            Expediente.id.label("expediente_id"),
            Documento.id.label("documento_id"),
            Expediente.serie,
            Expediente.correlativo,
            Expediente.fecha_emision,
            Expediente.moneda,
            Expediente.emisor_id,
            Expediente.receptor_id,
            LineaComprobanteItem.numero_linea,
            LineaComprobanteItem.descripcion_original,
            LineaComprobanteItem.unidad,
            LineaComprobanteItem.cantidad,
            LineaComprobanteItem.importe_linea,
        )
        .join(Documento, Documento.id == LineaComprobanteItem.documento_id)
        .join(Expediente, Expediente.id == Documento.expediente_id)
        .where(
            LineaComprobanteItem.producto_id == producto_id,
            LineaComprobanteItem.tenant_id == auth.tenant_id,
            Documento.tenant_id == auth.tenant_id,
            Expediente.tenant_id == auth.tenant_id,
            Documento.deleted_at.is_(None),
            Expediente.deleted_at.is_(None),
            _alcance(auth),
            or_(
                ultimo_estado.is_(None),
                ultimo_estado.not_in(
                    [
                        "OBSERVADA",
                        "INVALIDADA_CONFIRMADA",
                        "INVALIDADA_PENDIENTE",
                        "REACTIVACION_PENDIENTE",
                    ]
                ),
            ),
        )
    )
    if desde is not None:
        consulta = consulta.where(Expediente.fecha_emision >= desde)
    if hasta is not None:
        consulta = consulta.where(Expediente.fecha_emision <= hasta)
    if emisor_id is not None:
        consulta = consulta.where(Expediente.emisor_id == emisor_id)
    if receptor_id is not None:
        consulta = consulta.where(Expediente.receptor_id == receptor_id)
    consulta = consulta.order_by(
        Expediente.fecha_emision.desc(),
        Expediente.id,
        LineaComprobanteItem.numero_linea,
    ).limit(limite)
    return [
        {
            "expediente_id": str(fila.expediente_id),
            "documento_id": str(fila.documento_id),
            "comprobante": f"{fila.serie}-{fila.correlativo}",
            "fecha_emision": str(fila.fecha_emision),
            "moneda": fila.moneda,
            "emisor_id": str(fila.emisor_id),
            "receptor_id": str(fila.receptor_id),
            "numero_linea": str(fila.numero_linea),
            "descripcion_original": fila.descripcion_original,
            "unidad": fila.unidad,
            "cantidad": str(fila.cantidad),
            "importe": str(fila.importe_linea) if fila.importe_linea is not None else "",
        }
        for fila in session.execute(consulta)
    ]


@router.get("/conciliacion")
def conciliacion(
    session: SessionDep,
    auth: OperativeAuthDep,
    desde: date | None = None,
    hasta: date | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
) -> list[dict[str, str | int]]:
    """Control de importes de expedientes, sin duplicar por documentos o líneas."""
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(422, "La fecha inicial no puede ser posterior a la final")
    ultimo_estado = (
        select(AuditoriaFacturaItem.estado)
        .where(
            AuditoriaFacturaItem.expediente_id == Expediente.id,
            AuditoriaFacturaItem.tenant_id == auth.tenant_id,
        )
        .order_by(AuditoriaFacturaItem.created_at.desc(), AuditoriaFacturaItem.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    estado = func.coalesce(ultimo_estado, "VIGENTE")
    aprobado = estado == "VIGENTE"
    observado = estado == "OBSERVADA"
    otra = estado.not_in(("VIGENTE", "OBSERVADA"))
    consulta = (
        select(
            Expediente.moneda,
            func.count(Expediente.id).label("total_documentos"),
            func.coalesce(func.sum(Expediente.importe_total), 0).label("total"),
            func.sum(case((aprobado, 1), else_=0)).label("aprobados"),
            func.coalesce(func.sum(case((aprobado, Expediente.importe_total), else_=0)), 0).label(
                "importe_aprobado"
            ),
            func.sum(case((observado, 1), else_=0)).label("observados"),
            func.coalesce(func.sum(case((observado, Expediente.importe_total), else_=0)), 0).label(
                "importe_observado"
            ),
            func.sum(case((otra, 1), else_=0)).label("otros"),
            func.coalesce(func.sum(case((otra, Expediente.importe_total), else_=0)), 0).label(
                "importe_otros"
            ),
        )
        .where(
            Expediente.tenant_id == auth.tenant_id,
            Expediente.deleted_at.is_(None),
            _alcance(auth),
        )
        .group_by(Expediente.moneda)
        .order_by(Expediente.moneda)
    )
    if desde is not None:
        consulta = consulta.where(Expediente.fecha_emision >= desde)
    if hasta is not None:
        consulta = consulta.where(Expediente.fecha_emision <= hasta)
    if emisor_id is not None:
        consulta = consulta.where(Expediente.emisor_id == emisor_id)
    if receptor_id is not None:
        consulta = consulta.where(Expediente.receptor_id == receptor_id)
    return [
        {
            "moneda": fila.moneda,
            "total_documentos": fila.total_documentos,
            "importe_total": str(fila.total),
            "aprobados": fila.aprobados,
            "importe_aprobado": str(fila.importe_aprobado),
            "observados": fila.observados,
            "importe_observado": str(fila.importe_observado),
            "otros": fila.otros,
            "importe_otros": str(fila.importe_otros),
        }
        for fila in session.execute(consulta)
    ]


@router.get("/expedientes/{expediente_id}/detalle")
def detalle_expediente(
    expediente_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    """Detalle de líneas por expediente con alcance jerárquico y aislamiento de tenant."""
    expediente = session.scalar(
        select(Expediente).where(
            Expediente.id == expediente_id,
            Expediente.tenant_id == auth.tenant_id,
            Expediente.deleted_at.is_(None),
            _alcance(auth),
        )
    )
    if expediente is None:
        raise HTTPException(404, "Expediente no encontrado o fuera de alcance")
    estado = (
        session.scalar(
            select(AuditoriaFacturaItem.estado)
            .where(
                AuditoriaFacturaItem.tenant_id == auth.tenant_id,
                AuditoriaFacturaItem.expediente_id == expediente_id,
            )
            .order_by(AuditoriaFacturaItem.created_at.desc(), AuditoriaFacturaItem.id.desc())
            .limit(1)
        )
        or "VIGENTE"
    )
    consulta = (
        select(LineaComprobanteItem, Documento, ProductoItem)
        .join(
            Documento,
            (Documento.id == LineaComprobanteItem.documento_id)
            & (Documento.tenant_id == auth.tenant_id)
            & (Documento.deleted_at.is_(None)),
        )
        .join(
            ProductoItem,
            (ProductoItem.id == LineaComprobanteItem.producto_id)
            & (ProductoItem.tenant_id == auth.tenant_id),
        )
        .where(
            LineaComprobanteItem.tenant_id == auth.tenant_id,
            Documento.expediente_id == expediente_id,
        )
        .order_by(Documento.created_at, Documento.id, LineaComprobanteItem.numero_linea)
    )
    lineas = []
    for linea, documento, producto in session.execute(consulta):
        lineas.append(
            {
                "documento_id": str(documento.id),
                "formato_origen": documento.formato_origen or "",
                "numero_linea": linea.numero_linea,
                "producto_id": str(producto.id),
                "categoria": producto.categoria,
                "descripcion": linea.descripcion_original,
                "unidad": linea.unidad,
                "cantidad": str(linea.cantidad),
                "importe": str(linea.importe_linea) if linea.importe_linea is not None else "",
            }
        )
    return {
        "expediente_id": str(expediente.id),
        "moneda": expediente.moneda,
        "estado_auditoria": estado,
        "lineas": lineas,
    }


class DecisionItemsIn(BaseModel):
    accion: Literal["OBSERVAR", "DESACTIVAR", "REACTIVAR"]
    motivo: str = Field(min_length=3, max_length=1000)


@router.post("/expedientes/{expediente_id}/auditar")
def auditar_factura(
    expediente_id: uuid.UUID,
    datos: DecisionItemsIn,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    decision = registrar_decision(session, auth, expediente_id, datos.accion, datos.motivo)
    session.commit()
    return {"decision_id": str(decision.id), "estado": decision.estado}


@router.post("/auditorias/{decision_id}/resolver")
def resolver_auditoria(
    decision_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
    aprobar: bool = True,
) -> dict[str, str]:
    decision = resolver_propuesta(session, auth, decision_id, aprobar)
    session.commit()
    return {"decision_id": str(decision.id), "estado": decision.estado}


def _celda_csv(valor: str) -> str:
    """Evita que un nombre de producto se ejecute como fórmula al abrir CSV en Excel."""
    if valor.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + valor
    return valor


@router.get("/exportar-csv")
def exportar_csv(
    session: SessionDep,
    auth: OperativeAuthDep,
    desde: date | None = None,
    hasta: date | None = None,
    emisor_id: uuid.UUID | None = None,
    receptor_id: uuid.UUID | None = None,
    buscar: Annotated[str | None, Query(max_length=150)] = None,
    categoria: Annotated[str | None, Query(max_length=80)] = None,
) -> Response:
    """Exportación de acumulados autorizados; no expone comprobantes ajenos al tenant."""
    filas = resumen(
        session=session,
        auth=auth,
        desde=desde,
        hasta=hasta,
        emisor_id=emisor_id,
        receptor_id=receptor_id,
        limite=501,
        buscar=buscar,
        categoria=categoria,
    )
    if len(filas) > 500:
        raise HTTPException(413, "La exportación supera 500 grupos; reduzca el período")
    archivo = io.StringIO()
    escritor = csv.writer(archivo)
    escritor.writerow(["categoria", "producto", "unidad", "moneda", "cantidad", "importe"])
    for fila in filas:
        escritor.writerow(
            [
                _celda_csv(fila["categoria"]),
                _celda_csv(fila["descripcion"]),
                _celda_csv(fila["unidad"]),
                _celda_csv(fila["moneda"]),
                fila["cantidad"],
                fila["importe"],
            ]
        )
    return Response(
        content="\ufeff" + archivo.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="contabilidad-items.csv"'},
    )
