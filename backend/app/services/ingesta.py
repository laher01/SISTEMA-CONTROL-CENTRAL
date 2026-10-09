import hashlib
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.enums import EstadoDocumento, Moneda, TipoComprobante, TipoDocumento
from app.models import (
    Documento,
    Expediente,
    GerenteEmpresa,
    GerenteResponsable,
    Gestor,
    Miembro,
    PedidoGerencia,
)
from app.services import auditoria
from app.services.expedientes import (
    actualizar_expediente,
    buscar_expediente,
    obtener_o_crear_empresa,
    requiere_bancarizacion,
)
from app.services.ubl import ComprobanteUbl, parece_xml, parse_ubl
from app.storage import AlmacenLocal


def atribuir_gerencia_inequivoca(session: Session, expediente: Expediente) -> None:
    """Solo asigna si exactamente un Pedido de Gerencia corresponde al expediente."""
    if expediente.gerente_id is not None or expediente.usuario_id is None:
        return
    usuario = session.get(Miembro, expediente.usuario_id)
    if usuario is None or usuario.responsable_id is None:
        return
    periodo = expediente.fecha_emision.replace(day=1)
    candidatos = list(
        session.scalars(
            select(PedidoGerencia)
            .join(
                GerenteResponsable,
                (GerenteResponsable.gerente_id == PedidoGerencia.gerente_id)
                & (GerenteResponsable.responsable_id == PedidoGerencia.responsable_id)
                & (GerenteResponsable.tenant_id == PedidoGerencia.tenant_id),
            )
            .join(
                GerenteEmpresa,
                (GerenteEmpresa.gerente_id == PedidoGerencia.gerente_id)
                & (GerenteEmpresa.empresa_id == PedidoGerencia.cliente_id)
                & (GerenteEmpresa.tenant_id == PedidoGerencia.tenant_id),
            )
            .where(
                PedidoGerencia.tenant_id == expediente.tenant_id,
                PedidoGerencia.responsable_id == usuario.responsable_id,
                PedidoGerencia.cliente_id == expediente.receptor_id,
                PedidoGerencia.periodo_mes == periodo,
                PedidoGerencia.moneda == expediente.moneda,
                PedidoGerencia.estado == "ACTIVO",
                PedidoGerencia.gerente_id.is_not(None),
                GerenteResponsable.activo.is_(True),
                GerenteEmpresa.activo.is_(True),
            )
        )
    )
    if len(candidatos) != 1:
        return
    pedido = candidatos[0]
    expediente.gerente_id = pedido.gerente_id
    expediente.pedido_gerencia_id = pedido.id
    auditoria.registrar(
        session,
        expediente.tenant_id,
        "EXPEDIENTE_GERENCIA_ATRIBUCION_AUTOMATICA",
        "expediente",
        expediente.id,
        {"gerente_id": str(pedido.gerente_id), "pedido_id": str(pedido.id)},
    )


class DocumentoDuplicado(Exception):
    def __init__(self, documento_id: uuid.UUID) -> None:
        super().__init__(f"Documento duplicado: {documento_id}")
        self.documento_id = documento_id


class ComprobanteYaRegistrado(Exception):
    def __init__(self, expediente_id: uuid.UUID) -> None:
        self.expediente_id = expediente_id
        super().__init__("El comprobante ya está registrado")


class ExpedienteNoEncontrado(Exception):
    pass


@dataclass(frozen=True)
class ArchivoSubido:
    nombre: str
    mime_type: str
    contenido: bytes


