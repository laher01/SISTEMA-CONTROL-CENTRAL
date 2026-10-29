import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import AlmacenDep, HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.pesca.models import (
    AbonoMovimientoPesca,
    CargaEmbarcacionVehiculo,
    DescargaEmbarcacion,
    DocumentoPesca,
    EmbarcacionPesca,
    HistorialPesca,
    OperacionPesca,
    MovimientoPesca,
    RegistroPlanta,
    VehiculoPesca,
    VinculoDocumentoEmbarcacion,
    VinculoDocumentoVehiculo,
)
from app.pesca.schemas import (
    AbonoMovimientoIn,
    AbonoMovimientoOut,
    CargaIn,
    CierreOut,
    ConfirmarPrecioIn,
    DescargaOut,
    DocumentoOut,
    EmbarcacionIn,
    OperacionIn,
    OperacionOut,
    MovimientoIn,
    MovimientoOut,
    RegistrarFacturaIn,
    RegistroPlantaIn,
    RegistroPlantaOut,
    TiemposDescargaIn,
    TiemposPlantaIn,
    VehiculoIn,
    VehiculoOut,
)
from app.storage import AlmacenLocal

router = APIRouter(prefix="/pesca", tags=["operaciones de pesca"])
TIPOS_DOCUMENTO = {
    "certificado_matricula",
    "permiso_pesca",
    "certificado_sanipes",
    "reporte_satelital",
    "visto_bueno_produce",
    "guia_remitente",
    "guia_transportista",
    "acta_fiscalizacion",
    "formato_descarga",
    "certificado_procedencia",
    "certificado_captura",
    "factura",
    "comprobante_gasto",
    "peso_planta",
    "otro",
}
MIME_PERMITIDOS = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
FACTOR_KG = {
    "kg": Decimal("1"),
    "ton": Decimal("1000"),
    "lb": Decimal("0.45359237"),
    "oz": Decimal("0.028349523125"),
}


def obtener_actor(auth: OperativeAuthDep) -> str:
    """La auditoría usa la identidad validada por la sesión de la plataforma."""
    return auth.codigo[:200]


ActorDep = Annotated[str, Depends(obtener_actor)]


def _operacion(session: Session, tenant_id: uuid.UUID, op_id: uuid.UUID) -> OperacionPesca:
    obj = session.scalar(
        select(OperacionPesca).where(
            OperacionPesca.id == op_id, OperacionPesca.tenant_id == tenant_id
        )
    )
    if obj is None:
        raise HTTPException(404, "Operación no encontrada")
    return obj


def _vehiculo(session: Session, tenant_id: uuid.UUID, vehiculo_id: uuid.UUID) -> VehiculoPesca:
    obj = session.scalar(
        select(VehiculoPesca).where(
            VehiculoPesca.id == vehiculo_id, VehiculoPesca.tenant_id == tenant_id
        )
    )
    if obj is None:
        raise HTTPException(404, "Vehículo no encontrado")
    return obj


def _tipos_documento_vehiculo(
    session: Session, tenant_id: uuid.UUID, op_id: uuid.UUID, vehicle_id: uuid.UUID
) -> set[str]:
    tipos = set(
        session.scalars(
            select(DocumentoPesca.tipo).where(
                DocumentoPesca.operacion_id == op_id,
                DocumentoPesca.tenant_id == tenant_id,
                (DocumentoPesca.vehiculo_id.is_(None)) | (DocumentoPesca.vehiculo_id == vehicle_id),
            )
        )
    )
    linked = set(
        session.scalars(
            select(VinculoDocumentoVehiculo.documento_id).where(
                VinculoDocumentoVehiculo.vehiculo_id == vehicle_id
            )
        )
    )
    if linked:
        tipos.update(
            session.scalars(
                select(DocumentoPesca.tipo).where(
                    DocumentoPesca.tenant_id == tenant_id,
                    DocumentoPesca.id.in_(linked),
                )
            )
        )
    return tipos


def _historial(
    session: Session,
    tenant_id: uuid.UUID,
    operacion_id: uuid.UUID,
    actor: str,
    accion: str,
    detalle: str,
    vehiculo_id: uuid.UUID | None = None,
) -> None:
    session.add(
        HistorialPesca(
            tenant_id=tenant_id,
            operacion_id=operacion_id,
            vehiculo_id=vehiculo_id,
            actor=actor,
            accion=accion,
            detalle=detalle,
        )
    )


@router.post("/operaciones", response_model=OperacionOut, status_code=201)
def crear_operacion(
    datos: OperacionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    hoy: HoyDep,
    actor: ActorDep,
) -> OperacionPesca:
    op = OperacionPesca(
        tenant_id=tenant_id,
        fecha_reporte=datos.fecha_reporte or hoy,
        puerto=datos.puerto,
        muelle=datos.muelle,
        planta=datos.planta,
        armador_reportante=datos.armador_reportante,
        comprador=datos.comprador,
        remitente=datos.remitente,
        destinatario=datos.destinatario,
        facturador=datos.facturador,
        toneladas_declaradas=datos.toneladas_declaradas,
        precio_propuesto=datos.precio_propuesto,
        descarga_prevista=datos.descarga_prevista,
        llegada_planta_prevista=datos.llegada_planta_prevista,
        jefe_bahia=datos.jefe_bahia,
        encargado_muelle=datos.encargado_muelle,
        apuntador=datos.apuntador,
        responsable_id=actor[:200],
        estado="preparacion",
        observacion=datos.observacion,
    )
    session.add(op)
    session.flush()
    _historial(session, tenant_id, op.id, actor, "operacion_creada", "Operación iniciada")
    session.commit()
    session.refresh(op)
    return op


