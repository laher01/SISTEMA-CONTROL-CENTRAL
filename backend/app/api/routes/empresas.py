import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import HoyDep, SessionDep, SettingsDep, TenantDep
from app.api.errores import no_encontrado
from app.models import Empresa
from app.schemas import EmpresaActualizar, EmpresaOut
from app.services import auditoria
from app.services.expedientes import recalcular_expedientes

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.get("", response_model=list[EmpresaOut])
def listar(
    session: SessionDep, tenant_id: TenantDep, autorizada: bool | None = None
) -> list[Empresa]:
    consulta = select(Empresa).where(Empresa.tenant_id == tenant_id, Empresa.deleted_at.is_(None))
    if autorizada is not None:
        consulta = consulta.where(Empresa.autorizada == autorizada)
    return list(session.scalars(consulta.order_by(Empresa.razon_social)))


@router.patch("/{empresa_id}", response_model=EmpresaOut)
def actualizar(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    empresa_id: uuid.UUID,
    datos: EmpresaActualizar,
) -> Empresa:
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
