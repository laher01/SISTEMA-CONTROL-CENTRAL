import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import AlertaManual, Expediente, Gestor
from app.schemas import AlertaManualIn, AlertaManualOut
from app.services import auditoria

router = APIRouter(prefix="/mensajes-alerta", tags=["mensajes-alerta"])


@router.post("", response_model=AlertaManualOut, status_code=status.HTTP_201_CREATED)
def crear(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: AlertaManualIn,
) -> AlertaManual:
    if auth.rol not in (RolMiembro.SECRETARIA, RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo Secretaría o Administración puede emitir alertas manuales",
        )

    usuario_id = datos.destinatario_usuario_id
    gestor_id = datos.destinatario_gestor_id
    if datos.expediente_id is not None:
        expediente = session.get(Expediente, datos.expediente_id)
        if expediente is None or expediente.tenant_id != tenant_id or expediente.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
        usuario_id = usuario_id or expediente.usuario_id
        gestor_id = gestor_id or expediente.gestor_id

    if gestor_id is not None:
        gestor = session.get(Gestor, gestor_id)
        if gestor is None or gestor.tenant_id != tenant_id or gestor.deleted_at:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Gestor inválido")
        usuario_id = usuario_id or gestor.usuario_id

    if usuario_id is None and gestor_id is None and not datos.para_administracion:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La alerta necesita al menos un destinatario",
        )

    alerta = AlertaManual(
        tenant_id=tenant_id,
        expediente_id=datos.expediente_id,
        creado_por_codigo=auth.codigo,
        creado_por_rol=auth.rol,
        destinatario_usuario_id=usuario_id,
        destinatario_gestor_id=gestor_id,
        para_administracion=datos.para_administracion,
        asunto=datos.asunto.strip(),
        mensaje=datos.mensaje.strip(),
    )
    session.add(alerta)
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "ALERTA_MANUAL_CREADA",
        "alerta_manual",
        alerta.id,
        {
            "expediente_id": str(datos.expediente_id) if datos.expediente_id else None,
            "usuario_id": str(usuario_id) if usuario_id else None,
            "gestor_id": str(gestor_id) if gestor_id else None,
            "para_administracion": datos.para_administracion,
        },
    )
    session.commit()
    return alerta


@router.get("", response_model=list[AlertaManualOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    resuelta: bool | None = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[AlertaManual]:
    consulta = select(AlertaManual).where(AlertaManual.tenant_id == tenant_id)
    if resuelta is not None:
        consulta = consulta.where(AlertaManual.resuelta == resuelta)

    if auth.rol in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR):
        consulta = consulta.where(AlertaManual.para_administracion.is_(True))
    elif auth.rol == RolMiembro.SECRETARIA:
        pass
    elif auth.rol == RolMiembro.USUARIO:
        consulta = consulta.where(AlertaManual.destinatario_usuario_id == auth.usuario_id)
    elif auth.rol == "GESTOR":
        consulta = consulta.where(AlertaManual.destinatario_gestor_id == auth.gestor_id)
    else:
        consulta = consulta.where(or_(False))

    return list(session.scalars(consulta.order_by(AlertaManual.created_at.desc()).limit(limit)))


@router.patch("/{alerta_id}/resolver", response_model=AlertaManualOut)
def resolver(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    alerta_id: uuid.UUID,
) -> AlertaManual:
    alerta = session.get(AlertaManual, alerta_id)
    if alerta is None or alerta.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
    _validar_destinatario(auth, alerta)
    alerta.resuelta = True
    alerta.resuelta_at = datetime.now(UTC)
    auditoria.registrar(
        session,
        tenant_id,
        "ALERTA_MANUAL_RESUELTA",
        "alerta_manual",
        alerta.id,
        {"por": auth.codigo, "rol": auth.rol},
    )
    session.commit()
    return alerta


def _validar_destinatario(auth: OperativeAuthDep, alerta: AlertaManual) -> None:
    if auth.rol in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR, RolMiembro.SECRETARIA):
        return
    if auth.rol == RolMiembro.USUARIO and alerta.destinatario_usuario_id == auth.usuario_id:
        return
    if auth.rol == "GESTOR" and alerta.destinatario_gestor_id == auth.gestor_id:
        return
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
