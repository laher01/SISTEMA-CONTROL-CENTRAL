import json
import re
import tempfile
import uuid
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from starlette.background import BackgroundTask

from app.api.deps import AlmacenDep, HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.api.errores import no_encontrado
from app.enums import EstadoExpediente, RolMiembro
from app.models import Documento, Empresa, Expediente, ahora
from app.schemas import (
    ExpedienteDetalle,
    ExpedienteIn,
    ExpedienteOut,
    ImpresionExpedientesIn,
    Recalculo,
)
from app.security import cuenta_administradora_responsable
from app.services import auditoria
from app.services.ambito_gerencia import alcance_expedientes_gerente, expediente_visible_gerente
from app.services.expedientes import (
    buscar_expediente,
    documentos_faltantes,
    fecha_limite,
    recalcular_expedientes,
)
from app.services.ingesta import crear_expediente
from app.services.pdf_consolidado import pdf_con_documentos
from app.services.permisos import PERMISO_ELIMINAR_REGISTROS, permiso_habilitado

NUMERO_RE = re.compile(r"^([a-z0-9]{4})-0*(\d+)$")
NUMERO_RHE_RE = re.compile(r"^rhe-([a-z0-9]{4})-0*(\d+)$")

router = APIRouter(prefix="/expedientes", tags=["expedientes"])


