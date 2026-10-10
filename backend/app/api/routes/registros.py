import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import aliased

from app.api.deps import AuthDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.enums import Moneda, RolMiembro, TipoDocumento
from app.models import Empresa, Expediente, Gestor, Miembro
from app.schemas import FiltroOpcion, RegistroFila, RegistroOpciones, RegistroResumen
from app.services.ambito_gerencia import alcance_expedientes_gerente
from app.services.expedientes import documentos_faltantes, documentos_principales, tipos_presentes
from app.services.permisos import PERMISO_ELIMINAR_REGISTROS, permiso_habilitado

router = APIRouter(prefix="/registros", tags=["registros"])

_OPCIONALES_BASE = [
    TipoDocumento.COT,
    TipoDocumento.OC,
    TipoDocumento.REQ,
    TipoDocumento.FOTO,
    TipoDocumento.GRT,
    TipoDocumento.RET,
]


@router.get("/opciones", response_model=RegistroOpciones)
def opciones(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: AuthDep,
) -> RegistroOpciones:
    responsables: list[FiltroOpcion] = []
    usuarios: list[FiltroOpcion] = []
    gestores: list[FiltroOpcion] = []

    if auth.rol in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
        RolMiembro.SECRETARIA,
    ):
        responsables = [FiltroOpcion(id=r.id, codigo=r.codigo, nombre=r.nombre) for r in session.scalars(select(Miembro).where(Miembro.tenant_id == tenant_id, Miembro.rol == RolMiembro.RESPONSABLE, Miembro.activo.is_(True), Miembro.deleted_at.is_(None)).order_by(Miembro.codigo))]
        usuarios = [
            FiltroOpcion(id=u.id, codigo=u.codigo, nombre=u.nombre, responsable_id=u.responsable_id)
            for u in session.scalars(
                select(Miembro)
                .where(
                    Miembro.tenant_id == tenant_id,
                    Miembro.rol == RolMiembro.USUARIO,
                    Miembro.activo.is_(True),
                    Miembro.deleted_at.is_(None),
                )
                .order_by(Miembro.codigo)
            )
        ]
        gestores = [
            FiltroOpcion(
                id=g.id,
                codigo=g.codigo,
                nombre=g.nombre,
                usuario_id=g.usuario_id,
            )
            for g in session.scalars(
                select(Gestor)
                .where(Gestor.tenant_id == tenant_id, Gestor.deleted_at.is_(None))
                .order_by(Gestor.codigo)
            )
        ]
    elif auth.rol == RolMiembro.RESPONSABLE:
        usuarios = [FiltroOpcion(id=u.id, codigo=u.codigo, nombre=u.nombre, responsable_id=u.responsable_id) for u in session.scalars(select(Miembro).where(Miembro.tenant_id == tenant_id, Miembro.responsable_id == auth.miembro_id, Miembro.rol == RolMiembro.USUARIO, Miembro.activo.is_(True), Miembro.deleted_at.is_(None)).order_by(Miembro.codigo))]
        gestores = [FiltroOpcion(id=g.id, codigo=g.codigo, nombre=g.nombre, usuario_id=g.usuario_id) for g in session.scalars(select(Gestor).where(Gestor.tenant_id == tenant_id, Gestor.usuario_id.in_([u.id for u in usuarios]), Gestor.deleted_at.is_(None)).order_by(Gestor.codigo))]
    elif auth.rol == RolMiembro.USUARIO:
        gestores = [
            FiltroOpcion(id=g.id, codigo=g.codigo, nombre=g.nombre)
            for g in session.scalars(
                select(Gestor)
                .where(
                    Gestor.tenant_id == tenant_id,
                    Gestor.usuario_id == auth.usuario_id,
                    Gestor.deleted_at.is_(None),
                )
                .order_by(Gestor.codigo)
            )
        ]
    if auth.rol == RolMiembro.GERENTE:
        ids_usuarios = set(
            session.scalars(
                select(Expediente.usuario_id).where(
                    Expediente.tenant_id == tenant_id,
                    alcance_expedientes_gerente(auth),
                    Expediente.deleted_at.is_(None),
                )
            )
        )
        ids_gestores = set(
            session.scalars(
                select(Expediente.gestor_id).where(
                    Expediente.tenant_id == tenant_id,
                    alcance_expedientes_gerente(auth),
                    Expediente.deleted_at.is_(None),
                )
            )
        )
        usuarios = [u for u in usuarios if u.id in ids_usuarios]
        gestores = [g for g in gestores if g.id in ids_gestores]
    return RegistroOpciones(responsables=responsables, usuarios=usuarios, gestores=gestores)