def ingerir_documento(
    session: Session,
    almacen: AlmacenLocal,
    settings: Settings,
    hoy: date,
    tenant_id: uuid.UUID,
    archivo: ArchivoSubido,
    tipo_documento: TipoDocumento | None = None,
    expediente_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    creado_por_cuenta_id: uuid.UUID | None = None,
) -> Documento:
    sha256 = hashlib.sha256(archivo.contenido).hexdigest()
    existente = session.scalar(
        select(Documento.id).where(Documento.tenant_id == tenant_id, Documento.sha256 == sha256)
    )
    if existente is not None:
        raise DocumentoDuplicado(existente)

    expediente: Expediente | None = None
    if expediente_id is not None:
        expediente = _expediente_del_tenant(session, tenant_id, expediente_id)

    comprobante = (
        parse_ubl(archivo.contenido) if parece_xml(archivo.nombre, archivo.contenido) else None
    )
    datos: dict[str, object] | None = None
    if comprobante is not None:
        if comprobante.tipo_documento == TipoDocumento.FACT:
            existente_comercial = buscar_expediente(
                session,
                tenant_id,
                TipoComprobante.FACT,
                comprobante.serie,
                comprobante.correlativo,
                comprobante.emisor.ruc,
                comprobante.receptor.ruc,
            )
            if existente_comercial is not None:
                raise ComprobanteYaRegistrado(existente_comercial.id)
        tipo_documento = comprobante.tipo_documento
        datos = comprobante.a_dict()
        expediente = _expediente_para_comprobante(
            session,
            settings,
            tenant_id,
            comprobante,
            gestor_id,
            usuario_id,
            creado_por_cuenta_id,
        )

    usuario_id = usuario_id or _usuario_de_gestor(session, tenant_id, gestor_id)
    if expediente is not None and usuario_id is None:
        usuario_id = expediente.usuario_id

    ruta = almacen.guardar(tenant_id, sha256, archivo.contenido)
    documento = Documento(
        tenant_id=tenant_id,
        expediente_id=expediente.id if expediente else None,
        tipo_documento=tipo_documento,
        estado=_estado_documento(tipo_documento, expediente),
        sha256=sha256,
        nombre_original=archivo.nombre[:500],
        mime_type=archivo.mime_type[:100],
        tamano_bytes=len(archivo.contenido),
        ruta_storage=ruta,
        datos_extraidos=datos,
        gestor_id=gestor_id,
        usuario_id=usuario_id,
        creado_por_cuenta_id=creado_por_cuenta_id,
    )
    session.add(documento)
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "DOCUMENTO_SUBIDO",
        "documento",
        documento.id,
        {"sha256": sha256, "tipo_documento": tipo_documento, "expediente_id": _str(expediente)},
    )
    if expediente is not None:
        actualizar_expediente(session, expediente, hoy, settings)
    return documento


def vincular_documento(
    session: Session,
    settings: Settings,
    hoy: date,
    documento: Documento,
    expediente_id: uuid.UUID,
    tipo_documento: TipoDocumento,
) -> Documento:
    expediente = _expediente_del_tenant(session, documento.tenant_id, expediente_id)
    anterior = documento.expediente
    documento.expediente_id = expediente.id
    documento.tipo_documento = tipo_documento
    if documento.usuario_id is None:
        documento.usuario_id = expediente.usuario_id
    if documento.gestor_id is None:
        documento.gestor_id = expediente.gestor_id
    documento.estado = EstadoDocumento.RELACIONADO
    auditoria.registrar(
        session,
        documento.tenant_id,
        "DOCUMENTO_VINCULADO",
        "documento",
        documento.id,
        {"expediente_id": str(expediente.id), "tipo_documento": tipo_documento},
    )
    actualizar_expediente(session, expediente, hoy, settings)
    if anterior is not None and anterior.id != expediente.id:
        actualizar_expediente(session, anterior, hoy, settings)
    return documento


def crear_expediente(
    session: Session,
    settings: Settings,
    hoy: date,
    tenant_id: uuid.UUID,
    receptor: tuple[str, str],
    emisor: tuple[str, str],
    tipo_comprobante: TipoComprobante,
    serie: str,
    correlativo: str,
    fecha_emision: date,
    moneda: Moneda,
    importe_total: Decimal,
    requiere_guia: bool,
    gestor_id: uuid.UUID | None,
    usuario_id: uuid.UUID | None = None,
    creado_por_cuenta_id: uuid.UUID | None = None,
) -> Expediente:
    empresa_receptora = obtener_o_crear_empresa(
        session, tenant_id, *receptor, tipo_relacion="CLIENTE"
    )
    empresa_emisora = obtener_o_crear_empresa(
        session, tenant_id, *emisor, tipo_relacion="PROVEEDOR"
    )
    usuario_id = usuario_id or _usuario_de_gestor(session, tenant_id, gestor_id)
    expediente = Expediente(
        tenant_id=tenant_id,
        receptor_id=empresa_receptora.id,
        emisor_id=empresa_emisora.id,
        tipo_comprobante=tipo_comprobante,
        serie=serie,
        correlativo=str(int(correlativo)),
        fecha_emision=fecha_emision,
        moneda=moneda,
        importe_total=importe_total,
        requiere_guia=(
            requiere_guia
            and tipo_comprobante == TipoComprobante.FACT
            and requiere_bancarizacion(moneda, importe_total, settings)
        ),
        gestor_id=gestor_id,
        usuario_id=usuario_id,
        creado_por_cuenta_id=creado_por_cuenta_id,
    )
    session.add(expediente)
    session.flush()
    atribuir_gerencia_inequivoca(session, expediente)
    auditoria.registrar(session, tenant_id, "EXPEDIENTE_CREADO", "expediente", expediente.id)
    actualizar_expediente(session, expediente, hoy, settings)
    return expediente


