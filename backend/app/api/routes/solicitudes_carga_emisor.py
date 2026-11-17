"""Revisión de cargas de emisores ajenos: no son documentos fiscales activos."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import AlmacenDep, OperativeAuthDep, SessionDep, TenantDep
from app.models import AlertaManual, Gestor, Miembro, SolicitudCargaEmisor
from app.security import ContextoAcceso
from app.services import auditoria
from app.services.eliminacion import bloquear_clave_archivo

router = APIRouter(prefix="/solicitudes-carga-emisor", tags=["solicitudes-carga-emisor"])


class Decision(BaseModel):
    observacion: str | None = None


class SolicitudOut(BaseModel):
    id: uuid.UUID
    ruc_emisor: str
    estado: str
    gestor_propietario_id: uuid.UUID | None
    responsable_propietario_id: uuid.UUID | None


def _puede_revisar(auth: ContextoAcceso, solicitud: SolicitudCargaEmisor) -> bool:
    return bool(
        auth.rol == "ADMINISTRADOR"
        or (auth.rol == "RESPONSABLE" and auth.miembro_id == solicitud.responsable_propietario_id)
    )


class LoteEmisorOut(BaseModel):
    ruc_emisor: str
    gestor_solicitante_id: uuid.UUID | None
    cantidad_documentos: int
    cantidad_solicitudes: int


@router.get("/lotes", response_model=list[LoteEmisorOut])
def listar_lotes(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[LoteEmisorOut]:
    """Cola administrativa agrupada; ningún efecto contable ni cambio de titularidad."""
    if auth.rol != "ADMINISTRADOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración")
    modelo = SolicitudCargaEmisor
    filas = session.execute(
        select(
            modelo.ruc_emisor,
            modelo.gestor_solicitante_id,
            func.count(func.distinct(modelo.sha256_archivo)).label("cantidad_documentos"),
            func.count(modelo.id).label("cantidad_solicitudes"),
        )
        .where(modelo.tenant_id == tenant_id, modelo.estado == "PENDIENTE")
        .group_by(modelo.ruc_emisor, modelo.gestor_solicitante_id)
        .order_by(modelo.ruc_emisor, modelo.gestor_solicitante_id)
    )
    return [LoteEmisorOut(**fila._mapping) for fila in filas]


@router.get("/lotes/{ruc_emisor}", response_model=list[SolicitudOut])
def detalle_lote(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    ruc_emisor: str,
    gestor_solicitante_id: uuid.UUID | None = None,
    offset: int = 0,
    limite: int = 100,
) -> list[SolicitudCargaEmisor]:
    """Consulta paginada de integrantes de un lote, sin liberar documentos."""
    if auth.rol != "ADMINISTRADOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración")
    if offset < 0 or not 1 <= limite <= 200:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Paginación inválida")
    modelo = SolicitudCargaEmisor
    consulta = (
        select(modelo)
        .where(
            modelo.tenant_id == tenant_id,
            modelo.estado == "PENDIENTE",
            modelo.ruc_emisor == ruc_emisor,
            modelo.gestor_solicitante_id == gestor_solicitante_id,
        )
        .order_by(modelo.created_at, modelo.id)
        .offset(offset)
        .limit(limite)
    )
    return list(session.scalars(consulta))


class RechazoLoteIn(BaseModel):
    gestor_solicitante_id: uuid.UUID | None = None
    cantidad_esperada: int = Field(gt=0)
    observacion: str = Field(min_length=1, max_length=500)


@router.post("/lotes/{ruc_emisor}/rechazar")
def rechazar_lote(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    ruc_emisor: str,
    datos: RechazoLoteIn,
) -> dict[str, int]:
    """Cierra solicitudes en cuarentena sin borrar originales ni contabilizar."""
    if auth.rol != "ADMINISTRADOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración")
    motivo = datos.observacion.strip()
    if not motivo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Indique un motivo")
    bloquear_clave_archivo(
        session, tenant_id, f"emisor:{ruc_emisor}:gestor:{datos.gestor_solicitante_id}"
    )
    modelo = SolicitudCargaEmisor
    solicitudes = list(
        session.scalars(
            select(modelo)
            .where(
                modelo.tenant_id == tenant_id,
                modelo.ruc_emisor == ruc_emisor,
                modelo.gestor_solicitante_id == datos.gestor_solicitante_id,
                modelo.estado == "PENDIENTE",
            )
            .order_by(modelo.id)
            .with_for_update()
        )
    )
    if len(solicitudes) != datos.cantidad_esperada:
        raise HTTPException(status.HTTP_409_CONFLICT, "El lote cambió; actualice la revisión")
    if any(s.solicitante_cuenta_id == auth.cuenta_id for s in solicitudes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede decidir su propia solicitud")
    for solicitud in solicitudes:
        solicitud.estado = "RECHAZADA"
        solicitud.observacion = motivo
        solicitud.decidido_por_cuenta_id = auth.cuenta_id
        solicitud.decidido_at = datetime.now(UTC)
        auditoria.registrar(
            session,
            tenant_id,
            "CARGA_EMISOR_RECHAZADA",
            "solicitud_carga_emisor",
            solicitud.id,
            {"ruc_emisor": ruc_emisor, "por": auth.codigo, "lote": True},
        )
    session.commit()
    return {"rechazadas": len(solicitudes)}


class RevisionLoteIn(RechazoLoteIn):
    accion: Literal["VALIDAR_REVISION", "DERIVAR_REVISION"]
    gestor_destino_id: uuid.UUID
    referencia_sustento: str = Field(min_length=1, max_length=200)


@router.post("/lotes/{ruc_emisor}/resolver-revision")
def resolver_revision_lote(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    ruc_emisor: str,
    datos: RevisionLoteIn,
) -> dict[str, int]:
    """Resuelve la gestión documental, no la validez fiscal ni el asiento contable."""
    if auth.rol != "ADMINISTRADOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración")
    motivo = datos.observacion.strip()
    sustento = datos.referencia_sustento.strip()
    if not motivo or not sustento:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Indique motivo y sustento")
    bloquear_clave_archivo(
        session, tenant_id, f"emisor:{ruc_emisor}:gestor:{datos.gestor_solicitante_id}"
    )
    modelo = SolicitudCargaEmisor
    solicitudes = list(
        session.scalars(
            select(modelo)
            .where(
                modelo.tenant_id == tenant_id,
                modelo.ruc_emisor == ruc_emisor,
                modelo.gestor_solicitante_id == datos.gestor_solicitante_id,
                modelo.estado == "PENDIENTE",
            )
            .order_by(modelo.id)
            .with_for_update()
        )
    )
    if len(solicitudes) != datos.cantidad_esperada:
        raise HTTPException(status.HTTP_409_CONFLICT, "El lote cambió; actualice la revisión")
    if any(s.solicitante_cuenta_id == auth.cuenta_id for s in solicitudes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede decidir su propia solicitud")
    autorizados = (
        {datos.gestor_solicitante_id}
        if datos.accion == "VALIDAR_REVISION"
        else {s.gestor_propietario_id for s in solicitudes}
    )
    if autorizados != {datos.gestor_destino_id}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Destino no coincide con la cartera")
    gestor = session.scalar(
        select(Gestor).where(
            Gestor.id == datos.gestor_destino_id,
            Gestor.tenant_id == tenant_id,
            Gestor.deleted_at.is_(None),
        )
    )
    if gestor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gestor no disponible")
    usuario = session.get(Miembro, gestor.usuario_id) if gestor.usuario_id else None
    if usuario is None or usuario.tenant_id != tenant_id or usuario.deleted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Destino sin jerarquía válida")
    estado = "REVISION_VALIDADA" if datos.accion == "VALIDAR_REVISION" else "DERIVADA_REVISION"
    fecha = datetime.now(UTC)
    for solicitud in solicitudes:
        solicitud.estado = estado
        solicitud.observacion = motivo
        solicitud.decidido_por_cuenta_id = auth.cuenta_id
        solicitud.decidido_at = fecha
        auditoria.registrar(
            session,
            tenant_id,
            estado,
            "solicitud_carga_emisor",
            solicitud.id,
            {
                "ruc_emisor": ruc_emisor,
                "gestor_destino_id": str(gestor.id),
                "referencia_sustento": sustento,
                "por": auth.codigo,
                "efecto_contable": False,
            },
        )
    session.add(
        AlertaManual(
            tenant_id=tenant_id,
            creado_por_codigo=auth.codigo,
            creado_por_rol=auth.rol,
            destinatario_gestor_id=gestor.id,
            destinatario_usuario_id=usuario.id,
            para_administracion=True,
            asunto="Revisión documental asignada",
            mensaje=f"Proveedor {ruc_emisor}: {len(solicitudes)} archivos en revisión fiscal.",
        )
    )
    session.commit()
    return {"resueltas": len(solicitudes)}


@router.get("", response_model=list[SolicitudOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    estado: Literal["PENDIENTE", "APROBADA", "RECHAZADA", "REVISION_VALIDADA", "DERIVADA_REVISION"] = "PENDIENTE",
) -> list[SolicitudCargaEmisor]:
    consulta = select(SolicitudCargaEmisor).where(
        SolicitudCargaEmisor.tenant_id == tenant_id,
        SolicitudCargaEmisor.estado == estado,
    )
    if auth.rol == "RESPONSABLE":
        consulta = consulta.where(
            SolicitudCargaEmisor.responsable_propietario_id == auth.miembro_id
        )
    elif auth.rol != "ADMINISTRADOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración o Responsable")
    return list(session.scalars(consulta.order_by(SolicitudCargaEmisor.created_at.desc())))


@router.post("/{solicitud_id}/rechazar", response_model=SolicitudOut)
def rechazar(
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    solicitud_id: uuid.UUID,
    datos: Decision,
) -> SolicitudCargaEmisor:
    solicitud = session.scalar(
        select(SolicitudCargaEmisor)
        .where(
            SolicitudCargaEmisor.id == solicitud_id,
            SolicitudCargaEmisor.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if solicitud is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    if not _puede_revisar(auth, solicitud):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede decidir esta solicitud")
    if solicitud.solicitante_cuenta_id == auth.cuenta_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede decidir su propia solicitud")
    if solicitud.estado != "PENDIENTE":
        raise HTTPException(status.HTTP_409_CONFLICT, "Solicitud ya decidida")

    # Se conserva la ruta si no pudo borrarse, para permitir recuperación.
    ruta = solicitud.ruta_temporal
    if ruta:
        try:
            almacen.ruta_absoluta(ruta).unlink(missing_ok=True)
        except OSError as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "No se pudo eliminar el archivo en cuarentena",
            ) from exc
    solicitud.ruta_temporal = None
    solicitud.estado = "RECHAZADA"
    solicitud.observacion = datos.observacion
    solicitud.decidido_por_cuenta_id = auth.cuenta_id
    solicitud.decidido_at = datetime.now(UTC)
    auditoria.registrar(
        session,
        tenant_id,
        "CARGA_EMISOR_RECHAZADA",
        "solicitud_carga_emisor",
        solicitud.id,
        {"ruc_emisor": solicitud.ruc_emisor, "por": auth.codigo},
    )
    session.commit()
    return solicitud