@router.get("", response_model=RegistroResumen)
def listar(
    session: SessionDep,
    settings: SettingsDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    usuario_id: uuid.UUID | None = None,
    gestor_id: uuid.UUID | None = None,
    tipo_empresa: Literal["A", "B"] | None = None,
    emisor: Annotated[str | None, Query(max_length=100)] = None,
    receptor: Annotated[str | None, Query(max_length=100)] = None,
    dia: date | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    mes: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RegistroResumen:
    _validar_filtros(auth.rol, usuario_id, gestor_id)

    usuario = aliased(Miembro)
    gestor = aliased(Gestor)
    emisor_empresa = aliased(Empresa)
    receptor_empresa = aliased(Empresa)

    consulta = (
        select(
            Expediente,
            usuario.codigo,
            usuario.nombre,
            gestor.codigo,
            gestor.nombre,
            emisor_empresa.ruc,
            emisor_empresa.razon_social,
            emisor_empresa.clasificacion_proveedor,
            receptor_empresa.ruc,
            receptor_empresa.razon_social,
        )
        .outerjoin(usuario, Expediente.usuario_id == usuario.id)
        .outerjoin(gestor, Expediente.gestor_id == gestor.id)
        .join(emisor_empresa, Expediente.emisor_id == emisor_empresa.id)
        .join(receptor_empresa, Expediente.receptor_id == receptor_empresa.id)
        .where(
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
        )
    )

    consulta = _aplicar_ambito(consulta, auth)
    if tipo_empresa is not None:
        consulta = consulta.where(emisor_empresa.clasificacion_proveedor == tipo_empresa)
    if usuario_id is not None and auth.rol in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
        RolMiembro.SECRETARIA,
    ):
        consulta = consulta.where(Expediente.usuario_id == usuario_id)
    if gestor_id is not None and auth.rol in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
        RolMiembro.SECRETARIA,
        RolMiembro.USUARIO,
    ):
        consulta = consulta.where(Expediente.gestor_id == gestor_id)
    if emisor and emisor.strip():
        texto_emisor = emisor.strip().lower()
        consulta = consulta.where(
            (func.lower(emisor_empresa.ruc).contains(texto_emisor, autoescape=True))
            | (func.lower(emisor_empresa.razon_social).contains(texto_emisor, autoescape=True))
        )
    if receptor and receptor.strip():
        texto_receptor = receptor.strip().lower()
        consulta = consulta.where(
            (func.lower(receptor_empresa.ruc).contains(texto_receptor, autoescape=True))
            | (func.lower(receptor_empresa.razon_social).contains(texto_receptor, autoescape=True))
        )
    if dia:
        consulta = consulta.where(Expediente.fecha_emision == dia)
    if fecha_desde:
        consulta = consulta.where(Expediente.fecha_emision >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.where(Expediente.fecha_emision <= fecha_hasta)
    if mes:
        anio, numero_mes = [int(x) for x in mes.split("-")]
        consulta = consulta.where(
            func.extract("year", Expediente.fecha_emision) == anio,
            func.extract("month", Expediente.fecha_emision) == numero_mes,
        )

    base = consulta.subquery()
    total = session.execute(
        select(
            func.count(base.c.id),
            func.coalesce(
                func.sum(case((base.c.moneda == Moneda.PEN, base.c.importe_total), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((base.c.moneda == Moneda.USD, base.c.importe_total), else_=0)),
                0,
            ),
        )
    ).one()

    filas_query = (
        consulta.order_by(
            Expediente.fecha_emision.desc(),
            Expediente.created_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    puede_eliminar_rol = permiso_habilitado(
        session,
        tenant_id,
        auth.rol,
        PERMISO_ELIMINAR_REGISTROS,
    )
    filas: list[RegistroFila] = []
    for (
        expediente,
        usuario_codigo,
        usuario_nombre,
        gestor_codigo,
        gestor_nombre,
        emisor_ruc_fila,
        emisor_nombre,
        clasificacion_proveedor,
        receptor_ruc_fila,
        receptor_nombre,
    ) in session.execute(filas_query):
        requeridos = documentos_principales(expediente, settings)
        presentes = [TipoDocumento(t) for t in tipos_presentes(expediente)]
        faltantes = documentos_faltantes(expediente, settings)
        opcionales = list(_OPCIONALES_BASE)
        for tipo in (TipoDocumento.GRR, TipoDocumento.VCHR):
            if tipo not in requeridos and tipo not in opcionales:
                opcionales.append(tipo)

        mostrar_propiedad = auth.rol != RolMiembro.GERENTE
        puede_eliminar = puede_eliminar_rol and (
            auth.rol != "GESTOR" or expediente.gestor_id == auth.gestor_id
        )
        filas.append(
            RegistroFila(
                expediente_id=expediente.id,
                estado=expediente.estado,
                usuario_id=expediente.usuario_id if mostrar_propiedad else None,
                usuario_codigo=usuario_codigo if mostrar_propiedad else None,
                usuario_nombre=usuario_nombre if mostrar_propiedad else None,
                gestor_id=expediente.gestor_id if mostrar_propiedad else None,
                gestor_codigo=gestor_codigo if mostrar_propiedad else None,
                gestor_nombre=gestor_nombre if mostrar_propiedad else None,
                fecha_emision=expediente.fecha_emision,
                tipo_comprobante=expediente.tipo_comprobante,
                serie=expediente.serie,
                correlativo=expediente.correlativo,
                tipo_empresa=clasificacion_proveedor,
                emisor_ruc=emisor_ruc_fila,
                emisor_razon_social=emisor_nombre,
                receptor_ruc=receptor_ruc_fila,
                receptor_razon_social=receptor_nombre,
                moneda=expediente.moneda,
                importe_total=expediente.importe_total,
                documentos_requeridos=requeridos,
                documentos_presentes=presentes,
                documentos_faltantes=faltantes,
                documentos_opcionales=opcionales,
                puede_eliminar=puede_eliminar,
            )
        )

    return RegistroResumen(
        filas=filas,
        total_registros=int(total[0] or 0),
        total_pen=Decimal(total[1] or 0),
        total_usd=Decimal(total[2] or 0),
    )


def _aplicar_ambito(consulta: Any, auth: OperativeAuthDep) -> Any:
    if auth.rol == "GESTOR":
        return consulta.where(Expediente.gestor_id == auth.gestor_id)
    if auth.rol == RolMiembro.USUARIO:
        return consulta.where(Expediente.usuario_id == auth.usuario_id)
    if auth.rol == RolMiembro.GERENTE:
        return consulta.where(alcance_expedientes_gerente(auth))
    return consulta


def _validar_filtros(
    rol: str,
    usuario_id: uuid.UUID | None,
    gestor_id: uuid.UUID | None,
) -> None:
    if rol == "GESTOR" and (usuario_id is not None or gestor_id is not None):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El Gestor no necesita ni puede cambiar Usuario o Gestor del filtro",
        )
    if rol == RolMiembro.USUARIO and usuario_id is not None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El Usuario ya está limitado a su propia información",
        )
