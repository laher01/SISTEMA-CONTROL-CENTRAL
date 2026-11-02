"""Pagos bancarios documentales distribuidos entre expedientes fiscales."""

import hashlib
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.models import (
    AsignacionPagoDocumental,
    Documento,
    Expediente,
    PagoDocumental,
    PermisoConfigurado,
)

router = APIRouter(prefix="/pagos-documentales", tags=["pagos documentales"])


class AsignacionPagoIn(BaseModel):
    expediente_id: uuid.UUID
    importe_asignado: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    evidencia: str = Field(min_length=1, max_length=500)
    confianza: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)


class PagoDocumentalCrearIn(BaseModel):
    documento_id: uuid.UUID
    asignaciones: list[AsignacionPagoIn] = Field(min_length=1, max_length=500)


class ConfirmarConciliacionIn(BaseModel):
    confirmar_referencias: bool


class PagoDocumentalActualizarIn(BaseModel):
    asignaciones: list[AsignacionPagoIn] = Field(min_length=1, max_length=500)


def _campo(documento: Documento, nombre: str) -> tuple[str | None, str | None, Decimal | None]:
    datos = documento.datos_extraidos or {}
    procesamiento = datos.get("procesamiento_documental")
    estructurada = (
        procesamiento.get("extraccion_estructurada") if isinstance(procesamiento, dict) else None
    )
    confirmada = datos.get("extraccion_confirmada")
    fuentes = [confirmada.get("campos") if isinstance(confirmada, dict) else None]
    fuentes.append(estructurada.get("campos") if isinstance(estructurada, dict) else None)
    for campos in fuentes:
        if not isinstance(campos, dict):
            continue
        valor = campos.get(nombre)
        if isinstance(valor, dict):
            texto = valor.get("valor")
            evidencia = valor.get("evidencia")
            try:
                decimal = (
                    Decimal(str(texto)) if nombre == "importe_total" and texto is not None else None
                )
            except (InvalidOperation, ValueError):
                decimal = None
            return (
                str(texto)[:300] if texto is not None else None,
                str(evidencia)[:500] if evidencia is not None else None,
                decimal,
            )
        if valor is not None:
            try:
                decimal = Decimal(str(valor)) if nombre == "importe_total" else None
            except (InvalidOperation, ValueError):
                decimal = None
            return str(valor)[:300], None, decimal
    return None, None, None


def _valor_confirmado_o_sugerido(documento: Documento, nombre: str) -> str | None:
    return _campo(documento, nombre)[0]


def _scope_documento(documento: Documento, auth: OperativeAuthDep) -> None:
    if auth.rol in {"ADMINISTRADOR", "SECRETARIA"}:
        return
    if auth.rol == "GESTOR" and documento.gestor_id == auth.gestor_id:
        return
    if auth.rol == "USUARIO" and documento.usuario_id == auth.usuario_id:
        return
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Comprobante no encontrado")


def _validar_permiso_modulo(session: Session, tenant_id: uuid.UUID, auth: OperativeAuthDep) -> None:
    if auth.rol == "SECRETARIA":
        permiso = session.scalar(
            select(PermisoConfigurado).where(
                PermisoConfigurado.tenant_id == tenant_id,
                PermisoConfigurado.rol == "SECRETARIA",
                PermisoConfigurado.permiso == "SECRETARIA_MENU_DOCUMENTOS",
            )
        )
        if permiso is not None and not permiso.habilitado:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Módulo documental desactivado")


def _scope_expediente(expediente: Expediente, auth: OperativeAuthDep) -> None:
    if auth.rol in {"ADMINISTRADOR", "SECRETARIA"}:
        return
    if auth.rol == "GESTOR" and expediente.gestor_id == auth.gestor_id:
        return
    if auth.rol == "USUARIO" and expediente.usuario_id == auth.usuario_id:
        return
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")