@router.post("", response_model=ExpedienteOut, status_code=status.HTTP_201_CREATED)
def crear(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: ExpedienteIn,
) -> Expediente:
    if auth.rol == "GESTOR":
        gestor_id = auth.gestor_id
        usuario_id = auth.usuario_id
    elif auth.rol == RolMiembro.USUARIO:
        gestor_id = None
        usuario_id = auth.usuario_id
    else:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo un Usuario o Gestor puede crear expedientes operativos",
        )
    existente = buscar_expediente(
        session,
        tenant_id,
        datos.tipo_comprobante,
        datos.serie,
        str(int(datos.correlativo)),
        datos.emisor.ruc,
        datos.receptor.ruc,
    )
    if existente is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"mensaje": "El expediente ya existe", "expediente_id": str(existente.id)},
        )
    try:
        expediente = crear_expediente(
            session,
            settings,
            hoy,
            tenant_id,
            receptor=(datos.receptor.ruc, datos.receptor.razon_social),
            emisor=(datos.emisor.ruc, datos.emisor.razon_social),
            tipo_comprobante=datos.tipo_comprobante,
            serie=datos.serie,
            correlativo=datos.correlativo,
            fecha_emision=datos.fecha_emision,
            moneda=datos.moneda,
            importe_total=datos.importe_total,
            requiere_guia=datos.requiere_guia,
            gestor_id=gestor_id,
            usuario_id=usuario_id,
            creado_por_cuenta_id=cuenta_administradora_responsable(session, auth),
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El expediente ya existe") from exc
    return expediente


@router.get("", response_model=list[ExpedienteOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    estado: EstadoExpediente | None = None,
    receptor_ruc: str | None = None,
    emisor_ruc: str | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    dia: date | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    pendiente_aprobacion: bool | None = None,
    buscar: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Expediente]:
    consulta = select(Expediente).where(
        Expediente.tenant_id == tenant_id, Expediente.deleted_at.is_(None)
    )
    if auth.rol == "GESTOR":
        consulta = consulta.where(Expediente.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        consulta = consulta.where(Expediente.usuario_id == auth.usuario_id)
    elif auth.rol == RolMiembro.GERENTE:
        consulta = consulta.where(alcance_expedientes_gerente(auth))
    if estado is not None:
        consulta = consulta.where(Expediente.estado == estado)
    if pendiente_aprobacion is not None:
        consulta = consulta.where(Expediente.pendiente_aprobacion == pendiente_aprobacion)
    if usuario_id is not None:
        consulta = consulta.where(Expediente.usuario_id == usuario_id)
    if gestor_id is not None:
        consulta = consulta.where(Expediente.gestor_id == gestor_id)
    if tipo_empresa is not None or emisor_ruc is not None:
        empresa_emisora = aliased(Empresa)
        consulta = consulta.join(empresa_emisora, Expediente.emisor_id == empresa_emisora.id)
        if tipo_empresa is not None:
            consulta = consulta.where(empresa_emisora.clasificacion_proveedor == tipo_empresa)
        if emisor_ruc is not None:
            consulta = consulta.where(empresa_emisora.ruc == emisor_ruc)
    if dia is not None:
        consulta = consulta.where(Expediente.fecha_emision == dia)
    if fecha_desde is not None:
        consulta = consulta.where(Expediente.fecha_emision >= fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.where(Expediente.fecha_emision <= fecha_hasta)
    if receptor_ruc is not None:
        consulta = consulta.join(Empresa, Expediente.receptor_id == Empresa.id).where(
            Empresa.ruc == receptor_ruc
        )
    if buscar and buscar.strip():
        texto = buscar.strip().lower()
        if numero_rhe := NUMERO_RHE_RE.match(texto):
            texto = f"{numero_rhe.group(1)}-{int(numero_rhe.group(2))}"
            consulta = consulta.where(Expediente.tipo_comprobante == "RHE")
        elif numero := NUMERO_RE.match(texto):
            texto = f"{numero.group(1)}-{int(numero.group(2))}"
        emisor = aliased(Empresa)
        consulta = consulta.join(emisor, Expediente.emisor_id == emisor.id).where(
            or_(
                func.lower(Expediente.serie + "-" + Expediente.correlativo).contains(
                    texto, autoescape=True
                ),
                emisor.ruc.contains(texto, autoescape=True),
                func.lower(emisor.razon_social).contains(texto, autoescape=True),
            )
        )
    consulta = (
        consulta.order_by(
            Expediente.fecha_emision.desc(),
            Expediente.created_at.desc(),
            Expediente.id,
        )
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(consulta))


@router.get("/resumen")
def resumen_filtrado(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    estado: EstadoExpediente | None = None,
    receptor_ruc: str | None = None,
    emisor_ruc: str | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    pendiente_aprobacion: bool | None = None,
    buscar: Annotated[str | None, Query(max_length=100)] = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    dia: date | None = None,
) -> dict[str, int | Decimal]:
    consulta = select(Expediente).where(
        Expediente.tenant_id == tenant_id, Expediente.deleted_at.is_(None)
    )
    if auth.rol == "GESTOR":
        consulta = consulta.where(Expediente.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        consulta = consulta.where(Expediente.usuario_id == auth.usuario_id)
    elif auth.rol == RolMiembro.GERENTE:
        consulta = consulta.where(alcance_expedientes_gerente(auth))
    if estado is not None:
        consulta = consulta.where(Expediente.estado == estado)
    if pendiente_aprobacion is not None:
        consulta = consulta.where(Expediente.pendiente_aprobacion == pendiente_aprobacion)
    if usuario_id is not None:
        consulta = consulta.where(Expediente.usuario_id == usuario_id)
    if gestor_id is not None:
        consulta = consulta.where(Expediente.gestor_id == gestor_id)
    if tipo_empresa is not None or emisor_ruc is not None or buscar:
        emisor = aliased(Empresa)
        consulta = consulta.join(emisor, Expediente.emisor_id == emisor.id)
        if tipo_empresa is not None:
            consulta = consulta.where(emisor.clasificacion_proveedor == tipo_empresa)
        if emisor_ruc is not None:
            consulta = consulta.where(emisor.ruc == emisor_ruc)
    if receptor_ruc is not None:
        receptor = aliased(Empresa)
        consulta = consulta.join(receptor, Expediente.receptor_id == receptor.id)
        consulta = consulta.where(receptor.ruc == receptor_ruc)
    if dia is not None:
        consulta = consulta.where(Expediente.fecha_emision == dia)
    if fecha_desde is not None:
        consulta = consulta.where(Expediente.fecha_emision >= fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.where(Expediente.fecha_emision <= fecha_hasta)
    if buscar and buscar.strip():
        texto = buscar.strip().lower()
        if numero_rhe := NUMERO_RHE_RE.match(texto):
            texto = f"{numero_rhe.group(1)}-{int(numero_rhe.group(2))}"
            consulta = consulta.where(Expediente.tipo_comprobante == "RHE")
        elif numero := NUMERO_RE.match(texto):
            texto = f"{numero.group(1)}-{int(numero.group(2))}"
        consulta = consulta.where(
            or_(
                func.lower(Expediente.serie + "-" + Expediente.correlativo).contains(
                    texto, autoescape=True
                ),
                emisor.ruc.contains(texto, autoescape=True),
                func.lower(emisor.razon_social).contains(texto, autoescape=True),
            )
        )
    base = consulta.subquery()
    resultado = session.execute(
        select(
            func.count(base.c.id),
            func.coalesce(
                func.sum(case((base.c.moneda == "PEN", base.c.importe_total), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((base.c.moneda == "USD", base.c.importe_total), else_=0)), 0
            ),
        )
    ).one()
    return {
        "total_expedientes": int(resultado[0]),
        "total_pen": Decimal(resultado[1]),
        "total_usd": Decimal(resultado[2]),
    }


@router.get("/ids", response_model=list[uuid.UUID])
def listar_ids(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    estado: EstadoExpediente | None = None,
    receptor_ruc: str | None = None,
    emisor_ruc: str | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    dia: date | None = None,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    pendiente_aprobacion: bool | None = None,
    buscar: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 1000,
) -> list[uuid.UUID]:
    consulta = select(Expediente.id).where(
        Expediente.tenant_id == tenant_id,
        Expediente.deleted_at.is_(None),
    )
    if auth.rol == "GESTOR":
        consulta = consulta.where(Expediente.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        consulta = consulta.where(Expediente.usuario_id == auth.usuario_id)
    elif auth.rol == RolMiembro.GERENTE:
        consulta = consulta.where(alcance_expedientes_gerente(auth))
    if estado is not None:
        consulta = consulta.where(Expediente.estado == estado)
    if pendiente_aprobacion is not None:
        consulta = consulta.where(Expediente.pendiente_aprobacion == pendiente_aprobacion)
    if usuario_id is not None:
        consulta = consulta.where(Expediente.usuario_id == usuario_id)
    if gestor_id is not None:
        consulta = consulta.where(Expediente.gestor_id == gestor_id)
    if tipo_empresa is not None or emisor_ruc is not None:
        empresa_emisora = aliased(Empresa)
        consulta = consulta.join(empresa_emisora, Expediente.emisor_id == empresa_emisora.id)
        if tipo_empresa is not None:
            consulta = consulta.where(empresa_emisora.clasificacion_proveedor == tipo_empresa)
        if emisor_ruc is not None:
            consulta = consulta.where(empresa_emisora.ruc == emisor_ruc)
    if dia is not None:
        consulta = consulta.where(Expediente.fecha_emision == dia)
    if fecha_desde is not None:
        consulta = consulta.where(Expediente.fecha_emision >= fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.where(Expediente.fecha_emision <= fecha_hasta)
    if receptor_ruc is not None:
        consulta = consulta.join(Empresa, Expediente.receptor_id == Empresa.id).where(
            Empresa.ruc == receptor_ruc
        )
    if buscar and buscar.strip():
        texto = buscar.strip().lower()
        if numero_rhe := NUMERO_RHE_RE.match(texto):
            texto = f"{numero_rhe.group(1)}-{int(numero_rhe.group(2))}"
            consulta = consulta.where(Expediente.tipo_comprobante == "RHE")
        elif numero := NUMERO_RE.match(texto):
            texto = f"{numero.group(1)}-{int(numero.group(2))}"
        emisor = aliased(Empresa)
        consulta = consulta.join(emisor, Expediente.emisor_id == emisor.id).where(
            or_(
                func.lower(Expediente.serie + "-" + Expediente.correlativo).contains(
                    texto, autoescape=True
                ),
                emisor.ruc.contains(texto, autoescape=True),
                func.lower(emisor.razon_social).contains(texto, autoescape=True),
            )
        )
    consulta = consulta.order_by(
        Expediente.fecha_emision.desc(),
        Expediente.created_at.desc(),
        Expediente.id,
    ).limit(limit)
    return list(session.scalars(consulta))


def _visible_para_auth(expediente: Expediente, auth: OperativeAuthDep) -> bool:
    if auth.rol == "GESTOR":
        return expediente.gestor_id == auth.gestor_id
    if auth.rol == RolMiembro.USUARIO:
        return expediente.usuario_id == auth.usuario_id
    if auth.rol == RolMiembro.GERENTE:
        return expediente_visible_gerente(expediente, auth)
    return True


def _borrar_temporal(ruta: str) -> None:
    Path(ruta).unlink(missing_ok=True)


@router.post("/imprimir-lote")
def imprimir_lote(
    datos: ImpresionExpedientesIn,
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> FileResponse:
    ids_unicos = list(dict.fromkeys(datos.expediente_ids))
    expedientes = list(
        session.scalars(
            select(Expediente).where(
                Expediente.tenant_id == tenant_id,
                Expediente.id.in_(ids_unicos),
                Expediente.deleted_at.is_(None),
            )
        )
    )
    por_id = {item.id: item for item in expedientes}
    ordenados: list[Expediente] = []
    for expediente_id in ids_unicos:
        expediente = por_id.get(expediente_id)
        if expediente is None or not _visible_para_auth(expediente, auth):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
        ordenados.append(expediente)

    documentos = list(
        session.scalars(
            select(Documento)
            .where(
                Documento.tenant_id == tenant_id,
                Documento.expediente_id.in_(ids_unicos),
                Documento.deleted_at.is_(None),
            )
            .order_by(Documento.created_at, Documento.id)
        )
    )
    por_expediente: dict[uuid.UUID, list[Documento]] = {}
    for documento in documentos:
        if documento.expediente_id is not None:
            por_expediente.setdefault(documento.expediente_id, []).append(documento)

    writer = PdfWriter()
    pdfs_incluidos = 0
    expedientes_sin_pdf = 0
    for expediente in ordenados:
        incluidos_expediente = 0
        for documento in por_expediente.get(expediente.id, []):
            es_pdf = (
                documento.mime_type.lower() == "application/pdf"
                or documento.nombre_original.lower().endswith(".pdf")
            )
            if not es_pdf:
                continue
            ruta = almacen.ruta_absoluta(documento.ruta_storage)
            try:
                reader = PdfReader(str(ruta))
                for pagina in reader.pages:
                    writer.add_page(pagina)
            except (OSError, PdfReadError) as exc:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    f"No se pudo preparar para impresión: {documento.nombre_original}",
                ) from exc
            pdfs_incluidos += 1
            incluidos_expediente += 1
        if incluidos_expediente == 0:
            expedientes_sin_pdf += 1

    if len(writer.pages) == 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Los expedientes seleccionados no contienen archivos PDF imprimibles",
        )

    with tempfile.NamedTemporaryFile(
        prefix="fact-central-impresion-",
        suffix=".pdf",
        delete=False,
    ) as temporal:
        ruta_temporal = temporal.name
    with open(ruta_temporal, "wb") as destino:
        writer.write(destino)
    writer.close()

    auditoria.registrar(
        session,
        tenant_id,
        "EXPEDIENTES_IMPRESION_GENERADA",
        "tenant",
        tenant_id,
        {
            "actor": auth.codigo,
            "expediente_ids": [str(item.id) for item in ordenados],
            "expedientes": len(ordenados),
            "pdfs": pdfs_incluidos,
            "sin_pdf": expedientes_sin_pdf,
        },
    )
    session.commit()

    return FileResponse(
        ruta_temporal,
        media_type="application/pdf",
        filename="fact-central-expedientes.pdf",
        headers={
            "X-Expedientes-Impresos": str(len(ordenados)),
            "X-Pdfs-Impresos": str(pdfs_incluidos),
            "X-Expedientes-Sin-Pdf": str(expedientes_sin_pdf),
        },
        background=BackgroundTask(_borrar_temporal, ruta_temporal),
    )


@router.get("/{expediente_id}/descargar-pdf")
def descargar_pdf(
    expediente_id: uuid.UUID,
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> FileResponse:
    expediente = session.get(Expediente, expediente_id)
    if (
        expediente is None
        or expediente.tenant_id != tenant_id
        or expediente.deleted_at is not None
        or not _visible_para_auth(expediente, auth)
    ):
        raise no_encontrado("Expediente")
    documentos = list(
        session.scalars(
            select(Documento)
            .where(
                Documento.tenant_id == tenant_id,
                Documento.expediente_id == expediente_id,
                Documento.deleted_at.is_(None),
            )
            .order_by(Documento.created_at, Documento.id)
        )
    )
    try:
        writer, visibles, adjuntos = pdf_con_documentos(
            documentos,
            almacen,
            f"{expediente.serie}-{expediente.correlativo}",
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    with tempfile.NamedTemporaryFile(
        prefix="fact-central-pdf-",
        suffix=".pdf",
        delete=False,
    ) as temporal:
        ruta_temporal = temporal.name
    try:
        with open(ruta_temporal, "wb") as destino:
            writer.write(destino)
    except OSError:
        _borrar_temporal(ruta_temporal)
        raise
    finally:
        writer.close()
    auditoria.registrar(
        session,
        tenant_id,
        "EXPEDIENTE_PDF_DESCARGADO",
        "expediente",
        expediente_id,
        {"actor": auth.codigo, "visibles": visibles, "adjuntos": adjuntos},
    )
    session.commit()
    return FileResponse(
        ruta_temporal,
        media_type="application/pdf",
        filename=f"fact-central-{expediente.serie}-{expediente.correlativo}.pdf",
        background=BackgroundTask(_borrar_temporal, ruta_temporal),
    )


@router.get("/{expediente_id}/descargar-zip")
def descargar_zip(
    expediente_id: uuid.UUID,
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> FileResponse:
    """Entrega todos los originales de un expediente autorizado con manifiesto."""
    expediente = session.get(Expediente, expediente_id)
    if (
        expediente is None
        or expediente.tenant_id != tenant_id
        or expediente.deleted_at is not None
        or not _visible_para_auth(expediente, auth)
    ):
        raise no_encontrado("Expediente")

    documentos = list(
        session.scalars(
            select(Documento)
            .where(
                Documento.tenant_id == tenant_id,
                Documento.expediente_id == expediente_id,
                Documento.deleted_at.is_(None),
            )
            .order_by(Documento.created_at, Documento.id)
        )
    )
    if not documentos:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "El expediente no contiene documentos"
        )

    # Cuota de exportación: evita agotar disco o memoria con expedientes excesivos.
    if len(documentos) > 200 or sum(d.tamano_bytes for d in documentos) > 500 * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "Expediente demasiado grande para exportación",
        )

    nombre_carpeta = f"expediente-{expediente.id}"
    documentos_manifiesto: list[dict[str, str | None]] = []
    manifiesto = {
        "expediente": str(expediente.id),
        "emisor_ruc": expediente.emisor.ruc,
        "receptor_ruc": expediente.receptor.ruc,
        "comprobante": f"{expediente.tipo_comprobante} {expediente.serie}-{expediente.correlativo}",
        "documentos": documentos_manifiesto,
    }
    with tempfile.NamedTemporaryFile(
        prefix="fact-central-export-",
        suffix=".zip",
        delete=False,
    ) as temporal:
        ruta_temporal = temporal.name
    try:
        with zipfile.ZipFile(ruta_temporal, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i, doc in enumerate(documentos, start=1):
                extension = Path(doc.nombre_original).suffix.lower()
                if not extension or len(extension) > 12 or not extension[1:].isalnum():
                    extension = ".bin"
                nombre = (
                    f"{nombre_carpeta}/{i:03d}_{doc.tipo_documento or 'OTRO'}_{doc.id}{extension}"
                )
                ruta = almacen.ruta_absoluta(doc.ruta_storage)
                zf.write(ruta, arcname=nombre)
                documentos_manifiesto.append(
                    {
                        "nombre_original": doc.nombre_original,
                        "archivo": nombre,
                        "tipo_documento": doc.tipo_documento,
                        "sha256": doc.sha256,
                        "fecha_carga": doc.created_at.isoformat(),
                    }
                )
            zf.writestr(
                f"{nombre_carpeta}/manifiesto.json",
                json.dumps(manifiesto, ensure_ascii=False, indent=2),
            )
    except (OSError, zipfile.BadZipFile):
        _borrar_temporal(ruta_temporal)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "No se pudo preparar la exportación"
        ) from None

    auditoria.registrar(
        session,
        tenant_id,
        "EXPEDIENTE_ZIP_DESCARGADO",
        "expediente",
        expediente_id,
        {"actor": auth.codigo, "documentos": len(documentos)},
    )
    session.commit()
    return FileResponse(
        ruta_temporal,
        media_type="application/zip",
        filename=f"fact-central-{expediente.serie}-{expediente.correlativo}.zip",
        background=BackgroundTask(_borrar_temporal, ruta_temporal),
    )


@router.post("/recalcular", response_model=Recalculo)
def recalcular(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> Recalculo:
    if auth.rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR, RolMiembro.SECRETARIA):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No tiene permiso para recalcular expedientes",
        )
    actualizados = recalcular_expedientes(session, tenant_id, hoy, settings)
    session.commit()
    return Recalculo(actualizados=actualizados)


@router.get("/{expediente_id}", response_model=ExpedienteDetalle)
def detalle(
    session: SessionDep,
    settings: SettingsDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    expediente_id: uuid.UUID,
) -> ExpedienteDetalle:
    expediente = session.get(Expediente, expediente_id)
    if expediente is None or expediente.tenant_id != tenant_id or expediente.deleted_at:
        raise no_encontrado("Expediente")
    if auth.rol == "GESTOR" and expediente.gestor_id != auth.gestor_id:
        raise no_encontrado("Expediente")
    if not _visible_para_auth(expediente, auth):
        raise no_encontrado("Expediente")
    base = ExpedienteOut.model_validate(expediente)
    return ExpedienteDetalle(
        **base.model_dump(),
        documentos=[d for d in expediente.documentos if d.deleted_at is None],
        alertas=expediente.alertas,
        faltantes=documentos_faltantes(expediente, settings),
        fecha_limite=fecha_limite(expediente.fecha_emision, settings.dia_limite_expediente),
    )


@router.delete("/{expediente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    expediente_id: uuid.UUID,
) -> None:
    expediente = session.get(Expediente, expediente_id)
    if expediente is None or expediente.tenant_id != tenant_id or expediente.deleted_at:
        raise no_encontrado("Expediente")
    if auth.rol == "GESTOR" and expediente.gestor_id != auth.gestor_id:
        raise no_encontrado("Expediente")
    if not _visible_para_auth(expediente, auth):
        raise no_encontrado("Expediente")
    if not permiso_habilitado(
        session,
        tenant_id,
        auth.rol,
        PERMISO_ELIMINAR_REGISTROS,
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No tiene permiso para eliminar registros",
        )

    expediente.deleted_at = ahora()
    auditoria.registrar(
        session,
        tenant_id,
        "EXPEDIENTE_ELIMINADO",
        "expediente",
        expediente.id,
        {
            "tipo": expediente.tipo_comprobante,
            "serie": expediente.serie,
            "correlativo": expediente.correlativo,
        },
    )
    session.commit()
