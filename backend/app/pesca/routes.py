import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import AlmacenDep, HoyDep, SessionDep, SettingsDep, TenantDep
from app.pesca.models import (
    CargaEmbarcacionVehiculo,
    DescargaEmbarcacion,
    DocumentoPesca,
    EmbarcacionPesca,
    HistorialPesca,
    OperacionPesca,
    RegistroPlanta,
    VehiculoPesca,
    VinculoDocumentoVehiculo,
)
from app.pesca.schemas import (
    CargaIn,
    CierreOut,
    DescargaOut,
    DocumentoOut,
    EmbarcacionIn,
    OperacionIn,
    OperacionOut,
    RegistroPlantaIn,
    RegistroPlantaOut,
    TiemposPlantaIn,
    VehiculoIn,
    VehiculoOut,
)
from app.storage import AlmacenLocal

router = APIRouter(prefix="/pesca", tags=["operaciones de pesca"])
TIPOS_DOCUMENTO = {
    "guia_remitente",
    "guia_transportista",
    "acta_fiscalizacion",
    "formato_descarga",
    "certificado_procedencia",
    "certificado_captura",
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


def obtener_actor(
    identidad_access: Annotated[str | None, Header(alias="Cf-Access-Authenticated-User-Email")] = None,
    actor_local: Annotated[str | None, Header(alias="X-Actor")] = None,
) -> str:
    """Usa la identidad inyectada por Access; X-Actor queda para desarrollo local."""
    return (identidad_access or actor_local or "usuario_sistema")[:200]


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
        responsable_id=actor[:200],
        observacion=datos.observacion,
    )
    session.add(op)
    session.flush()
    _historial(session, tenant_id, op.id, actor, "operacion_creada", "Operación iniciada")
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


@router.post("/operaciones/{op_id}/embarcaciones", response_model=DescargaOut, status_code=201)
def agregar_embarcacion(
    op_id: uuid.UUID,
    datos: EmbarcacionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> DescargaOut:
    op = _operacion(session, tenant_id, op_id)
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
            patron_armador=datos.patron_armador,
            intermediario=datos.intermediario,
        )
        session.add(embarcacion)
        session.flush()
    else:
        embarcacion.nombre = datos.nombre
        embarcacion.patron_armador = datos.patron_armador
        embarcacion.intermediario = datos.intermediario
    descarga = DescargaEmbarcacion(
        tenant_id=tenant_id,
        operacion_id=op.id,
        embarcacion_id=embarcacion.id,
        inicio_descarga=datos.inicio_descarga,
        fin_descarga=datos.fin_descarga,
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
        matricula=embarcacion.matricula,
        nombre=embarcacion.nombre,
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
            matricula=vessel.matricula,
            nombre=vessel.nombre,
        )
        for descarga, vessel in rows
    ]


@router.post("/operaciones/{op_id}/vehiculos", response_model=VehiculoOut, status_code=201)
def agregar_vehiculo(
    op_id: uuid.UUID,
    datos: VehiculoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    actor: ActorDep,
) -> VehiculoPesca:
    op = _operacion(session, tenant_id, op_id)
    if op.estado == "cerrada":
        raise HTTPException(409, "La operación ya está cerrada")
    vehicle = VehiculoPesca(
        tenant_id=tenant_id,
        operacion_id=op_id,
        placa=datos.placa,
        tipo=datos.tipo,
        chofer=datos.chofer,
        fecha_reporte_planta=datos.fecha_reporte_planta,
        inicio_planta=datos.inicio_planta,
        turno=datos.turno,
    )
    session.add(vehicle)
    session.flush()
    _historial(session, tenant_id, op_id, actor, "vehiculo_agregado", f"Vehículo {datos.placa}", vehicle.id)
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
    if vehicle.estado == "cerrado":
        raise HTTPException(409, "El registro del vehículo ya está cerrado")
    vehicle.fecha_reporte_planta = vehicle.fecha_reporte_planta or hoy
    vehicle.inicio_planta = vehicle.inicio_planta or datetime.now(UTC)
    vehicle.estado = "en_planta"
    _historial(session, tenant_id, vehicle.operacion_id, actor, "planta_iniciada", "Ingreso e inicio de descarga en planta", vehicle.id)
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
    if vehicle.estado == "cerrado":
        raise HTTPException(409, "El registro del vehículo ya está cerrado")
    antes = {
        "fecha_reporte_planta": str(vehicle.fecha_reporte_planta) if vehicle.fecha_reporte_planta else None,
        "inicio_planta": vehicle.inicio_planta.isoformat() if vehicle.inicio_planta else None,
        "fin_planta": vehicle.fin_planta.isoformat() if vehicle.fin_planta else None,
    }
    if "fecha_reporte_planta" in datos.model_fields_set:
        vehicle.fecha_reporte_planta = datos.fecha_reporte_planta
    if "inicio_planta" in datos.model_fields_set:
        vehicle.inicio_planta = datos.inicio_planta
    if "fin_planta" in datos.model_fields_set:
        vehicle.fin_planta = datos.fin_planta
    _historial(
        session,
        tenant_id,
        vehicle.operacion_id,
        actor,
        "fechas_planta_editadas",
        f"Antes: {antes}; ahora: fecha={vehicle.fecha_reporte_planta}, inicio={vehicle.inicio_planta}, fin={vehicle.fin_planta}. Motivo: {datos.observacion}",
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
) -> DocumentoPesca:
    op = _operacion(session, tenant_id, op_id)
    if tipo not in TIPOS_DOCUMENTO:
        raise HTTPException(422, "Tipo de documento no reconocido")
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
    digest = hashlib.sha256(raw).hexdigest()
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
    requeridos = (
        "guia_remitente",
        "guia_transportista",
        "acta_fiscalizacion",
        "formato_descarga",
        "certificado_procedencia",
        "certificado_captura",
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
        tipos_disponibles = {
            doc.tipo
            for doc in docs
            if doc.vehiculo_id is None or doc.vehiculo_id == vehicle.id or doc.id in vinculados
        }
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
    doc_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep, almacen: AlmacenDep
) -> FileResponse:
    doc = session.scalar(
        select(DocumentoPesca).where(
            DocumentoPesca.id == doc_id, DocumentoPesca.tenant_id == tenant_id
        )
    )
    if doc is None:
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
    if datos.resultado == "completo" and datos.peso_aceptado <= 0:
        raise HTTPException(422, "El peso aceptado debe ser mayor que cero")
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