def _pago_out(
    session: Session, pago: PagoDocumental, destacado: uuid.UUID | None = None
) -> dict[str, object]:
    asignaciones = list(
        session.scalars(
            select(AsignacionPagoDocumental)
            .where(
                AsignacionPagoDocumental.tenant_id == pago.tenant_id,
                AsignacionPagoDocumental.pago_id == pago.id,
            )
            .order_by(AsignacionPagoDocumental.created_at, AsignacionPagoDocumental.id)
        )
    )
    total_asignado = sum((a.importe_asignado for a in asignaciones), Decimal("0.00"))
    documento = session.scalar(
        select(Documento).where(
            Documento.id == pago.documento_id,
            Documento.tenant_id == pago.tenant_id,
        )
    )
    tipo_ocr = _valor_confirmado_o_sugerido(documento, "tipo_operacion") if documento else None
    numero_ocr = _valor_confirmado_o_sugerido(documento, "numero_operacion") if documento else None
    tipo_operacion = pago.tipo_operacion
    if not tipo_operacion or tipo_operacion == "OTRO":
        tipo_operacion = tipo_ocr or tipo_operacion or "OTRO"
    return {
        "id": pago.id,
        "documento_id": pago.documento_id,
        "documento_nombre": documento.nombre_original if documento else None,
        "banco": pago.banco,
        "tipo_operacion": tipo_operacion,
        "fecha_hora": pago.fecha_hora,
        "numero_operacion": pago.numero_operacion or numero_ocr,
        "beneficiario": pago.beneficiario,
        "cuenta_beneficiario": pago.cuenta_beneficiario,
        "agencia": pago.agencia,
        "moneda": pago.moneda,
        "importe": pago.importe,
        "remitente": pago.remitente,
        "cuenta_remitente": pago.cuenta_remitente,
        "estado": pago.estado,
        "conciliado": pago.conciliado,
        "total_asignado": total_asignado,
        "diferencia": (pago.importe - total_asignado) if pago.importe is not None else None,
        "destacado_expediente_id": destacado,
        "asignaciones": [
            {
                "id": a.id,
                "expediente_id": a.expediente_id,
                "importe_asignado": a.importe_asignado,
                "evidencia": a.evidencia,
                "confianza": a.confianza,
                "referencia_confirmada": a.referencia_confirmada,
                "expediente": _expediente_out(session, pago.tenant_id, a.expediente_id),
            }
            for a in asignaciones
        ],
    }


