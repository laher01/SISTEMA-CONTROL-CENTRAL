import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.enums import EstadoExpediente, Moneda, TipoAlerta, TipoComprobante, TipoDocumento
from app.models import Alerta, Empresa, Expediente, Tenant, ahora


def obtener_tenant(session: Session, nombre: str) -> Tenant:
    tenant = session.scalar(select(Tenant).where(Tenant.nombre == nombre))
    if tenant is None:
        tenant = Tenant(nombre=nombre)
        session.add(tenant)
        session.flush()
    return tenant


def obtener_o_crear_empresa(
    session: Session, tenant_id: uuid.UUID, ruc: str, razon_social: str
) -> Empresa:
    empresa = session.scalar(
        select(Empresa).where(Empresa.tenant_id == tenant_id, Empresa.ruc == ruc)
    )
    if empresa is None:
        empresa = Empresa(tenant_id=tenant_id, ruc=ruc, razon_social=razon_social)
        session.add(empresa)
        session.flush()
    return empresa


def buscar_expediente(
    session: Session,
    tenant_id: uuid.UUID,
    tipo_comprobante: TipoComprobante,
    serie: str,
    correlativo: str,
    emisor_ruc: str,
    receptor_ruc: str | None = None,
) -> Expediente | None:
    emisor = Empresa.__table__.alias("emisor")
    receptor = Empresa.__table__.alias("receptor")
    consulta = (
        select(Expediente)
        .join(emisor, Expediente.emisor_id == emisor.c.id)
        .join(receptor, Expediente.receptor_id == receptor.c.id)
        .where(
            Expediente.tenant_id == tenant_id,
            Expediente.tipo_comprobante == tipo_comprobante,
            Expediente.serie == serie,
            Expediente.correlativo == correlativo,
            Expediente.deleted_at.is_(None),
            emisor.c.ruc == emisor_ruc,
        )
    )
    if receptor_ruc is not None:
        consulta = consulta.where(receptor.c.ruc == receptor_ruc)
    return session.scalars(consulta).first()


def documentos_principales(expediente: Expediente) -> list[TipoDocumento]:
    requeridos = [TipoDocumento(expediente.tipo_comprobante)]
    if expediente.tipo_comprobante == TipoComprobante.FACT and expediente.requiere_guia:
        requeridos.append(TipoDocumento.GRR)
    requeridos.append(TipoDocumento.VCHR)
    return requeridos


def tipos_presentes(expediente: Expediente) -> set[str]:
    return {
        d.tipo_documento
        for d in expediente.documentos
        if d.deleted_at is None and d.tipo_documento is not None
    }


def documentos_faltantes(expediente: Expediente) -> list[TipoDocumento]:
    presentes = tipos_presentes(expediente)
    faltantes = [t for t in documentos_principales(expediente) if t not in presentes]
    if expediente.receptor.agente_retencion and TipoDocumento.RET not in presentes:
        faltantes.append(TipoDocumento.RET)
    return faltantes


def fecha_limite(fecha_emision: date, dia_limite: int) -> date:
    if fecha_emision.month == 12:
        return date(fecha_emision.year + 1, 1, dia_limite)
    return date(fecha_emision.year, fecha_emision.month + 1, dia_limite)


def requiere_bancarizacion(moneda: str, importe: Decimal, settings: Settings) -> bool:
    if moneda == Moneda.USD:
        return importe >= settings.umbral_bancarizacion_usd
    return importe >= settings.umbral_bancarizacion_pen


def calcular_estado(expediente: Expediente, hoy: date, settings: Settings) -> EstadoExpediente:
    presentes = tipos_presentes(expediente)
    falta_principal = any(t not in presentes for t in documentos_principales(expediente))
    if falta_principal:
        if hoy > fecha_limite(expediente.fecha_emision, settings.dia_limite_expediente):
            return EstadoExpediente.ROJO
        return EstadoExpediente.NARANJA
    if expediente.receptor.agente_retencion and TipoDocumento.RET not in presentes:
        return EstadoExpediente.AMARILLO
    return EstadoExpediente.VERDE


def alertas_activas(
    expediente: Expediente, estado: EstadoExpediente, settings: Settings
) -> dict[TipoAlerta, str]:
    presentes = tipos_presentes(expediente)
    numero = f"{expediente.serie}-{expediente.correlativo}"
    activas: dict[TipoAlerta, str] = {}
    if (
        requiere_bancarizacion(expediente.moneda, expediente.importe_total, settings)
        and TipoDocumento.VCHR not in presentes
    ):
        activas[TipoAlerta.BANCARIZACION_SIN_VOUCHER] = (
            f"{numero}: importe {expediente.moneda} {expediente.importe_total} "
            "requiere bancarización y no tiene Voucher."
        )
    if expediente.receptor.agente_retencion and TipoDocumento.RET not in presentes:
        activas[TipoAlerta.RETENCION_PENDIENTE] = (
            f"{numero}: el receptor es agente de retención y falta la constancia."
        )
    if not expediente.receptor.autorizada:
        activas[TipoAlerta.RECEPTOR_NO_AUTORIZADO] = (
            f"{numero}: el receptor {expediente.receptor.ruc} no está autorizado."
        )
    if estado == EstadoExpediente.ROJO:
        activas[TipoAlerta.EXPEDIENTE_VENCIDO] = (
            f"{numero}: venció el plazo y falta documentación principal."
        )
    return activas


def actualizar_expediente(
    session: Session, expediente: Expediente, hoy: date, settings: Settings
) -> None:
    session.flush()
    session.refresh(expediente, ["documentos", "alertas", "receptor"])
    estado = calcular_estado(expediente, hoy, settings)
    expediente.estado = estado
    expediente.pendiente_aprobacion = not expediente.receptor.autorizada
    _sincronizar_alertas(session, expediente, alertas_activas(expediente, estado, settings))


def _sincronizar_alertas(
    session: Session, expediente: Expediente, activas: dict[TipoAlerta, str]
) -> None:
    momento: datetime = ahora()
    existentes = {a.tipo: a for a in expediente.alertas}
    for tipo, alerta in existentes.items():
        if tipo in activas:
            alerta.mensaje = activas[TipoAlerta(tipo)]
            alerta.resuelta = False
            alerta.resuelta_at = None
        elif not alerta.resuelta:
            alerta.resuelta = True
            alerta.resuelta_at = momento
    for tipo, mensaje in activas.items():
        if tipo not in existentes:
            session.add(
                Alerta(
                    tenant_id=expediente.tenant_id,
                    expediente_id=expediente.id,
                    tipo=tipo,
                    mensaje=mensaje,
                )
            )


def recalcular_expedientes(
    session: Session,
    tenant_id: uuid.UUID,
    hoy: date,
    settings: Settings,
    receptor_id: uuid.UUID | None = None,
) -> int:
    consulta = select(Expediente).where(
        Expediente.tenant_id == tenant_id, Expediente.deleted_at.is_(None)
    )
    if receptor_id is not None:
        consulta = consulta.where(Expediente.receptor_id == receptor_id)
    expedientes = list(session.scalars(consulta))
    for expediente in expedientes:
        actualizar_expediente(session, expediente, hoy, settings)
    return len(expedientes)
