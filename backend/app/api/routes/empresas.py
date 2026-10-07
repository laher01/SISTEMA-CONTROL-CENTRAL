import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import exists, or_, select

from app.api.deps import HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.api.errores import no_encontrado
from app.enums import RolMiembro
from app.models import Empresa, Expediente
from app.schemas import EmpresaActualizar, EmpresaOut
from app.services import auditoria
from app.services.expedientes import recalcular_expedientes

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.get("", response_model=list[EmpresaOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    autorizada: bool | None = None,
) -> list[Empresa]:
    consulta = select(Empresa).where(Empresa.tenant_id == tenant_id, Empresa.deleted_at.is_(None))
    if auth.rol == "GESTOR":
        consulta = consulta.where(
            exists().where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                Expediente.gestor_id == auth.gestor_id,
                or_(Expediente.emisor_id == Empresa.id, Expediente.receptor_id == Empresa.id),
            )
        )
    elif auth.rol == RolMiembro.USUARIO:
        consulta = consulta.where(
            exists().where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                Expediente.usuario_id == auth.usuario_id,
                or_(Expediente.emisor_id == Empresa.id, Expediente.receptor_id == Empresa.id),
            )
        )
    if autorizada is not None:
        consulta = consulta.where(Empresa.autorizada == autorizada)
    return list(session.scalars(consulta.order_by(Empresa.razon_social)))


@router.patch("/{empresa_id}", response_model=EmpresaOut)
def actualizar(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    empresa_id: uuid.UUID,
    datos: EmpresaActualizar,
) -> Empresa:
    if auth.rol not in (RolMiembro.ADMINISTRADOR, RolMiembro.SECRETARIA):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para modificar Empresas")
    empresa = session.get(Empresa, empresa_id)
    if empresa is None or empresa.tenant_id != tenant_id or empresa.deleted_at:
        raise no_encontrado("Empresa")
    if datos.razon_social is not None:
        empresa.razon_social = datos.razon_social
    if datos.autorizada is not None:
        empresa.autorizada = datos.autorizada
    if datos.agente_retencion is not None:
        empresa.agente_retencion = datos.agente_retencion
    cambios: dict[str, object] = datos.model_dump(exclude_unset=True, exclude_none=True)
    auditoria.registrar(session, tenant_id, "EMPRESA_ACTUALIZADA", "empresa", empresa.id, cambios)
    recalcular_expedientes(session, tenant_id, hoy, settings, receptor_id=empresa.id)
    session.commit()
    return empresa