def _expediente_out(
    session: Session, tenant_id: uuid.UUID, expediente_id: uuid.UUID
) -> dict[str, object] | None:
    expediente = session.scalar(
        select(Expediente).where(
            Expediente.id == expediente_id,
            Expediente.tenant_id == tenant_id,
        )
    )
    if expediente is None:
        return None
    return {
        "id": expediente.id,
        "serie": expediente.serie,
        "correlativo": expediente.correlativo,
        "moneda": expediente.moneda,
        "importe_total": expediente.importe_total,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_pago_documental(
    datos: PagoDocumentalCrearIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _validar_permiso_modulo(session, tenant_id, auth)
    documento = session.scalar(
        select(Documento).where(
            Documento.id == datos.documento_id,
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Voucher no encontrado")
    _scope_documento(documento, auth)
    if documento.tipo_documento != "VCHR":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "El documento debe ser un voucher"
        )

    existente = session.scalar(
        select(PagoDocumental).where(
            PagoDocumental.tenant_id == tenant_id,
            PagoDocumental.documento_id == documento.id,
        )
    )
    if existente is not None:
        return _pago_out(session, existente)

    pares: set[uuid.UUID] = set()
    asignaciones: list[tuple[Expediente, AsignacionPagoIn]] = []
    for asignacion in datos.asignaciones:
        if asignacion.expediente_id in pares:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Factura repetida en el pago"
            )
        pares.add(asignacion.expediente_id)
        expediente = session.scalar(
            select(Expediente)
            .where(
                Expediente.id == asignacion.expediente_id,
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if expediente is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Una de las facturas no está disponible")
        _scope_expediente(expediente, auth)
        asignaciones.append((expediente, asignacion))

    banco = _valor_confirmado_o_sugerido(documento, "banco")
    operacion = _valor_confirmado_o_sugerido(documento, "numero_operacion")
    fecha_texto = _valor_confirmado_o_sugerido(
        documento, "fecha_operacion"
    ) or _valor_confirmado_o_sugerido(documento, "fecha_emision")
    hora_texto = _valor_confirmado_o_sugerido(documento, "hora_operacion")
    moneda = _valor_confirmado_o_sugerido(documento, "moneda")
    importe = _campo(documento, "importe_total")[2]
    fecha_hora = None
    if fecha_texto:
        try:
            fecha = date.fromisoformat(fecha_texto[:10])
            if not hora_texto:
                hora = datetime.min.time()
            elif len(hora_texto) == 5:
                hora = datetime.strptime(hora_texto, "%H:%M").time()
            else:
                hora = datetime.strptime(hora_texto, "%H:%M:%S").time()
            fecha_hora = datetime.combine(fecha, hora)
        except ValueError:
            fecha_hora = None
    huella = None
    if banco and operacion and fecha_texto and importe is not None and moneda:
        huella = hashlib.sha256(
            "|".join(
                (banco.strip().upper(), operacion.strip(), fecha_texto[:10], moneda, str(importe))
            ).encode()
        ).hexdigest()
        repetido = session.scalar(
            select(PagoDocumental).where(
                PagoDocumental.tenant_id == tenant_id,
                PagoDocumental.huella_operacion == huella,
            )
        )
        if repetido is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Posible pago duplicado: ya existe un voucher con el mismo banco, operación, "
                "fecha e importe",
            )

    pago = PagoDocumental(
        tenant_id=tenant_id,
        documento_id=documento.id,
        huella_operacion=huella,
        banco=banco,
        tipo_operacion=_valor_confirmado_o_sugerido(documento, "tipo_operacion") or "OTRO",
        fecha_hora=fecha_hora,
        numero_operacion=operacion,
        beneficiario=_valor_confirmado_o_sugerido(documento, "beneficiario"),
        cuenta_beneficiario=_valor_confirmado_o_sugerido(documento, "cuenta_beneficiario"),
        agencia=_valor_confirmado_o_sugerido(documento, "agencia"),
        moneda=moneda,
        importe=importe,
        remitente=_valor_confirmado_o_sugerido(documento, "remitente"),
        cuenta_remitente=_valor_confirmado_o_sugerido(documento, "cuenta_remitente"),
        estado="PENDIENTE_REVISION",
    )
    session.add(pago)
    session.flush()
    for expediente, asignacion in asignaciones:
        if moneda and expediente.moneda != moneda:
            session.rollback()
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "La moneda no coincide con la factura"
            )
        pagado_previo = session.scalar(
            select(func.coalesce(func.sum(AsignacionPagoDocumental.importe_asignado), 0)).where(
                AsignacionPagoDocumental.tenant_id == tenant_id,
                AsignacionPagoDocumental.expediente_id == expediente.id,
            )
        ) or Decimal("0.00")
        if pagado_previo + asignacion.importe_asignado > expediente.importe_total:
            session.rollback()
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "La asignación excede el saldo documental de "
                f"{expediente.serie}-{expediente.correlativo}",
            )
        session.add(
            AsignacionPagoDocumental(
                tenant_id=tenant_id,
                pago_id=pago.id,
                expediente_id=expediente.id,
                importe_asignado=asignacion.importe_asignado,
                evidencia=asignacion.evidencia.strip(),
                confianza=asignacion.confianza,
                referencia_confirmada=False,
            )
        )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El pago o sus asignaciones ya existen"
        ) from exc
    session.refresh(pago)
    return _pago_out(session, pago)


