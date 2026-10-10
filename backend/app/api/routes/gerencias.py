"""Vínculos operativos entre Gerentes y Responsables, controlados por Administración."""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import (
    Empresa,
    Expediente,
    GerenteEmpresa,
    GerenteResponsable,
    Miembro,
    PedidoGerencia,
)
from app.services import auditoria

router = APIRouter(prefix="/gerencias", tags=["gerencias"])


class VinculoIn(BaseModel):
    gerente_id: uuid.UUID
    responsable_id: uuid.UUID
    activo: bool = True


class VinculoOut(BaseModel):
    id: uuid.UUID
    gerente_id: uuid.UUID
    responsable_id: uuid.UUID
    activo: bool


def _administracion(auth: OperativeAuthDep) -> None:
    if auth.rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración puede asignar equipos")


def _miembro_activo(
    session: SessionDep, tenant_id: uuid.UUID, miembro_id: uuid.UUID, rol: str
) -> Miembro:
    miembro = session.get(Miembro, miembro_id)
    if (
        miembro is None
        or miembro.tenant_id != tenant_id
        or miembro.rol != rol
        or not miembro.activo
        or miembro.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Miembro no disponible")
    return miembro


@router.get("/vinculos", response_model=list[VinculoOut])
def vinculos(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[GerenteResponsable]:
    if auth.rol not in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
        RolMiembro.RESPONSABLE,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso")
    query = select(GerenteResponsable).where(GerenteResponsable.tenant_id == tenant_id)
    if auth.rol == RolMiembro.GERENTE:
        if auth.miembro_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Gerente sin identidad")
        query = query.where(GerenteResponsable.gerente_id == auth.miembro_id)
    if auth.rol == RolMiembro.RESPONSABLE:
        if auth.miembro_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Responsable sin identidad")
        query = query.where(GerenteResponsable.responsable_id == auth.miembro_id)
    return list(session.scalars(query.order_by(GerenteResponsable.created_at)))


@router.put("/vinculos", response_model=VinculoOut)
def asignar(
    datos: VinculoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> GerenteResponsable:
    _administracion(auth)
    _miembro_activo(session, tenant_id, datos.gerente_id, RolMiembro.GERENTE)
    _miembro_activo(session, tenant_id, datos.responsable_id, RolMiembro.RESPONSABLE)
    relacion = session.scalar(
        select(GerenteResponsable).where(
            GerenteResponsable.tenant_id == tenant_id,
            GerenteResponsable.gerente_id == datos.gerente_id,
            GerenteResponsable.responsable_id == datos.responsable_id,
        )
    )
    if relacion is None:
        relacion = GerenteResponsable(
            tenant_id=tenant_id,
            gerente_id=datos.gerente_id,
            responsable_id=datos.responsable_id,
            activo=datos.activo,
        )
        session.add(relacion)
    else:
        relacion.activo = datos.activo
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "GERENCIA_RESPONSABLE_VINCULO",
        "gerentes_responsables",
        relacion.id,
        {
            "gerente_id": str(datos.gerente_id),
            "responsable_id": str(datos.responsable_id),
            "activo": datos.activo,
            "actor": auth.codigo,
        },
    )
    session.commit()
    session.refresh(relacion)
    return relacion


class AtribucionFacturaIn(BaseModel):
    pedido_id: uuid.UUID


@router.put("/facturas/{expediente_id}/atribuir")
def atribuir_factura(
    expediente_id: uuid.UUID,
    datos: AtribucionFacturaIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    """Atribución explícita y auditable, solo Administración.

    Nunca asignar al Gerente por el RUC del cliente únicamente:
    varios Gerentes pueden trabajar con el mismo receptor.
    """
    _administracion(auth)
    expediente = session.get(Expediente, expediente_id)
    pedido = session.get(PedidoGerencia, datos.pedido_id)
    if (
        expediente is None
        or expediente.tenant_id != tenant_id
        or expediente.deleted_at is not None
        or pedido is None
        or pedido.tenant_id != tenant_id
        or pedido.gerente_id is None
        or pedido.responsable_id is None
        or pedido.estado != "ACTIVO"
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Factura o pedido inválido")
    if (
        expediente.receptor_id != pedido.cliente_id
        or expediente.moneda != pedido.moneda
        or expediente.fecha_emision.year != pedido.periodo_mes.year
        or expediente.fecha_emision.month != pedido.periodo_mes.month
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La factura no corresponde a cliente, moneda y mes del pedido",
        )
    usuario = session.get(Miembro, expediente.usuario_id) if expediente.usuario_id else None
    if usuario is None or usuario.responsable_id != pedido.responsable_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El Usuario no pertenece al Responsable",
        )
    autorizado = session.scalar(
        select(GerenteResponsable.id).where(
            GerenteResponsable.tenant_id == tenant_id,
            GerenteResponsable.gerente_id == pedido.gerente_id,
            GerenteResponsable.responsable_id == pedido.responsable_id,
            GerenteResponsable.activo.is_(True),
        )
    )
    if autorizado is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Gerencia y Responsable sin vínculo")
    if expediente.pedido_gerencia_id not in (None, pedido.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La factura ya pertenece a otro pedido; requiere regularización auditada",
        )
    expediente.pedido_gerencia_id = pedido.id
    expediente.gerente_id = pedido.gerente_id
    auditoria.registrar(
        session,
        tenant_id,
        "FACTURA_ATRIBUIDA_GERENCIA",
        "expediente",
        expediente.id,
        {
            "gerente_id": str(pedido.gerente_id),
            "pedido_id": str(pedido.id),
            "actor": auth.codigo,
        },
    )
    session.commit()
    return {"expediente_id": str(expediente.id), "pedido_id": str(pedido.id)}


class CarteraGerenteIn(BaseModel):
    gerente_id: uuid.UUID
    empresa_id: uuid.UUID
    activo: bool = True


class CarteraGerenteOut(BaseModel):
    id: uuid.UUID
    gerente_id: uuid.UUID
    empresa_id: uuid.UUID
    activo: bool


@router.get("/empresas", response_model=list[CarteraGerenteOut])
def listar_cartera(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[GerenteEmpresa]:
    if auth.rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR, RolMiembro.GERENTE):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso a cartera de Gerencia")
    consulta = select(GerenteEmpresa).where(GerenteEmpresa.tenant_id == tenant_id)
    if auth.rol == RolMiembro.GERENTE:
        if auth.miembro_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Gerente sin identidad")
        consulta = consulta.where(GerenteEmpresa.gerente_id == auth.miembro_id)
    return list(session.scalars(consulta.order_by(GerenteEmpresa.created_at)))


@router.put("/empresas", response_model=CarteraGerenteOut)
def asignar_cartera(
    datos: CarteraGerenteIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> GerenteEmpresa:
    _administracion(auth)
    _miembro_activo(session, tenant_id, datos.gerente_id, RolMiembro.GERENTE)
    empresa = session.get(Empresa, datos.empresa_id)
    if empresa is None or empresa.tenant_id != tenant_id or empresa.deleted_at is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Empresa inválida")
    relacion = session.scalar(
        select(GerenteEmpresa).where(
            GerenteEmpresa.tenant_id == tenant_id,
            GerenteEmpresa.gerente_id == datos.gerente_id,
            GerenteEmpresa.empresa_id == datos.empresa_id,
        )
    )
    if relacion is None:
        relacion = GerenteEmpresa(
            tenant_id=tenant_id,
            gerente_id=datos.gerente_id,
            empresa_id=datos.empresa_id,
            activo=datos.activo,
        )
        session.add(relacion)
    else:
        relacion.activo = datos.activo
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "CARTERA_GERENCIA_CAMBIADA",
        "gerentes_empresas",
        relacion.id,
        {
            "gerente_id": str(datos.gerente_id),
            "empresa_id": str(datos.empresa_id),
            "activo": datos.activo,
            "actor": auth.codigo,
        },
    )
    session.commit()
    session.refresh(relacion)
    return relacion



class AltaEmpresaCarteraIn(BaseModel):
    gerente_id: uuid.UUID | None = None
    ruc: str = Field(pattern=r"^[0-9]{11}$")
    razon_social: str = Field(min_length=3, max_length=300)
    tipo_relacion: str = Field(default="SIN_CLASIFICAR", pattern="^(CLIENTE|PROVEEDOR|AMBOS|SIN_CLASIFICAR)$")


class ImportarCarteraIn(BaseModel):
    gerente_id: uuid.UUID | None = None
    empresas: list[AltaEmpresaCarteraIn] = Field(min_length=1, max_length=500)


def _gerente_autorizado(
    session: SessionDep, tenant_id: uuid.UUID, auth: OperativeAuthDep,
    gerente_id: uuid.UUID | None,
) -> Miembro:
    if auth.rol == RolMiembro.GERENTE:
        if auth.miembro_id is None or (gerente_id is not None and gerente_id != auth.miembro_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede administrar otra Gerencia")
        gerente_id = auth.miembro_id
    else:
        _administracion(auth)
    if gerente_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Seleccione un Gerente")
    return _miembro_activo(session, tenant_id, gerente_id, RolMiembro.GERENTE)


def _registrar_empresa_cartera(
    session: SessionDep, tenant_id: uuid.UUID, auth: OperativeAuthDep,
    gerente: Miembro, datos: AltaEmpresaCarteraIn,
) -> tuple[Empresa, str]:
    empresa = session.scalar(
        select(Empresa).where(Empresa.tenant_id == tenant_id, Empresa.ruc == datos.ruc)
    )
    estado = "VINCULADA"
    if empresa is None:
        empresa = Empresa(
            tenant_id=tenant_id, ruc=datos.ruc,
            razon_social=datos.razon_social.strip(),
            tipo_relacion=datos.tipo_relacion,
        )
        session.add(empresa)
        session.flush()
        estado = "CREADA"
    elif empresa.deleted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "RUC archivado: solicitar revisión")
    # Los datos fiscales compartidos nunca se sobrescriben al importar.
    relacion = session.scalar(
        select(GerenteEmpresa).where(
            GerenteEmpresa.tenant_id == tenant_id,
            GerenteEmpresa.gerente_id == gerente.id,
            GerenteEmpresa.empresa_id == empresa.id,
        )
    )
    if relacion is None:
        session.add(GerenteEmpresa(
            tenant_id=tenant_id, gerente_id=gerente.id, empresa_id=empresa.id, activo=True
        ))
    else:
        relacion.activo = True
    auditoria.registrar(
        session, tenant_id, "CARTERA_EMPRESA_ALTA", "empresas", empresa.id,
        {"gerente_id": str(gerente.id), "ruc": datos.ruc, "estado": estado,
         "actor": auth.codigo},
    )
    return empresa, estado


@router.post("/empresas/alta", status_code=status.HTTP_201_CREATED)
def alta_empresa_cartera(
    datos: AltaEmpresaCarteraIn, session: SessionDep,
    tenant_id: TenantDep, auth: OperativeAuthDep,
) -> dict[str, str]:
    gerente = _gerente_autorizado(session, tenant_id, auth, datos.gerente_id)
    empresa, estado = _registrar_empresa_cartera(session, tenant_id, auth, gerente, datos)
    session.commit()
    return {"empresa_id": str(empresa.id), "resultado": estado}


@router.post("/empresas/importar")
def importar_empresas_cartera(
    datos: ImportarCarteraIn, session: SessionDep,
    tenant_id: TenantDep, auth: OperativeAuthDep,
) -> dict[str, int]:
    gerente = _gerente_autorizado(session, tenant_id, auth, datos.gerente_id)
    # Evitar duplicados dentro del mismo archivo antes de escribir.
    rucs = [item.ruc for item in datos.empresas]
    if len(rucs) != len(set(rucs)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "RUC duplicado en importación")
    creadas = 0
    vinculadas = 0
    for item in datos.empresas:
        empresa, estado = _registrar_empresa_cartera(session, tenant_id, auth, gerente, item)
        if estado == "CREADA":
            creadas += 1
        else:
            vinculadas += 1
    session.commit()
    return {"creadas": creadas, "vinculadas": vinculadas}


class RegularizarPedidoIn(BaseModel):
    gerente_id: uuid.UUID


@router.put("/pedidos/{pedido_id}/gerente")
def regularizar_pedido(
    pedido_id: uuid.UUID,
    datos: RegularizarPedidoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    """Asignación auditada de pedidos históricos sin Gerente identificado."""
    _administracion(auth)
    pedido = session.get(PedidoGerencia, pedido_id)
    if pedido is None or pedido.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    if pedido.gerente_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido ya tiene Gerente")
    _miembro_activo(session, tenant_id, datos.gerente_id, RolMiembro.GERENTE)
    cartera = session.scalar(
        select(GerenteEmpresa.id).where(
            GerenteEmpresa.tenant_id == tenant_id,
            GerenteEmpresa.gerente_id == datos.gerente_id,
            GerenteEmpresa.empresa_id == pedido.cliente_id,
            GerenteEmpresa.activo.is_(True),
        )
    )
    if cartera is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cliente no asignado al Gerente")
    if pedido.responsable_id is not None:
        vinculo = session.scalar(
            select(GerenteResponsable.id).where(
                GerenteResponsable.tenant_id == tenant_id,
                GerenteResponsable.gerente_id == datos.gerente_id,
                GerenteResponsable.responsable_id == pedido.responsable_id,
                GerenteResponsable.activo.is_(True),
            )
        )
        if vinculo is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Responsable no vinculado al Gerente")
    conflicto = session.scalar(
        select(PedidoGerencia.id).where(
            PedidoGerencia.tenant_id == tenant_id,
            PedidoGerencia.id != pedido.id,
            PedidoGerencia.gerente_id == datos.gerente_id,
            PedidoGerencia.cliente_id == pedido.cliente_id,
            PedidoGerencia.periodo_mes == pedido.periodo_mes,
            PedidoGerencia.moneda == pedido.moneda,
            PedidoGerencia.estado != "CANCELADO",
        )
    )
    if conflicto is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Pedido ya registrado para ese Gerente")
    ya_atribuido = session.scalar(
        select(Expediente.id).where(
            Expediente.tenant_id == tenant_id,
            Expediente.pedido_gerencia_id == pedido.id,
            Expediente.gerente_id.is_not(None),
        )
    )
    if ya_atribuido is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Pedido con facturas ya atribuidas")
    pedido.gerente_id = datos.gerente_id
    auditoria.registrar(
        session,
        tenant_id,
        "PEDIDO_GERENCIA_REGULARIZADO",
        "pedido_gerencia",
        pedido.id,
        {"gerente_id": str(datos.gerente_id), "actor": auth.codigo},
    )
    session.commit()
    return {"pedido_id": str(pedido.id), "gerente_id": str(datos.gerente_id)}