@router.post("/operaciones/{op_id}/iniciar-descarga", response_model=OperacionOut)
def iniciar_descarga_operacion(
    op_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> OperacionPesca:
    op = _operacion(session, tenant_id, op_id)
    if op.estado != "preparacion":
        raise HTTPException(409, "La operación no está en etapa de preparación")
    if op.precio_confirmado is None:
        raise HTTPException(409, "Falta confirmar el precio con el comprador")
    embarcaciones = list(
        session.scalars(
            select(DescargaEmbarcacion).where(
                DescargaEmbarcacion.operacion_id == op.id,
                DescargaEmbarcacion.tenant_id == tenant_id,
            )
        )
    )
    if not embarcaciones:
        raise HTTPException(409, "Registra al menos una embarcación antes de iniciar la descarga")
    if op.toneladas_declaradas is None and any(item.peso_declarado_kg is None for item in embarcaciones):
        raise HTTPException(409, "Registra el peso declarado de la operación o de cada embarcación")
    vehiculo_preparado = session.scalar(
        select(VehiculoPesca.id).where(
            VehiculoPesca.operacion_id == op.id,
            VehiculoPesca.tenant_id == tenant_id,
        ).limit(1)
    )
    if vehiculo_preparado is None:
        raise HTTPException(409, "Prepara y registra al menos un vehículo antes de iniciar la descarga")
    vinculos_nave = select(VinculoDocumentoEmbarcacion.documento_id)
    documentos_globales = list(
        session.scalars(
            select(DocumentoPesca).where(
                DocumentoPesca.operacion_id == op.id,
                DocumentoPesca.tenant_id == tenant_id,
                DocumentoPesca.vehiculo_id.is_(None),
                ~DocumentoPesca.id.in_(vinculos_nave),
            )
        )
    )
    tipos_globales = {doc.tipo for doc in documentos_globales}
    requeridos = {
        "certificado_matricula",
        "permiso_pesca",
        "certificado_sanipes",
        "reporte_satelital",
        "visto_bueno_produce",
        "guia_remitente",
    }
    faltantes_por_nave: list[str] = []
    for descarga in embarcaciones:
        tipos_nave = set(tipos_globales)
        tipos_nave.update(
            session.scalars(
                select(DocumentoPesca.tipo)
                .join(VinculoDocumentoEmbarcacion, VinculoDocumentoEmbarcacion.documento_id == DocumentoPesca.id)
                .where(
                    DocumentoPesca.tenant_id == tenant_id,
                    DocumentoPesca.operacion_id == op.id,
                    VinculoDocumentoEmbarcacion.embarcacion_id == descarga.embarcacion_id,
                )
            )
        )
        missing = sorted(requeridos - tipos_nave)
        if missing:
            embarcacion = session.get(EmbarcacionPesca, descarga.embarcacion_id)
            nombre_nave = embarcacion.matricula if embarcacion else str(descarga.embarcacion_id)
            faltantes_por_nave.append(f"{nombre_nave}: {', '.join(missing)}")
    faltantes = faltantes_por_nave
    if faltantes:
        raise HTTPException(409, f"Faltan documentos previos a descarga por embarcación: {'; '.join(faltantes)}")
    op.estado = "en_descarga"
    _historial(session, tenant_id, op.id, actor, "descarga_iniciada", "Documentos y precio verificados; descarga autorizada")
    session.commit()
    session.refresh(op)
    return op


@router.post("/operaciones/{op_id}/confirmar-precio", response_model=OperacionOut)
def confirmar_precio(
    op_id: uuid.UUID,
    datos: ConfirmarPrecioIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> OperacionPesca:
    op = _operacion(session, tenant_id, op_id)
    if op.estado == "cerrada":
        raise HTTPException(409, "La operación ya está cerrada")
    if op.precio_confirmado is not None:
        raise HTTPException(409, "El precio ya fue confirmado y no se puede cambiar")
    if op.comprador and datos.comprador.casefold().strip() != op.comprador.casefold().strip():
        raise HTTPException(422, "La confirmación debe corresponder al comprador registrado")
    op.comprador = op.comprador or datos.comprador.strip()
    op.precio_confirmado = datos.precio_confirmado
    op.precio_confirmado_por = actor[:200]
    op.precio_confirmado_at = datetime.now(UTC)
    _historial(
        session,
        tenant_id,
        op.id,
        actor,
        "precio_confirmado",
        f"Comprador: {op.comprador}; precio confirmado: S/ {datos.precio_confirmado}",
    )
    session.commit()
    session.refresh(op)
    return op


@router.post("/operaciones/{op_id}/factura", response_model=OperacionOut)
def registrar_factura(
    op_id: uuid.UUID,
    datos: RegistrarFacturaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> OperacionPesca:
    op = _operacion(session, tenant_id, op_id)
    if op.estado != "cerrada":
        raise HTTPException(409, "Registra la factura después de cerrar la recepción de todos los vehículos")
    certificado = session.scalar(
        select(DocumentoPesca.id).where(
            DocumentoPesca.operacion_id == op.id,
            DocumentoPesca.tenant_id == tenant_id,
            DocumentoPesca.tipo == "certificado_procedencia",
            DocumentoPesca.vehiculo_id.is_(None),
        )
    )
    if certificado is None:
        raise HTTPException(409, "Falta adjuntar el certificado de procedencia")
    if op.factura_serie is not None:
        raise HTTPException(409, "La factura ya fue registrada para esta operación")
    op.factura_serie = datos.serie.strip().upper()
    op.factura_correlativo = datos.correlativo.strip()
    op.factura_emitida_at = datetime.now(UTC)
    op.factura_emitida_por = actor[:200]
    op.estado_facturacion = "pendiente_documento"
    _historial(session, tenant_id, op.id, actor, "factura_registrada", f"Factura {op.factura_serie}-{op.factura_correlativo}; pendiente adjuntar comprobante")
    session.commit()
    session.refresh(op)
    return op


@router.get("/operaciones", response_model=list[OperacionOut])
def listar_operaciones(session: SessionDep, tenant_id: TenantDep) -> list[OperacionPesca]:
    return list(
        session.scalars(
            select(OperacionPesca)
            .where(OperacionPesca.tenant_id == tenant_id)
            .order_by(OperacionPesca.created_at.desc())
        )
    )


def _movimiento_out(session: Session, item: MovimientoPesca) -> MovimientoOut:
    abonado = session.scalar(
        select(func.coalesce(func.sum(AbonoMovimientoPesca.importe), 0)).where(
            AbonoMovimientoPesca.tenant_id == item.tenant_id,
            AbonoMovimientoPesca.movimiento_id == item.id,
        )
    ) or Decimal("0")
    saldo = max(Decimal("0"), item.importe - Decimal(abonado))
    if item.clase == "gasto_empresa":
        estado = "pagado_empresa"
    elif saldo == 0:
        estado = "saldado"
    elif item.clase == "gasto_bahia_reembolsable":
        estado = "pendiente_reembolso"
    elif item.clase == "adelanto_armador_empresa":
        estado = "pendiente_devolucion"
    else:
        estado = "prestamo_personal_pendiente"
    return MovimientoOut.model_validate(item).model_copy(update={"abonado": abonado, "saldo": saldo, "estado": estado})


@router.post("/movimientos", response_model=MovimientoOut, status_code=201)
def crear_movimiento(
    datos: MovimientoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> MovimientoOut:
    if datos.operacion_id is not None:
        _operacion(session, tenant_id, datos.operacion_id)
    item = MovimientoPesca(
        tenant_id=tenant_id,
        operacion_id=datos.operacion_id,
        clase=datos.clase,
        pagador=datos.pagador,
        beneficiario=datos.beneficiario,
        concepto=datos.concepto,
        importe=datos.importe,
        moneda=datos.moneda,
        cantidad=datos.cantidad,
        tarifa_unitaria=datos.tarifa_unitaria,
        registrado_por=actor[:200],
    )
    session.add(item)
    session.flush()
    if item.operacion_id:
        _historial(session, tenant_id, item.operacion_id, actor, "movimiento_financiero_registrado", f"{item.clase}: {item.concepto}; importe {item.moneda} {item.importe}")
    session.commit()
    session.refresh(item)
    return _movimiento_out(session, item)


@router.get("/operaciones/{op_id}/movimientos", response_model=list[MovimientoOut])
def listar_movimientos_operacion(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> list[MovimientoOut]:
    _operacion(session, tenant_id, op_id)
    items = session.scalars(
        select(MovimientoPesca)
        .where(MovimientoPesca.tenant_id == tenant_id, MovimientoPesca.operacion_id == op_id)
        .order_by(MovimientoPesca.created_at)
    )
    return [_movimiento_out(session, item) for item in items]


@router.get("/movimientos-personales", response_model=list[MovimientoOut])
def listar_prestamos_personales(session: SessionDep, tenant_id: TenantDep, actor: ActorDep) -> list[MovimientoOut]:
    items = session.scalars(
        select(MovimientoPesca)
        .where(
            MovimientoPesca.tenant_id == tenant_id,
            MovimientoPesca.clase == "prestamo_personal_bahia",
            MovimientoPesca.registrado_por == actor,
        )
        .order_by(MovimientoPesca.created_at.desc())
    )
    return [_movimiento_out(session, item) for item in items]


@router.post("/movimientos/{movimiento_id}/abonos", response_model=AbonoMovimientoOut, status_code=201)
def registrar_abono_movimiento(
    movimiento_id: uuid.UUID,
    datos: AbonoMovimientoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> AbonoMovimientoPesca:
    item = session.scalar(
        select(MovimientoPesca).where(
            MovimientoPesca.id == movimiento_id, MovimientoPesca.tenant_id == tenant_id
        )
    )
    if item is None:
        raise HTTPException(404, "Movimiento no encontrado")
    if item.clase == "prestamo_personal_bahia" and item.registrado_por != actor:
        raise HTTPException(404, "Movimiento no encontrado")
    if item.clase == "gasto_empresa":
        raise HTTPException(409, "Un gasto pagado directamente por la empresa no tiene saldo por cobrar")
    current = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(AbonoMovimientoPesca.importe), 0)).where(
                AbonoMovimientoPesca.tenant_id == tenant_id,
                AbonoMovimientoPesca.movimiento_id == item.id,
            )
        ) or 0
    )
    if current + datos.importe > item.importe:
        raise HTTPException(422, "El abono supera el saldo pendiente")
    tipo = {
        "gasto_bahia_reembolsable": "reembolso_bahia",
        "adelanto_armador_empresa": "devolucion_armador",
        "prestamo_personal_bahia": "abono_prestamo_personal",
    }[item.clase]
    abono = AbonoMovimientoPesca(
        tenant_id=tenant_id,
        movimiento_id=item.id,
        importe=datos.importe,
        tipo=tipo,
        registrado_por=actor[:200],
        observacion=datos.observacion,
    )
    session.add(abono)
    if item.operacion_id:
        _historial(session, tenant_id, item.operacion_id, actor, tipo, f"Abono {item.moneda} {datos.importe} al movimiento {item.id}")
    session.commit()
    session.refresh(abono)
    return abono


@router.post("/movimientos/{movimiento_id}/comprobante", response_model=DocumentoOut, status_code=201)
async def adjuntar_comprobante_movimiento(
    movimiento_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    actor: ActorDep,
    archivo: UploadFile = File(...),
) -> DocumentoPesca:
    item = session.scalar(
        select(MovimientoPesca).where(
            MovimientoPesca.id == movimiento_id, MovimientoPesca.tenant_id == tenant_id
        )
    )
    if item is None or (item.clase == "prestamo_personal_bahia" and item.registrado_por != actor):
        raise HTTPException(404, "Movimiento no encontrado")
    if item.comprobante_documento_id is not None:
        raise HTTPException(409, "Este movimiento ya tiene un comprobante adjunto")
    mime = archivo.content_type or "application/octet-stream"
    if mime not in MIME_PERMITIDOS:
        raise HTTPException(415, "Solo se permiten PDF, JPG, PNG o WEBP")
    raw = await archivo.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Archivo demasiado grande")
    if not raw:
        raise HTTPException(422, "Archivo vacío")
    digest = hashlib.sha256(raw).hexdigest()
    path = almacen.guardar(tenant_id, digest, raw)
    doc = DocumentoPesca(
        tenant_id=tenant_id,
        operacion_id=item.operacion_id,
        tipo="comprobante_gasto",
        nombre=archivo.filename or "comprobante",
        mime_type=mime,
        sha256=digest,
        ruta_storage=path,
        subido_por=actor[:200],
    )
    session.add(doc)
    session.flush()
    item.comprobante_documento_id = doc.id
    if item.operacion_id:
        _historial(session, tenant_id, item.operacion_id, actor, "comprobante_financiero_cargado", f"Comprobante {doc.nombre} para {item.clase}")
    session.commit()
    session.refresh(doc)
    return doc


@router.post("/operaciones/{op_id}/embarcaciones", response_model=DescargaOut, status_code=201)
def agregar_embarcacion(
    op_id: uuid.UUID,
    datos: EmbarcacionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> DescargaOut:
    op = _operacion(session, tenant_id, op_id)
    if op.estado != "preparacion":
        raise HTTPException(409, "Las embarcaciones deben quedar vinculadas antes de iniciar la descarga")
    embarcacion = session.scalar(
        select(EmbarcacionPesca).where(
            EmbarcacionPesca.tenant_id == tenant_id,
            EmbarcacionPesca.matricula == datos.matricula,
        )
    )
    if embarcacion is None:
        embarcacion = EmbarcacionPesca(
            tenant_id=tenant_id,
            matricula=datos.matricula,
            nombre=datos.nombre,
            patron_armador=f"Armador: {datos.armador}; patrón: {datos.patron}",
            armador=datos.armador,
            patron=datos.patron,
            intermediario=datos.intermediario,
        )
        session.add(embarcacion)
        session.flush()
    else:
        embarcacion.nombre = datos.nombre
        embarcacion.patron_armador = f"Armador: {datos.armador}; patrón: {datos.patron}"
        embarcacion.armador = datos.armador
        embarcacion.patron = datos.patron
        embarcacion.intermediario = datos.intermediario
    descarga = DescargaEmbarcacion(
        tenant_id=tenant_id,
        operacion_id=op.id,
        embarcacion_id=embarcacion.id,
        matricula_snapshot=embarcacion.matricula,
        nombre_snapshot=embarcacion.nombre,
        armador_snapshot=datos.armador.strip(),
        patron_snapshot=datos.patron.strip(),
        inicio_descarga=datos.inicio_descarga,
        fin_descarga=datos.fin_descarga,
        peso_declarado_kg=datos.peso_declarado_kg,
    )
    session.add(descarga)
    _historial(session, tenant_id, op.id, actor, "embarcacion_agregada", f"Embarcación {datos.matricula}")
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "La embarcación ya está vinculada a esta operación") from exc
    return DescargaOut(
        descarga_id=descarga.id,
        embarcacion_id=embarcacion.id,
        matricula=descarga.matricula_snapshot,
        nombre=descarga.nombre_snapshot,
        armador=descarga.armador_snapshot,
        patron=descarga.patron_snapshot,
        peso_declarado_kg=descarga.peso_declarado_kg,
        inicio_descarga=descarga.inicio_descarga,
        fin_descarga=descarga.fin_descarga,
    )


@router.get("/operaciones/{op_id}/embarcaciones", response_model=list[DescargaOut])
def listar_embarcaciones(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> list[DescargaOut]:
    _operacion(session, tenant_id, op_id)
    rows = session.execute(
        select(DescargaEmbarcacion, EmbarcacionPesca)
        .join(EmbarcacionPesca, EmbarcacionPesca.id == DescargaEmbarcacion.embarcacion_id)
        .where(
            DescargaEmbarcacion.operacion_id == op_id,
            DescargaEmbarcacion.tenant_id == tenant_id,
        )
        .order_by(DescargaEmbarcacion.created_at)
    )
    return [
        DescargaOut(
            descarga_id=descarga.id,
            embarcacion_id=vessel.id,
            matricula=descarga.matricula_snapshot,
            nombre=descarga.nombre_snapshot,
            armador=descarga.armador_snapshot,
            patron=descarga.patron_snapshot,
            peso_declarado_kg=descarga.peso_declarado_kg,
            inicio_descarga=descarga.inicio_descarga,
            fin_descarga=descarga.fin_descarga,
        )
        for descarga, vessel in rows
    ]


@router.patch("/descargas/{descarga_id}/fechas", response_model=DescargaOut)
def actualizar_tiempos_descarga(
    descarga_id: uuid.UUID,
    datos: TiemposDescargaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> DescargaOut:
    descarga = session.scalar(
        select(DescargaEmbarcacion).where(
            DescargaEmbarcacion.id == descarga_id,
            DescargaEmbarcacion.tenant_id == tenant_id,
        )
    )
    if descarga is None:
        raise HTTPException(404, "Descarga no encontrada")
    op = _operacion(session, tenant_id, descarga.operacion_id)
    if op.estado == "cerrada":
        raise HTTPException(409, "La operación está cerrada")
    antes = f"inicio={descarga.inicio_descarga}; fin={descarga.fin_descarga}"
    if "inicio_descarga" in datos.model_fields_set:
        descarga.inicio_descarga = datos.inicio_descarga
    if "fin_descarga" in datos.model_fields_set:
        descarga.fin_descarga = datos.fin_descarga
    _historial(
        session,
        tenant_id,
        op.id,
        actor,
        "horas_descarga_actualizadas",
        f"Matrícula de descarga {descarga.embarcacion_id}; antes: {antes}; ahora: inicio={descarga.inicio_descarga}; fin={descarga.fin_descarga}. Motivo: {datos.observacion}",
    )
    session.commit()
    vessel = session.get(EmbarcacionPesca, descarga.embarcacion_id)
    if vessel is None:
        raise HTTPException(404, "Embarcación no encontrada")
    return DescargaOut(
        descarga_id=descarga.id,
        embarcacion_id=vessel.id,
        matricula=descarga.matricula_snapshot,
        nombre=descarga.nombre_snapshot,
        armador=descarga.armador_snapshot,
        patron=descarga.patron_snapshot,
        peso_declarado_kg=descarga.peso_declarado_kg,
        inicio_descarga=descarga.inicio_descarga,
        fin_descarga=descarga.fin_descarga,
    )


@router.post("/operaciones/{op_id}/vehiculos", response_model=VehiculoOut, status_code=201)
def agregar_vehiculo(
    op_id: uuid.UUID,
    datos: VehiculoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> VehiculoPesca:
    op = _operacion(session, tenant_id, op_id)
    if op.estado not in {"preparacion", "en_descarga"}:
        raise HTTPException(409, "No se pueden agregar vehículos después del despacho a planta")
    vehicle = VehiculoPesca(
        tenant_id=tenant_id,
        operacion_id=op_id,
        placa=datos.placa,
        tipo=datos.tipo,
        chofer=datos.chofer,
        turno=datos.turno,
        estado="pendiente_muelle",
    )
    session.add(vehicle)
    session.flush()
    _historial(session, tenant_id, op_id, actor, "vehiculo_agregado", f"Vehículo {datos.placa}", vehicle.id)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.post("/vehiculos/{vehiculo_id}/traslado/iniciar", response_model=VehiculoOut)
def iniciar_traslado_planta(
    vehiculo_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> VehiculoPesca:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    op = _operacion(session, tenant_id, vehicle.operacion_id)
    if op.estado != "en_descarga":
        raise HTTPException(409, "La operación debe estar en descarga antes de despachar el vehículo")
    if vehicle.estado != "pendiente_muelle":
        raise HTTPException(409, "El vehículo no está esperando despacho desde el muelle")
    tiene_carga = session.scalar(
        select(CargaEmbarcacionVehiculo.id).where(
            CargaEmbarcacionVehiculo.tenant_id == tenant_id,
            CargaEmbarcacionVehiculo.vehiculo_id == vehicle.id,
        ).limit(1)
    )
    if tiene_carga is None:
        raise HTTPException(409, "Asigna el peso y la embarcación de origen antes de despachar")
    tipos = _tipos_documento_vehiculo(session, tenant_id, op.id, vehicle.id)
    requeridos = {"guia_remitente", "guia_transportista", "acta_fiscalizacion", "formato_descarga"}
    faltantes = sorted(requeridos - tipos)
    if faltantes:
        raise HTTPException(409, f"Faltan documentos para el traslado: {', '.join(faltantes)}")
    vehicle.salida_muelle = datetime.now(UTC)
    vehicle.estado = "en_traslado"
    _historial(session, tenant_id, op.id, actor, "vehiculo_despachado", f"Traslado a planta iniciado a las {vehicle.salida_muelle.isoformat()}", vehicle.id)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.post("/vehiculos/{vehiculo_id}/planta/iniciar", response_model=VehiculoOut)
def iniciar_descarga_planta(
    vehiculo_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    hoy: HoyDep,
    actor: ActorDep,
) -> VehiculoPesca:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado != "en_traslado":
        raise HTTPException(409, "Registra la salida del muelle con carga y documentos antes del ingreso a planta")
    if vehicle.estado == "cerrado":
        raise HTTPException(409, "El registro del vehículo ya está cerrado")
    vehicle.fecha_reporte_planta = vehicle.fecha_reporte_planta or hoy
    vehicle.llegada_planta = vehicle.llegada_planta or datetime.now(UTC)
    vehicle.estado = "en_planta"
    _historial(session, tenant_id, vehicle.operacion_id, actor, "llegada_planta_registrada", f"Llegada real a planta: {vehicle.llegada_planta.isoformat()}", vehicle.id)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.post("/vehiculos/{vehiculo_id}/planta/descarga/iniciar", response_model=VehiculoOut)
def iniciar_descarga_en_planta(
    vehiculo_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> VehiculoPesca:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado != "en_planta" or vehicle.llegada_planta is None:
        raise HTTPException(409, "Registra primero la llegada real del vehículo a planta")
    if vehicle.inicio_planta is not None:
        raise HTTPException(409, "El inicio de descarga en planta ya está registrado")
    vehicle.inicio_planta = datetime.now(UTC)
    _historial(session, tenant_id, vehicle.operacion_id, actor, "descarga_planta_iniciada", f"Inicio real de descarga en planta: {vehicle.inicio_planta.isoformat()}", vehicle.id)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.patch("/vehiculos/{vehiculo_id}/planta/fechas", response_model=VehiculoOut)
def actualizar_tiempos_planta(
    vehiculo_id: uuid.UUID,
    datos: TiemposPlantaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> VehiculoPesca:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado not in {"en_traslado", "en_planta", "pendiente_evidencia"}:
        raise HTTPException(409, "Los horarios de planta se editan después del despacho y antes del cierre")
    antes = {
        "fecha_reporte_planta": str(vehicle.fecha_reporte_planta) if vehicle.fecha_reporte_planta else None,
        "llegada_planta": vehicle.llegada_planta.isoformat() if vehicle.llegada_planta else None,
        "inicio_planta": vehicle.inicio_planta.isoformat() if vehicle.inicio_planta else None,
        "fin_planta": vehicle.fin_planta.isoformat() if vehicle.fin_planta else None,
    }
    if "fecha_reporte_planta" in datos.model_fields_set:
        vehicle.fecha_reporte_planta = datos.fecha_reporte_planta
    if "llegada_planta" in datos.model_fields_set:
        vehicle.llegada_planta = datos.llegada_planta
    if "inicio_planta" in datos.model_fields_set:
        vehicle.inicio_planta = datos.inicio_planta
    if "fin_planta" in datos.model_fields_set:
        vehicle.fin_planta = datos.fin_planta
    if vehicle.salida_muelle and vehicle.llegada_planta and vehicle.llegada_planta < vehicle.salida_muelle:
        raise HTTPException(422, "La llegada a planta no puede ser anterior a la salida del muelle")
    if vehicle.inicio_planta and vehicle.llegada_planta is None:
        raise HTTPException(422, "Registra la llegada a planta antes del inicio de descarga")
    if vehicle.llegada_planta and vehicle.inicio_planta and vehicle.inicio_planta < vehicle.llegada_planta:
        raise HTTPException(422, "El inicio de descarga en planta no puede ser anterior a la llegada")
    if vehicle.inicio_planta and vehicle.fin_planta and vehicle.fin_planta < vehicle.inicio_planta:
        raise HTTPException(422, "El fin de descarga en planta no puede ser anterior al inicio")
    _historial(
        session,
        tenant_id,
        vehicle.operacion_id,
        actor,
        "fechas_planta_editadas",
        f"Antes: {antes}; ahora: fecha={vehicle.fecha_reporte_planta}, llegada={vehicle.llegada_planta}, inicio={vehicle.inicio_planta}, fin={vehicle.fin_planta}. Motivo: {datos.observacion}",
        vehicle.id,
    )
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.post("/vehiculos/{vehiculo_id}/cargas", status_code=201)
def agregar_carga(
    vehiculo_id: uuid.UUID,
    datos: CargaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> dict[str, str]:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    op = _operacion(session, tenant_id, vehicle.operacion_id)
    if op.estado != "en_descarga":
        raise HTTPException(409, "Primero completa la preparación y autoriza el inicio de descarga")
    if vehicle.estado != "pendiente_muelle":
        raise HTTPException(409, "La carga solo se puede modificar mientras el vehículo está en el muelle")
    descarga = session.scalar(
        select(DescargaEmbarcacion).where(
            DescargaEmbarcacion.id == datos.descarga_id,
            DescargaEmbarcacion.tenant_id == tenant_id,
            DescargaEmbarcacion.operacion_id == vehicle.operacion_id,
        )
    )
    if descarga is None:
        raise HTTPException(404, "La embarcación no pertenece a esta operación")
    session.add(
        CargaEmbarcacionVehiculo(
            tenant_id=tenant_id,
            descarga_id=descarga.id,
            vehiculo_id=vehicle.id,
            peso_muelle_kg=datos.peso_muelle_kg,
            cajas=datos.cajas,
            observacion=datos.observacion,
        )
    )
    _historial(session, tenant_id, vehicle.operacion_id, actor, "carga_asignada", "Carga de embarcación asignada al vehículo", vehicle.id)
    session.commit()
    return {"estado": "registrado", "vehiculo_id": str(vehicle.id)}


@router.post("/operaciones/{op_id}/documentos", response_model=DocumentoOut, status_code=201)
async def subir_documento(
    op_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    actor: ActorDep,
    archivo: UploadFile = File(...),
    tipo: str = Form(...),
    vehiculo_ids: list[uuid.UUID] = Form(default=[]),
    embarcacion_ids: list[uuid.UUID] = Form(default=[]),
) -> DocumentoPesca:
    op = _operacion(session, tenant_id, op_id)
    if tipo not in TIPOS_DOCUMENTO:
        raise HTTPException(422, "Tipo de documento no reconocido")
    if tipo == "factura" and (op.factura_serie is None or op.factura_correlativo is None):
        raise HTTPException(409, "Primero registra serie y correlativo de la factura después del cierre y del certificado de procedencia")
    mime = archivo.content_type or "application/octet-stream"
    if mime not in MIME_PERMITIDOS:
        raise HTTPException(415, "Solo se permiten PDF, JPG, PNG o WEBP")
    raw = await archivo.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Archivo demasiado grande")
    if not raw:
        raise HTTPException(422, "Archivo vacío")
    vehicles: list[VehiculoPesca] = []
    for vehicle_id in vehiculo_ids:
        vehicle = _vehiculo(session, tenant_id, vehicle_id)
        if vehicle.operacion_id != op.id:
            raise HTTPException(422, "Todos los vehículos deben pertenecer a la operación")
        vehicles.append(vehicle)
    vessels: list[EmbarcacionPesca] = []
    for vessel_id in embarcacion_ids:
        vessel = session.scalar(
            select(EmbarcacionPesca)
            .join(DescargaEmbarcacion, DescargaEmbarcacion.embarcacion_id == EmbarcacionPesca.id)
            .where(
                EmbarcacionPesca.id == vessel_id,
                EmbarcacionPesca.tenant_id == tenant_id,
                DescargaEmbarcacion.operacion_id == op.id,
                DescargaEmbarcacion.tenant_id == tenant_id,
            )
        )
        if vessel is None:
            raise HTTPException(422, "Todas las embarcaciones deben pertenecer a la operación")
        vessels.append(vessel)
    if tipo == "certificado_procedencia" and (vehicles or vessels):
        raise HTTPException(422, "El certificado de procedencia debe adjuntarse a toda la operación")
    digest = hashlib.sha256(raw).hexdigest()
    existente = session.scalar(
        select(DocumentoPesca).where(
            DocumentoPesca.tenant_id == tenant_id,
            DocumentoPesca.operacion_id == op.id,
            DocumentoPesca.tipo == tipo,
            DocumentoPesca.sha256 == digest,
        )
    )
    if existente is not None:
        for vehicle in vehicles:
            vinculo = session.get(VinculoDocumentoVehiculo, (existente.id, vehicle.id))
            if vinculo is None:
                session.add(VinculoDocumentoVehiculo(documento_id=existente.id, vehiculo_id=vehicle.id))
        for vessel in vessels:
            vinculo = session.get(VinculoDocumentoEmbarcacion, (existente.id, vessel.id))
            if vinculo is None:
                session.add(VinculoDocumentoEmbarcacion(documento_id=existente.id, embarcacion_id=vessel.id))
        if tipo == "factura" and op.factura_serie and op.factura_correlativo:
            op.estado_facturacion = "lista_para_pago"
        _historial(session, tenant_id, op.id, actor, "documento_reutilizado", f"{tipo}: {existente.nombre}")
        session.commit()
        session.refresh(existente)
        return existente
    path = almacen.guardar(tenant_id, digest, raw)
    doc = DocumentoPesca(
        tenant_id=tenant_id,
        operacion_id=op.id,
        vehiculo_id=vehicles[0].id if len(vehicles) == 1 else None,
        tipo=tipo,
        nombre=archivo.filename or "archivo",
        mime_type=mime,
        sha256=digest,
        ruta_storage=path,
        subido_por=actor[:200],
    )
    session.add(doc)
    session.flush()
    for vehicle in vehicles:
        session.add(VinculoDocumentoVehiculo(documento_id=doc.id, vehiculo_id=vehicle.id))
    for vessel in vessels:
        session.add(VinculoDocumentoEmbarcacion(documento_id=doc.id, embarcacion_id=vessel.id))
    if tipo == "factura" and op.factura_serie and op.factura_correlativo:
        op.estado_facturacion = "lista_para_pago"
    _historial(session, tenant_id, op.id, actor, "documento_cargado", f"{tipo}: {doc.nombre}")
    session.commit()
    session.refresh(doc)
    return doc


@router.get("/operaciones/{op_id}/documentos", response_model=list[DocumentoOut])
def listar_documentos_pesca(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> list[DocumentoPesca]:
    _operacion(session, tenant_id, op_id)
    return list(
        session.scalars(
            select(DocumentoPesca)
            .where(DocumentoPesca.operacion_id == op_id, DocumentoPesca.tenant_id == tenant_id)
            .order_by(DocumentoPesca.created_at)
        )
    )


@router.get("/operaciones/{op_id}/documentacion")
def revisar_documentacion(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> dict[str, object]:
    op = _operacion(session, tenant_id, op_id)
    vehicles = list(
        session.scalars(
            select(VehiculoPesca).where(
                VehiculoPesca.operacion_id == op.id, VehiculoPesca.tenant_id == tenant_id
            )
        )
    )
    docs = list(
        session.scalars(
            select(DocumentoPesca).where(
                DocumentoPesca.operacion_id == op.id, DocumentoPesca.tenant_id == tenant_id
            )
        )
    )
    vinculos_naves = set(
        session.scalars(
            select(VinculoDocumentoEmbarcacion.documento_id)
            .join(DocumentoPesca, DocumentoPesca.id == VinculoDocumentoEmbarcacion.documento_id)
            .where(DocumentoPesca.tenant_id == tenant_id, DocumentoPesca.operacion_id == op.id)
        )
    )
    documentos_globales = {doc.id for doc in docs if doc.vehiculo_id is None and doc.id not in vinculos_naves}
    requeridos = (
        "certificado_matricula",
        "permiso_pesca",
        "certificado_sanipes",
        "reporte_satelital",
        "visto_bueno_produce",
        "guia_remitente",
        "guia_transportista",
        "acta_fiscalizacion",
        "formato_descarga",
        "certificado_procedencia",
        "factura",
        "peso_planta",
    )
    salida = []
    for vehicle in vehicles:
        vinculados = set(
            session.scalars(
                select(VinculoDocumentoVehiculo.documento_id).where(
                    VinculoDocumentoVehiculo.vehiculo_id == vehicle.id
                )
            )
        )
        ids_embarcaciones = set(
            session.scalars(
                select(DescargaEmbarcacion.embarcacion_id)
                .join(CargaEmbarcacionVehiculo, CargaEmbarcacionVehiculo.descarga_id == DescargaEmbarcacion.id)
                .where(
                    DescargaEmbarcacion.tenant_id == tenant_id,
                    CargaEmbarcacionVehiculo.tenant_id == tenant_id,
                    CargaEmbarcacionVehiculo.vehiculo_id == vehicle.id,
                )
            )
        )
        documentos_nave = set(
            session.scalars(
                select(VinculoDocumentoEmbarcacion.documento_id).where(
                    VinculoDocumentoEmbarcacion.embarcacion_id.in_(ids_embarcaciones)
                )
            )
        ) if ids_embarcaciones else set()
        documentos_validos = documentos_globales | vinculados | documentos_nave | {
            doc.id for doc in docs if doc.vehiculo_id == vehicle.id
        }
        tipos_disponibles = {doc.tipo for doc in docs if doc.id in documentos_validos}
        faltantes = [tipo for tipo in requeridos if tipo not in tipos_disponibles]
        salida.append(
            {
                "vehiculo_id": vehicle.id,
                "placa": vehicle.placa,
                "documentacion_lista": not faltantes,
                "faltantes": faltantes,
                "estado_entrega": vehicle.estado,
            }
        )
    return {"operacion_id": op.id, "planta": op.planta, "vehiculos": salida}


@router.get("/documentos/{doc_id}/archivo")
def descargar_documento_pesca(
    doc_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep, almacen: AlmacenDep, actor: ActorDep
) -> FileResponse:
    doc = session.scalar(
        select(DocumentoPesca).where(
            DocumentoPesca.id == doc_id, DocumentoPesca.tenant_id == tenant_id
        )
    )
    if doc is None:
        raise HTTPException(404, "Documento no encontrado")
    if doc.operacion_id is None:
        movement = session.scalar(
            select(MovimientoPesca).where(
                MovimientoPesca.tenant_id == tenant_id,
                MovimientoPesca.comprobante_documento_id == doc.id,
                MovimientoPesca.clase == "prestamo_personal_bahia",
                MovimientoPesca.registrado_por == actor,
            )
        )
        if movement is None:
            raise HTTPException(404, "Documento no encontrado")
    return FileResponse(
        almacen.ruta_absoluta(doc.ruta_storage),
        media_type=doc.mime_type,
        filename=doc.nombre,
        content_disposition_type="inline" if doc.mime_type.startswith("image/") else "attachment",
        headers={"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/vehiculos/{vehiculo_id}/planta", response_model=RegistroPlantaOut)
def registrar_peso_planta(
    vehiculo_id: uuid.UUID,
    datos: RegistroPlantaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> RegistroPlanta:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado == "cerrado":
        raise HTTPException(409, "El registro de planta está cerrado")
    if vehicle.estado not in {"en_planta", "pendiente_evidencia"}:
        raise HTTPException(409, "Registra primero la llegada y el inicio de recepción en planta")
    if vehicle.inicio_planta is None:
        raise HTTPException(409, "Registra el inicio real de descarga en planta antes del pesaje")
    if datos.resultado in {"completo", "parcial"} and datos.peso_aceptado <= 0:
        raise HTTPException(422, "El peso aceptado debe ser mayor que cero para un resultado completo o parcial")
    record = session.scalar(
        select(RegistroPlanta).where(
            RegistroPlanta.tenant_id == tenant_id,
            RegistroPlanta.vehiculo_id == vehicle.id,
        )
    )
    antes = "registro creado"
    if record is None:
        record = RegistroPlanta(tenant_id=tenant_id, vehiculo_id=vehicle.id)
        session.add(record)
    else:
        if not datos.observacion:
            raise HTTPException(422, "Explique en observaciones el cambio del registro de planta")
        antes = f"resultado={record.resultado}, peso={record.peso_aceptado} {record.unidad}"
    record.resultado = datos.resultado
    record.peso_aceptado = datos.peso_aceptado
    record.unidad = datos.unidad
    record.cajas_rechazadas = datos.cajas_rechazadas
    record.motivo_rechazo = datos.motivo_rechazo
    record.fecha_finalizacion = (
        None
        if datos.no_registrar_fecha_finalizacion
        else datos.fecha_finalizacion or datetime.now(UTC)
    )
    record.observacion = datos.observacion
    vehicle.fin_planta = record.fecha_finalizacion
    vehicle.estado = "pendiente_evidencia"
    session.flush()
    _historial(
        session,
        tenant_id,
        vehicle.operacion_id,
        actor,
        "peso_planta_registrado",
        f"Antes: {antes}; ahora: {datos.resultado}, {datos.peso_aceptado} {datos.unidad}",
        vehicle.id,
    )
    session.commit()
    session.refresh(record)
    return record


@router.get("/vehiculos/{vehiculo_id}/comparacion-planta")
def comparar_pesos(
    vehiculo_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> dict[str, object]:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    record = session.scalar(select(RegistroPlanta).where(RegistroPlanta.vehiculo_id == vehicle.id))
    muelle = session.scalar(
        select(func.coalesce(func.sum(CargaEmbarcacionVehiculo.peso_muelle_kg), 0)).where(
            CargaEmbarcacionVehiculo.tenant_id == tenant_id,
            CargaEmbarcacionVehiculo.vehiculo_id == vehicle.id,
        )
    )
    if record is None:
        raise HTTPException(404, "Aún no hay peso de planta")
    aceptado_kg = record.peso_aceptado * FACTOR_KG[record.unidad]
    muelle_decimal = Decimal(muelle)
    diferencia = aceptado_kg - muelle_decimal
    color = "sin_comparacion" if muelle_decimal == 0 else "verde" if diferencia > 0 else "naranja" if diferencia == 0 else "rojo"
    return {
        "vehiculo_id": vehicle.id,
        "estado": color,
        "peso_aceptado_kg": aceptado_kg,
        "peso_muelle_kg": muelle_decimal if muelle_decimal else None,
        "diferencia_kg": diferencia if muelle_decimal else None,
    }


@router.post("/vehiculos/{vehiculo_id}/planta/cerrar", response_model=CierreOut)
def cerrar_registro_planta(
    vehiculo_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> CierreOut:
    vehicle = _vehiculo(session, tenant_id, vehiculo_id)
    if vehicle.estado == "cerrado":
        raise HTTPException(409, "El registro de planta ya está cerrado")
    if vehicle.estado != "pendiente_evidencia":
        raise HTTPException(409, "Registra el peso de planta antes de cerrar el vehículo")
    record = session.scalar(
        select(RegistroPlanta).where(RegistroPlanta.tenant_id == tenant_id, RegistroPlanta.vehiculo_id == vehicle.id)
    )
    if record is None:
        raise HTTPException(409, "Registre el resultado y peso de planta antes de cerrar")
    evidence = session.scalar(
        select(DocumentoPesca.id)
        .outerjoin(VinculoDocumentoVehiculo, VinculoDocumentoVehiculo.documento_id == DocumentoPesca.id)
        .where(
            DocumentoPesca.tenant_id == tenant_id,
            DocumentoPesca.operacion_id == vehicle.operacion_id,
            DocumentoPesca.tipo == "peso_planta",
            ((DocumentoPesca.vehiculo_id == vehicle.id) | (VinculoDocumentoVehiculo.vehiculo_id == vehicle.id)),
        )
        .limit(1)
    )
    if evidence is None:
        raise HTTPException(409, "Suba la foto o archivo del peso de planta antes de cerrar")
    if record.resultado in {"completo", "parcial"} and record.peso_aceptado <= 0:
        raise HTTPException(409, "El peso aceptado debe ser mayor que cero")
    vehicle.estado = "cerrado"
    _historial(session, tenant_id, vehicle.operacion_id, actor, "vehiculo_planta_cerrado", "Registro de planta cerrado con evidencia", vehicle.id)
    session.commit()
    return CierreOut(estado="cerrado", mensaje="Registro del vehículo cerrado")


@router.post("/operaciones/{op_id}/cerrar", response_model=CierreOut)
def cerrar_operacion(
    op_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> CierreOut:
    op = _operacion(session, tenant_id, op_id)
    if op.estado == "cerrada":
        raise HTTPException(409, "La operación ya está cerrada")
    vehicles = list(session.scalars(select(VehiculoPesca).where(VehiculoPesca.operacion_id == op.id)))
    if not vehicles:
        raise HTTPException(409, "La operación aún no tiene vehículos")
    pendientes = [vehicle.placa for vehicle in vehicles if vehicle.estado != "cerrado"]
    if pendientes:
        raise HTTPException(409, {"mensaje": "Hay registros de planta pendientes", "vehiculos": pendientes})
    op.estado = "cerrada"
    op.updated_at = datetime.now(UTC)
    _historial(session, tenant_id, op.id, actor, "operacion_cerrada", "Todos los vehículos tienen peso de planta y evidencia")
    session.commit()
    return CierreOut(estado="cerrada", mensaje="Operación cerrada")


@router.get("/operaciones/{op_id}/vehiculos", response_model=list[VehiculoOut])
def listar_vehiculos(op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep) -> list[VehiculoPesca]:
    _operacion(session, tenant_id, op_id)
    return list(session.scalars(select(VehiculoPesca).where(VehiculoPesca.operacion_id == op_id).order_by(VehiculoPesca.created_at)))


@router.get("/operaciones/{op_id}/historial")
def historial_operacion(op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep) -> list[dict[str, object]]:
    _operacion(session, tenant_id, op_id)
    rows = session.scalars(
        select(HistorialPesca).where(HistorialPesca.operacion_id == op_id, HistorialPesca.tenant_id == tenant_id).order_by(HistorialPesca.created_at)
    )
    return [
        {"id": row.id, "vehiculo_id": row.vehiculo_id, "accion": row.accion, "actor": row.actor, "detalle": row.detalle, "fecha": row.created_at}
        for row in rows
    ]


@router.get("/operaciones/{op_id}/resumen")
def resumen_operacion(
    op_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep
) -> dict[str, object]:
    op = _operacion(session, tenant_id, op_id)
    vehicles = list(
        session.scalars(
            select(VehiculoPesca).where(
                VehiculoPesca.operacion_id == op.id, VehiculoPesca.tenant_id == tenant_id
            )
        )
    )
    total_aceptado_kg = Decimal(0)
    total_muelle_kg = Decimal(0)
    detalle = []
    for vehicle in vehicles:
        plant = session.scalar(
            select(RegistroPlanta).where(
                RegistroPlanta.tenant_id == tenant_id,
                RegistroPlanta.vehiculo_id == vehicle.id,
            )
        )
        muelle_value = session.scalar(
            select(func.coalesce(func.sum(CargaEmbarcacionVehiculo.peso_muelle_kg), 0)).where(
                CargaEmbarcacionVehiculo.tenant_id == tenant_id,
                CargaEmbarcacionVehiculo.vehiculo_id == vehicle.id,
            )
        )
        muelle_kg = Decimal(muelle_value)
        accepted_kg = plant.peso_aceptado * FACTOR_KG[plant.unidad] if plant else Decimal(0)
        total_muelle_kg += muelle_kg
        total_aceptado_kg += accepted_kg
        detalle.append(
            {
                "vehiculo_id": vehicle.id,
                "placa": vehicle.placa,
                "chofer": vehicle.chofer,
                "estado": vehicle.estado,
                "resultado_planta": plant.resultado if plant else "pendiente",
                "peso_aceptado": plant.peso_aceptado if plant else None,
                "unidad": plant.unidad if plant else None,
                "peso_aceptado_kg": accepted_kg if plant else None,
                "peso_muelle_kg": muelle_kg if muelle_kg else None,
            }
        )
    return {
        "operacion_id": op.id,
        "fecha_reporte": op.fecha_reporte,
        "puerto": op.puerto,
        "muelle": op.muelle,
        "planta": op.planta,
        "estado": op.estado,
        "vehiculos": detalle,
        "total_peso_muelle_kg": total_muelle_kg,
        "total_peso_aceptado_planta_kg": total_aceptado_kg,
    }
