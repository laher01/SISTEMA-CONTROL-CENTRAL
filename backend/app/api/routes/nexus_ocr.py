"""API administrativa de la cola OCR; no expone originales ni permite despliegues."""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AlmacenDep, HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.enums import RolMiembro
from app.models import CasoOcr, Documento, ReglaOcr, ahora
from app.services import auditoria
from app.services.casos_ocr import clave_diagnostico, registrar_caso, serializar_caso
from app.services.ingesta import ComprobanteYaRegistrado
from app.services.procesamiento_documental import DocumentoNoProcesable
from app.services.reglas_ocr import validar_definicion

router = APIRouter(prefix="/nexus/ocr", tags=["nexus-ocr"])


def _admin(auth: OperativeAuthDep) -> None:
    if auth.rol not in (RolMiembro.ADMINISTRADOR, RolMiembro.SUPERADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo administradores")


@router.get("/casos")
def listar_casos(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[dict[str, object]]:
    _admin(auth)
    consulta = (
        select(CasoOcr)
        .where(CasoOcr.tenant_id == tenant_id)
        .order_by(CasoOcr.created_at.desc())
        .limit(100)
    )
    return [serializar_caso(caso) for caso in session.scalars(consulta)]


@router.get("/casos/{caso_id}")
def ver_caso(
    caso_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _admin(auth)
    caso = session.scalar(
        select(CasoOcr).where(CasoOcr.id == caso_id, CasoOcr.tenant_id == tenant_id)
    )
    if caso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Caso no encontrado")
    return {**serializar_caso(caso), "referencia_chat": clave_diagnostico(caso.id)}


@router.post("/documentos/{documento_id}/diagnostico")
def crear_diagnostico(
    documento_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    """Registra un fallo ya documentado; nunca ejecuta OCR ni crea expediente."""
    _admin(auth)
    documento = session.scalar(
        select(Documento).where(
            Documento.id == documento_id,
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    caso = registrar_caso(session, documento)
    if caso is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Documento sin fallo OCR diagnosticable")
    session.commit()
    return {**serializar_caso(caso), "referencia_chat": clave_diagnostico(caso.id)}


class ReglaOcrIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9_-]+$")
    version: int = Field(ge=1)
    definicion: dict[str, object]


class AprobarReglaIn(BaseModel):
    confirmacion: str


@router.post("/reglas")
def proponer_regla(
    datos: ReglaOcrIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _admin(auth)
    try:
        segura = validar_definicion(datos.definicion)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    existente = session.scalar(
        select(ReglaOcr).where(
            ReglaOcr.tenant_id == tenant_id,
            ReglaOcr.nombre == datos.nombre,
            ReglaOcr.version == datos.version,
        )
    )
    if existente is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Versión existente")
    regla = ReglaOcr(
        tenant_id=tenant_id,
        nombre=datos.nombre,
        version=datos.version,
        definicion=segura,
        estado="BORRADOR",
    )
    session.add(regla)
    session.flush()
    auditoria.registrar(
        session, tenant_id, "REGLA_OCR_PROPUESTA", "regla_ocr", regla.id,
        {"nombre": regla.nombre, "version": regla.version},
    )
    session.commit()
    return {"id": str(regla.id), "estado": regla.estado}


@router.post("/reglas/{regla_id}/aprobar")
def aprobar_regla(
    regla_id: uuid.UUID,
    datos: AprobarReglaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _admin(auth)
    if datos.confirmacion != "AUTORIZO REGLA OCR":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Confirmación requerida")
    regla = session.scalar(
        select(ReglaOcr)
        .where(ReglaOcr.id == regla_id, ReglaOcr.tenant_id == tenant_id)
        .with_for_update()
    )
    if regla is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada")
    if regla.estado != "BORRADOR":
        raise HTTPException(status.HTTP_409_CONFLICT, "Regla no está en borrador")
    validar_definicion(regla.definicion)
    regla.estado = "APROBADA"
    regla.aprobada_at = ahora()
    auditoria.registrar(
        session, tenant_id, "REGLA_OCR_APROBADA", "regla_ocr", regla.id,
        {"version": regla.version},
    )
    session.commit()
    return {"id": str(regla.id), "estado": regla.estado}


@router.get("/casos/{caso_id}/diagnostico-nexus")
def diagnostico_nexus(
    caso_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    """Resumen mínimo para asistentes autenticados; sin texto ni archivo original."""
    _admin(auth)
    caso = session.scalar(
        select(CasoOcr).where(CasoOcr.id == caso_id, CasoOcr.tenant_id == tenant_id)
    )
    if caso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Caso no encontrado")
    documento = session.scalar(
        select(Documento).where(
            Documento.tenant_id == tenant_id, Documento.id == caso.documento_id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    return {
        "referencia": clave_diagnostico(caso.id),
        "estado": caso.estado,
        "mime_type": documento.mime_type,
        "tipo_documento": documento.tipo_documento,
        "sha256": documento.sha256,
        "diagnostico": "Revisar extracción dentro de sesión autorizada",
        "exportable_a_github": False,
    }


class ReprocesarCasoIn(BaseModel):
    confirmacion: str


@router.post("/casos/{caso_id}/reprocesar")
def reprocesar_caso(
    caso_id: uuid.UUID,
    datos: ReprocesarCasoIn,
    session: SessionDep,
    settings: SettingsDep,
    almacen: AlmacenDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    """Reintento manual controlado: usa el mismo motor y el mismo documento original."""
    _admin(auth)
    if datos.confirmacion != "AUTORIZO REPROCESAR OCR":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Confirmación requerida")
    caso = session.scalar(
        select(CasoOcr)
        .where(CasoOcr.tenant_id == tenant_id, CasoOcr.id == caso_id)
        .with_for_update()
    )
    if caso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Caso no encontrado")
    if caso.estado == "REPROCESADO":
        return {"id": str(caso.id), "estado": caso.estado, "idempotente": True}
    if caso.intentos >= 3:
        raise HTTPException(status.HTTP_409_CONFLICT, "Límite de reintentos alcanzado")
    documento = session.scalar(
        select(Documento).where(
            Documento.tenant_id == tenant_id,
            Documento.id == caso.documento_id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    if documento.expediente_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Documento ya vinculado a expediente")
    # Se reutiliza el pipeline de producción; no se crea motor OCR alterno.
    from app.api.routes.documentos import _procesar_y_aplicar

    try:
        resultado = _procesar_y_aplicar(
            session, settings, almacen, hoy, documento,
            reutilizar=False, forzar_cache=True,
        )
    except DocumentoNoProcesable:
        session.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "OCR no procesable")
    except ComprobanteYaRegistrado:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Identidad fiscal duplicada")
    caso.intentos += 1
    caso.estado = "REPROCESADO" if resultado.relacionado else "VALIDACION"
    caso.ultimo_resultado = {
        "estado": resultado.estado,
        "relacionado": resultado.relacionado,
    }
    auditoria.registrar(
        session, tenant_id, "CASO_OCR_REPROCESADO", "documento", documento.id,
        {"caso_id": str(caso.id), "estado": caso.estado, "intentos": caso.intentos},
    )
    session.commit()
    return {"id": str(caso.id), "estado": caso.estado, "idempotente": False}