def _expediente_para_comprobante(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
    comprobante: ComprobanteUbl,
    gestor_id: uuid.UUID | None,
    usuario_id: uuid.UUID | None = None,
    creado_por_cuenta_id: uuid.UUID | None = None,
) -> Expediente | None:
    if comprobante.tipo_documento == TipoDocumento.FACT:
        expediente = buscar_expediente(
            session,
            tenant_id,
            TipoComprobante.FACT,
            comprobante.serie,
            comprobante.correlativo,
            comprobante.emisor.ruc,
            comprobante.receptor.ruc,
        )
        if expediente is not None:
            return expediente
        if comprobante.moneda is None or comprobante.importe_total is None:
            return None
        receptor = obtener_o_crear_empresa(
            session,
            tenant_id,
            comprobante.receptor.ruc,
            comprobante.receptor.razon_social,
            tipo_relacion="CLIENTE",
        )
        emisor = obtener_o_crear_empresa(
            session,
            tenant_id,
            comprobante.emisor.ruc,
            comprobante.emisor.razon_social,
            tipo_relacion="PROVEEDOR",
        )
        usuario_id = usuario_id or _usuario_de_gestor(session, tenant_id, gestor_id)
        expediente = Expediente(
            tenant_id=tenant_id,
            receptor_id=receptor.id,
            emisor_id=emisor.id,
            tipo_comprobante=TipoComprobante.FACT,
            serie=comprobante.serie,
            correlativo=comprobante.correlativo,
            fecha_emision=comprobante.fecha_emision,
            moneda=comprobante.moneda,
            importe_total=comprobante.importe_total,
            requiere_guia=requiere_bancarizacion(
                comprobante.moneda, comprobante.importe_total, settings
            ),
            gestor_id=gestor_id,
            usuario_id=usuario_id,
            creado_por_cuenta_id=creado_por_cuenta_id,
        )
        session.add(expediente)
        session.flush()
        atribuir_gerencia_inequivoca(session, expediente)
        auditoria.registrar(session, tenant_id, "EXPEDIENTE_CREADO", "expediente", expediente.id)
        return expediente

    referencia = comprobante.referencia
    if referencia is None:
        return None
    return buscar_expediente(
        session,
        tenant_id,
        TipoComprobante.FACT,
        referencia.serie,
        referencia.correlativo,
        referencia.emisor_ruc or comprobante.emisor.ruc,
        comprobante.receptor.ruc,
    )


def _expediente_del_tenant(
    session: Session, tenant_id: uuid.UUID, expediente_id: uuid.UUID
) -> Expediente:
    expediente = session.get(Expediente, expediente_id)
    if expediente is None or expediente.tenant_id != tenant_id or expediente.deleted_at:
        raise ExpedienteNoEncontrado(str(expediente_id))
    return expediente


def _estado_documento(
    tipo_documento: TipoDocumento | None, expediente: Expediente | None
) -> EstadoDocumento:
    if tipo_documento is None:
        return EstadoDocumento.PENDIENTE_CLASIFICACION
    if expediente is None:
        return EstadoDocumento.PENDIENTE_RELACION
    return EstadoDocumento.RELACIONADO


def _str(expediente: Expediente | None) -> str | None:
    return str(expediente.id) if expediente else None


def _usuario_de_gestor(
    session: Session, tenant_id: uuid.UUID, gestor_id: uuid.UUID | None
) -> uuid.UUID | None:
    if gestor_id is None:
        return None
    gestor = session.get(Gestor, gestor_id)
    if gestor is None or gestor.tenant_id != tenant_id or gestor.deleted_at is not None:
        return None
    return gestor.usuario_id
