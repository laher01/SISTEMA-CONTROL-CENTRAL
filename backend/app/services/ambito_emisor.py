"""Prevalidación de propiedad del emisor basada en asignaciones existentes.

Una asignación de pedido no implica titularidad permanente: los resultados
son evidencia provisional para el futuro flujo de autorización, NO permiso
para contabilizar automáticamente un documento.
"""
import uuid
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AsignacionPedidoGerencia, Empresa, PedidoGerencia


class EstadoAmbitoEmisor(StrEnum):
    SIN_ASIGNACION = "SIN_ASIGNACION"
    ASIGNADO_AL_GRUPO = "ASIGNADO_AL_GRUPO"
    ASIGNADO_A_OTRO_GRUPO = "ASIGNADO_A_OTRO_GRUPO"
    AMBIGUO = "AMBIGUO"


@dataclass(frozen=True)
class RevisionEmisor:
    estado: EstadoAmbitoEmisor
    empresa_id: uuid.UUID | None = None
    gestor_propietario_id: uuid.UUID | None = None
    responsable_propietario_id: uuid.UUID | None = None


def revisar_asignaciones_emisor(
    session: Session,
    tenant_id: uuid.UUID,
    ruc_emisor: str,
    usuario_id: uuid.UUID | None,
    gestor_id: uuid.UUID | None,
) -> RevisionEmisor:
    """Solo lee asignaciones de proveedores de pedidos ACTIVOS del mismo tenant.

    Si existen varios grupos propietarios, no elige uno arbitrariamente.
    No clasifica ausencia de asignación como autorización.
    """
    empresa = session.scalar(
        select(Empresa).where(
            Empresa.tenant_id == tenant_id,
            Empresa.ruc == ruc_emisor,
            Empresa.deleted_at.is_(None),
        )
    )
    if empresa is None:
        return RevisionEmisor(EstadoAmbitoEmisor.SIN_ASIGNACION)

    filas = session.execute(
        select(
            AsignacionPedidoGerencia.usuario_id,
            AsignacionPedidoGerencia.gestor_id,
            PedidoGerencia.responsable_id,
        )
        .join(PedidoGerencia, AsignacionPedidoGerencia.pedido_id == PedidoGerencia.id)
        .where(
            AsignacionPedidoGerencia.tenant_id == tenant_id,
            PedidoGerencia.tenant_id == tenant_id,
            AsignacionPedidoGerencia.proveedor_id == empresa.id,
            PedidoGerencia.estado == "ACTIVO",
        )
    ).all()
    grupos = set(filas)
    if not grupos:
        return RevisionEmisor(EstadoAmbitoEmisor.SIN_ASIGNACION, empresa.id)
    if len(grupos) > 1:
        return RevisionEmisor(EstadoAmbitoEmisor.AMBIGUO, empresa.id)

    propietario_usuario, propietario_gestor, propietario_responsable = next(iter(grupos))
    coincide = (
        gestor_id is not None and gestor_id == propietario_gestor
        or usuario_id is not None and usuario_id == propietario_usuario
    )
    return RevisionEmisor(
        EstadoAmbitoEmisor.ASIGNADO_AL_GRUPO if coincide
        else EstadoAmbitoEmisor.ASIGNADO_A_OTRO_GRUPO,
        empresa.id,
        propietario_gestor,
        propietario_responsable,
    )
