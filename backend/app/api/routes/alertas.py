from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro, TipoAlerta
from app.models import Alerta, Expediente, Miembro
from app.schemas import AlertaOut
from app.services.ambito_gerencia import alcance_expedientes_gerente
from app.services.expedientes import expediente_tiene_documentos_activos
from app.services.jerarquia_documental import nombres_jerarquia

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.get("", response_model=list[AlertaOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    resuelta: bool = False,
    tipo: TipoAlerta | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AlertaOut]:
    # Usar siempre el expediente para aplicar el ámbito real antes de paginar.
    consulta = (
        select(Alerta)
        .join(Expediente, Alerta.expediente_id == Expediente.id)
        .where(
            Alerta.tenant_id == tenant_id,
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
            expediente_tiene_documentos_activos(),
            Alerta.resuelta == resuelta,
        )
    )
    if auth.rol == "GESTOR":
        consulta = consulta.where(Expediente.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        consulta = consulta.where(Expediente.usuario_id == auth.usuario_id)
    elif auth.rol == RolMiembro.RESPONSABLE:
        if auth.miembro_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Responsable sin identidad")
        subordinados = select(Miembro.id).where(
            Miembro.tenant_id == tenant_id,
            Miembro.responsable_id == auth.miembro_id,
            Miembro.rol == RolMiembro.USUARIO,
            Miembro.deleted_at.is_(None),
        )
        consulta = consulta.where(Expediente.usuario_id.in_(subordinados))
    elif auth.rol == RolMiembro.GERENTE:
        consulta = consulta.where(alcance_expedientes_gerente(auth))
    if tipo is not None:
        consulta = consulta.where(Alerta.tipo == tipo)
    alertas = list(
        session.scalars(
            consulta.order_by(Alerta.created_at.desc(), Alerta.id).limit(limit).offset(offset)
        )
    )
    ids = {alerta.expediente_id for alerta in alertas}
    expedientes = {
        expediente.id: expediente
        for expediente in session.scalars(
            select(Expediente).where(Expediente.tenant_id == tenant_id, Expediente.id.in_(ids))
        )
    }
    ver_ruta = auth.rol in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
        RolMiembro.SECRETARIA,
        RolMiembro.RESPONSABLE,
    )
    jerarquias = (
        nombres_jerarquia(session, tenant_id, list(expedientes.values())) if ver_ruta else {}
    )
    resultado = []
    for alerta in alertas:
        expediente = expedientes[alerta.expediente_id]
        ruta = jerarquias.get(expediente.id, {})
        resultado.append(
            AlertaOut.model_validate(alerta).model_copy(
                update={
                    "cliente_nombre": expediente.receptor.razon_social,
                    "tipo_empresa": expediente.emisor.clasificacion_proveedor,
                    "fecha_emision": expediente.fecha_emision,
                    "moneda": expediente.moneda,
                    "importe_total": expediente.importe_total,
                    "responsable_nombre": ruta.get("responsable_nombre"),
                    "usuario_nombre": ruta.get("usuario_nombre"),
                    "gestor_nombre": ruta.get("gestor_nombre"),
                }
            )
        )
    return resultado
