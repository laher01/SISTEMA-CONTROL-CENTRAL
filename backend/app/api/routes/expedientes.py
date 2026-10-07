import re
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from app.api.deps import HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.api.errores import no_encontrado
from app.enums import EstadoExpediente, RolMiembro
from app.models import Empresa, Expediente
from app.schemas import ExpedienteDetalle, ExpedienteIn, ExpedienteOut, Recalculo
from app.services.expedientes import (
    buscar_expediente,
    documentos_faltantes,
    fecha_limite,
    recalcular_expedientes,
)
from app.services.ingesta import crear_expediente

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
    if estado is not None:
        consulta = consulta.where(Expediente.estado == estado)
    if pendiente_aprobacion is not None:
        consulta = consulta.where(Expediente.pendiente_aprobacion == pendiente_aprobacion)
    if usuario_id is not None:
        consulta = consulta.where(Expediente.usuario_id == usuario_id)
    if gestor_id is not None:
        consulta = consulta.where(Expediente.gestor_id == gestor_id)
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
    consulta = consulta.order_by(Expediente.fecha_emision.desc()).limit(limit).offset(offset)
    return list(session.scalars(consulta))


@router.post("/recalcular", response_model=Recalculo)
def recalcular(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> Recalculo:
    if auth.rol not in (RolMiembro.ADMINISTRADOR, RolMiembro.SECRETARIA):
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
    if auth.rol == RolMiembro.USUARIO and expediente.usuario_id != auth.usuario_id:
        raise no_encontrado("Expediente")
    base = ExpedienteOut.model_validate(expediente)
    return ExpedienteDetalle(
        **base.model_dump(),
        documentos=[d for d in expediente.documentos if d.deleted_at is None],
        alertas=expediente.alertas,
        faltantes=documentos_faltantes(expediente, settings),
        fecha_limite=fecha_limite(expediente.fecha_emision, settings.dia_limite_expediente),
    )