@router.put("/{pago_id}/asignaciones")
def actualizar_asignaciones_pago(
    pago_id: uuid.UUID,
    datos: PagoDocumentalActualizarIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _validar_permiso_modulo(session, tenant_id, auth)
    pago = session.scalar(
        select(PagoDocumental)
        .where(
            PagoDocumental.id == pago_id,
            PagoDocumental.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if pago is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    documento = session.scalar(
        select(Documento).where(
            Documento.id == pago.documento_id,
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Voucher no encontrado")
    _scope_documento(documento, auth)
    if pago.conciliado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un pago conciliado no puede redistribuirse")
    pares: set[uuid.UUID] = set()
    nuevos: list[tuple[Expediente, AsignacionPagoIn]] = []
    for asignacion in datos.asignaciones:
        if asignacion.expediente_id in pares:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Factura repetida en el pago"
            )
        pares.add(asignacion.expediente_id)
        expediente = session.scalar(
            select(Expediente)
            .where(
                Expediente.id == asignacion.expediente_id,
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if expediente is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Una de las facturas no está disponible")
        _scope_expediente(expediente, auth)
        if pago.moneda and expediente.moneda != pago.moneda:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "La moneda no coincide con la factura"
            )
        previo = session.scalar(
            select(func.coalesce(func.sum(AsignacionPagoDocumental.importe_asignado), 0)).where(
                AsignacionPagoDocumental.tenant_id == tenant_id,
                AsignacionPagoDocumental.expediente_id == expediente.id,
                AsignacionPagoDocumental.pago_id != pago.id,
            )
        ) or Decimal("0.00")
        if previo + asignacion.importe_asignado > expediente.importe_total:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "La asignación supera el saldo de la factura"
            )
        nuevos.append((expediente, asignacion))
    session.query(AsignacionPagoDocumental).filter_by(tenant_id=tenant_id, pago_id=pago.id).delete(
        synchronize_session=False
    )
    for expediente, asignacion in nuevos:
        session.add(
            AsignacionPagoDocumental(
                tenant_id=tenant_id,
                pago_id=pago.id,
                expediente_id=expediente.id,
                importe_asignado=asignacion.importe_asignado,
                evidencia=asignacion.evidencia.strip(),
                confianza=asignacion.confianza,
                referencia_confirmada=False,
            )
        )
    pago.estado = "PENDIENTE_REVISION"
    session.commit()
    session.refresh(pago)
    return _pago_out(session, pago)


@router.get("/por-documento/{documento_id}")
def pagos_por_documento(
    documento_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[dict[str, object]]:
    _validar_permiso_modulo(session, tenant_id, auth)
    documento = session.scalar(
        select(Documento).where(
            Documento.id == documento_id,
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    _scope_documento(documento, auth)
    pagos = session.scalars(
        select(PagoDocumental).where(
            PagoDocumental.tenant_id == tenant_id,
            PagoDocumental.documento_id == documento.id,
        )
    )
    return [_pago_out(session, pago) for pago in pagos]


@router.get("/por-expediente/{expediente_id}")
def pagos_por_expediente(
    expediente_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[dict[str, object]]:
    _validar_permiso_modulo(session, tenant_id, auth)
    expediente = session.scalar(
        select(Expediente).where(
            Expediente.id == expediente_id,
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
        )
    )
    if expediente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    _scope_expediente(expediente, auth)
    pagos = session.scalars(
        select(PagoDocumental)
        .join(AsignacionPagoDocumental, AsignacionPagoDocumental.pago_id == PagoDocumental.id)
        .where(
            PagoDocumental.tenant_id == tenant_id,
            AsignacionPagoDocumental.tenant_id == tenant_id,
            AsignacionPagoDocumental.expediente_id == expediente.id,
        )
        .order_by(PagoDocumental.created_at.desc())
    )
    return [_pago_out(session, pago, expediente.id) for pago in pagos]


@router.post("/{pago_id}/conciliar")
def conciliar_pago_documental(
    pago_id: uuid.UUID,
    datos: ConfirmarConciliacionIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _validar_permiso_modulo(session, tenant_id, auth)
    pago = session.scalar(
        select(PagoDocumental)
        .where(
            PagoDocumental.id == pago_id,
            PagoDocumental.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if pago is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    documento = session.get(Documento, pago.documento_id)
    if documento is None or documento.tenant_id != tenant_id or documento.deleted_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Voucher no encontrado")
    _scope_documento(documento, auth)
    if not datos.confirmar_referencias:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Confirme expresamente las referencias"
        )
    asignaciones = list(
        session.scalars(
            select(AsignacionPagoDocumental).where(
                AsignacionPagoDocumental.tenant_id == tenant_id,
                AsignacionPagoDocumental.pago_id == pago.id,
            )
        )
    )
    total = sum((a.importe_asignado for a in asignaciones), Decimal("0.00"))
    if not asignaciones or pago.importe is None or total != pago.importe:
        diferencia = (pago.importe - total) if pago.importe is not None else None
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "mensaje": "La distribución no cuadra con el voucher",
                "importe_voucher": str(pago.importe) if pago.importe is not None else None,
                "total_asignado": str(total),
                "diferencia": str(diferencia) if diferencia is not None else None,
            },
        )
    for asignacion in asignaciones:
        asignacion.referencia_confirmada = True
    pago.estado = "CONCILIADO"
    pago.conciliado = True
    session.commit()
    session.refresh(pago)
    return _pago_out(session, pago)
