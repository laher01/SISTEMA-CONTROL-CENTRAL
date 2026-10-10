from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased

from app.core.config import Settings
from app.enums import RolMiembro
from app.models import (
    Documento,
    Empresa,
    Expediente,
    GerenteEmpresa,
    GerenteResponsable,
    Gestor,
    Miembro,
    PagoERP,
    PedidoGerencia,
)
from app.security import ContextoAcceso


@dataclass
class ContextoNexus:
    seccion: str
    ruta: str
    actor: dict[str, object]
    filtros: dict[str, list[str]]
    datos: dict[str, object] = field(default_factory=dict)
    advertencias: list[str] = field(default_factory=list)

    def a_prompt(self, max_chars: int) -> str:
        actor_minimo = {clave: valor for clave, valor in self.actor.items() if clave != "tenant_id"}
        partes = [
            f"SECCION={self.seccion}",
            f"RUTA={self.ruta}",
            f"ACTOR={actor_minimo}",
            f"FILTROS={self.filtros}",
            f"DATOS_AUTORIZADOS={self.datos}",
        ]
        if self.advertencias:
            partes.append(f"ADVERTENCIAS={self.advertencias}")
        texto = "\n".join(partes)
        return texto[:max_chars]


def construir_contexto(
    session: Session,
    settings: Settings,
    auth: ContextoAcceso,
    ruta: str,
    expediente_id: uuid.UUID | None,
) -> ContextoNexus:
    split = urlsplit(ruta)
    seccion = _seccion(split.path)
    contexto = ContextoNexus(
        seccion=seccion,
        ruta=ruta,
        actor={
            "codigo": auth.codigo,
            "nombre": auth.nombre,
            "rol": str(auth.rol),
            "tenant_id": str(auth.tenant_id),
            "usuario_id": str(auth.usuario_id) if auth.usuario_id else None,
            "gestor_id": str(auth.gestor_id) if auth.gestor_id else None,
            "proposito": f"asistencia_contextual:{seccion.lower()}",
            "base_autorizacion": f"rol_activo:{auth.rol}",
        },
        filtros=parse_qs(split.query, keep_blank_values=False),
    )

    hoy = settings.hoy()
    desde = date(hoy.year, hoy.month, 1)
    condiciones = condiciones_expedientes(session, auth)
    condiciones.extend(
        [
            Expediente.tenant_id == auth.tenant_id,
            Expediente.deleted_at.is_(None),
        ]
    )

    filas = session.execute(
        select(
            Expediente.moneda,
            func.count(Expediente.id),
            func.coalesce(func.sum(Expediente.importe_total), 0),
        )
        .where(*condiciones, Expediente.fecha_emision >= desde, Expediente.fecha_emision <= hoy)
        .group_by(Expediente.moneda)
    ).all()
    contexto.datos["mes_actual"] = {
        "desde": desde.isoformat(),
        "hasta": hoy.isoformat(),
        "compras": {
            str(moneda): {"expedientes": int(cantidad), "importe": str(Decimal(total or 0))}
            for moneda, cantidad, total in filas
        },
    }

    estados = session.execute(
        select(Expediente.estado, func.count(Expediente.id))
        .where(*condiciones)
        .group_by(Expediente.estado)
    ).all()
    contexto.datos["expedientes_por_estado"] = {
        str(estado): int(cantidad) for estado, cantidad in estados
    }

    if expediente_id is not None:
        _agregar_expediente(session, auth, contexto, expediente_id)

    if seccion == "REGISTROS":
        _agregar_registros(session, auth, contexto)
    elif seccion == "DOCUMENTOS":
        _agregar_documentos(session, auth, contexto)
    elif seccion == "EMPRESAS":
        _agregar_empresas(session, auth, contexto)
    elif seccion == "ORGANIZACION":
        _agregar_organizacion(session, auth, contexto)
    elif seccion == "PRODUCCION":
        _agregar_produccion(session, auth, contexto)
    elif seccion == "PAGOS":
        _agregar_pagos(session, auth, contexto, desde, hoy)

    return contexto


def _agregar_expediente(
    session: Session,
    auth: ContextoAcceso,
    contexto: ContextoNexus,
    expediente_id: uuid.UUID,
) -> None:
    expediente = session.get(Expediente, expediente_id)
    if expediente is None or expediente.tenant_id != auth.tenant_id or expediente.deleted_at:
        contexto.advertencias.append("El expediente indicado no existe dentro del Tenant activo.")
        return
    if not puede_ver_expediente(session, auth, expediente):
        contexto.advertencias.append("El expediente indicado está fuera del ámbito del actor.")
        return

    emisor = session.get(Empresa, expediente.emisor_id)
    receptor = session.get(Empresa, expediente.receptor_id)
    documentos = list(
        session.scalars(
            select(Documento).where(
                Documento.tenant_id == auth.tenant_id,
                Documento.expediente_id == expediente.id,
                Documento.deleted_at.is_(None),
            )
        )
    )
    contexto.datos["expediente_actual"] = {
        "id": str(expediente.id),
        "numero": f"{expediente.tipo_comprobante} {expediente.serie}-{expediente.correlativo}",
        "fecha_emision": expediente.fecha_emision.isoformat(),
        "moneda": expediente.moneda,
        "importe_total": str(expediente.importe_total),
        "estado": expediente.estado,
        "pendiente_aprobacion": expediente.pendiente_aprobacion,
        "emisor": (
            {"ruc": emisor.ruc, "razon_social": emisor.razon_social} if emisor is not None else None
        ),
        "receptor": (
            {"ruc": receptor.ruc, "razon_social": receptor.razon_social}
            if receptor is not None
            else None
        ),
        "documentos": [
            {
                "tipo": str(documento.tipo_documento) if documento.tipo_documento else None,
                "estado": str(documento.estado),
                "nombre": documento.nombre_original,
            }
            for documento in documentos
        ],
    }


def _agregar_registros(
    session: Session,
    auth: ContextoAcceso,
    contexto: ContextoNexus,
) -> None:
    emisor = aliased(Empresa)
    receptor = aliased(Empresa)
    condiciones = [
        Expediente.tenant_id == auth.tenant_id,
        Expediente.deleted_at.is_(None),
        *condiciones_expedientes(session, auth),
    ]
    filtros = contexto.filtros

    usuario_id = _uuid_filtro(filtros, "usuario_id")
    gestor_id = _uuid_filtro(filtros, "gestor_id")
    if usuario_id is not None and auth.rol in {
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
        RolMiembro.SECRETARIA,
    }:
        condiciones.append(Expediente.usuario_id == usuario_id)
    if gestor_id is not None and auth.rol in {
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
        RolMiembro.SECRETARIA,
        RolMiembro.USUARIO,
    }:
        condiciones.append(Expediente.gestor_id == gestor_id)

    consulta = (
        select(Expediente)
        .join(emisor, Expediente.emisor_id == emisor.id)
        .join(receptor, Expediente.receptor_id == receptor.id)
        .where(*condiciones)
    )
    texto_emisor = _primer_filtro(filtros, "emisor")
    if texto_emisor:
        texto = texto_emisor.lower()
        consulta = consulta.where(
            func.lower(emisor.ruc).contains(texto, autoescape=True)
            | func.lower(emisor.razon_social).contains(texto, autoescape=True)
        )
    texto_receptor = _primer_filtro(filtros, "receptor")
    if texto_receptor:
        texto = texto_receptor.lower()
        consulta = consulta.where(
            func.lower(receptor.ruc).contains(texto, autoescape=True)
            | func.lower(receptor.razon_social).contains(texto, autoescape=True)
        )

    dia = _fecha_filtro(filtros, "dia")
    desde = _fecha_filtro(filtros, "fecha_desde")
    hasta = _fecha_filtro(filtros, "fecha_hasta")
    mes = _primer_filtro(filtros, "mes")
    if dia is not None:
        consulta = consulta.where(Expediente.fecha_emision == dia)
    if desde is not None:
        consulta = consulta.where(Expediente.fecha_emision >= desde)
    if hasta is not None:
        consulta = consulta.where(Expediente.fecha_emision <= hasta)
    if mes and re_full_mes(mes):
        anio, numero_mes = (int(valor) for valor in mes.split("-", 1))
        consulta = consulta.where(
            func.extract("year", Expediente.fecha_emision) == anio,
            func.extract("month", Expediente.fecha_emision) == numero_mes,
        )

    tipo_empresa = _primer_filtro(filtros, "tipo_empresa")
    if tipo_empresa in {"A", "B"}:
        consulta = consulta.where(emisor.clasificacion_proveedor == tipo_empresa)

    base = consulta.subquery()
    total = session.execute(
        select(
            func.count(base.c.id),
            func.coalesce(
                func.sum(
                    case(
                        (base.c.moneda == "PEN", base.c.importe_total),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (base.c.moneda == "USD", base.c.importe_total),
                        else_=0,
                    )
                ),
                0,
            ),
        )
    ).one()

    muestra = list(
        session.scalars(
            consulta.order_by(
                Expediente.fecha_emision.desc(),
                Expediente.created_at.desc(),
            ).limit(8)
        )
    )
    contexto.datos["registros_filtrados"] = {
        "total_registros": int(total[0] or 0),
        "total_pen": str(Decimal(total[1] or 0)),
        "total_usd": str(Decimal(total[2] or 0)),
        "muestra": [
            {
                "numero": f"{item.tipo_comprobante} {item.serie}-{item.correlativo}",
                "fecha": item.fecha_emision.isoformat(),
                "moneda": item.moneda,
                "importe": str(item.importe_total),
            }
            for item in muestra
        ],
    }


def _agregar_produccion(
    session: Session,
    auth: ContextoAcceso,
    contexto: ContextoNexus,
) -> None:
    condiciones = [
        Expediente.tenant_id == auth.tenant_id,
        Expediente.deleted_at.is_(None),
        *condiciones_expedientes(session, auth),
    ]
    filas = session.execute(
        select(
            Miembro.codigo,
            Miembro.nombre,
            Gestor.codigo,
            Gestor.nombre,
            Expediente.moneda,
            func.count(Expediente.id),
            func.coalesce(func.sum(Expediente.importe_total), 0),
        )
        .outerjoin(Miembro, Expediente.usuario_id == Miembro.id)
        .outerjoin(Gestor, Expediente.gestor_id == Gestor.id)
        .where(*condiciones)
        .group_by(
            Miembro.codigo,
            Miembro.nombre,
            Gestor.codigo,
            Gestor.nombre,
            Expediente.moneda,
        )
        .order_by(func.sum(Expediente.importe_total).desc())
        .limit(12)
    ).all()
    contexto.datos["produccion_visible"] = [
        {
            "usuario": f"{usuario_codigo or 'SIN-USUARIO'} · {usuario_nombre or 'Sin usuario'}",
            "gestor": f"{gestor_codigo or 'SIN-GESTOR'} · {gestor_nombre or 'Sin gestor'}",
            "moneda": moneda,
            "expedientes": int(cantidad),
            "importe": str(Decimal(total or 0)),
        }
        for (
            usuario_codigo,
            usuario_nombre,
            gestor_codigo,
            gestor_nombre,
            moneda,
            cantidad,
            total,
        ) in filas
    ]


def _agregar_documentos(
    session: Session,
    auth: ContextoAcceso,
    contexto: ContextoNexus,
) -> None:
    condiciones = [
        Documento.tenant_id == auth.tenant_id,
        Documento.deleted_at.is_(None),
    ]
    if auth.rol == "GESTOR":
        condiciones.append(Documento.gestor_id == auth.gestor_id)
    else:
        usuarios = _usuarios_visibles(session, auth)
        if usuarios is not None:
            condiciones.append(Documento.usuario_id.in_(usuarios))
    filas = session.execute(
        select(Documento.estado, func.count(Documento.id))
        .where(*condiciones)
        .group_by(Documento.estado)
    ).all()
    contexto.datos["documentos_por_estado"] = {
        str(estado): int(cantidad) for estado, cantidad in filas
    }


def _agregar_empresas(
    session: Session,
    auth: ContextoAcceso,
    contexto: ContextoNexus,
) -> None:
    consulta = select(Empresa.tipo_relacion, func.count(Empresa.id)).where(
        Empresa.tenant_id == auth.tenant_id,
        Empresa.deleted_at.is_(None),
    )

    if auth.rol in {RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR}:
        pass
    elif auth.rol == RolMiembro.GERENTE and auth.miembro_id is not None:
        empresas = list(
            session.scalars(
                select(GerenteEmpresa.empresa_id).where(
                    GerenteEmpresa.tenant_id == auth.tenant_id,
                    GerenteEmpresa.gerente_id == auth.miembro_id,
                    GerenteEmpresa.activo.is_(True),
                )
            )
        )
        consulta = consulta.where(Empresa.id.in_(empresas))
    elif auth.rol == RolMiembro.RESPONSABLE:
        usuarios = _usuarios_visibles(session, auth) or []
        filas = session.execute(
            select(Expediente.emisor_id, Expediente.receptor_id).where(
                Expediente.tenant_id == auth.tenant_id,
                Expediente.deleted_at.is_(None),
                Expediente.usuario_id.in_(usuarios),
            )
        ).all()
        empresas = {
            empresa_id
            for emisor_id, receptor_id in filas
            for empresa_id in (emisor_id, receptor_id)
            if empresa_id is not None
        }
        consulta = consulta.where(Empresa.id.in_(empresas))
    else:
        contexto.advertencias.append(
            "NEXUS no amplió la vista maestra de Empresas porque el rol actual "
            "no tiene acceso administrativo a ese padrón."
        )
        return

    filas = session.execute(consulta.group_by(Empresa.tipo_relacion)).all()
    contexto.datos["empresas_por_relacion"] = {str(tipo): int(cantidad) for tipo, cantidad in filas}


def _agregar_organizacion(
    session: Session,
    auth: ContextoAcceso,
    contexto: ContextoNexus,
) -> None:
    if auth.rol in {RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR}:
        miembros = session.execute(
            select(Miembro.rol, func.count(Miembro.id))
            .where(
                Miembro.tenant_id == auth.tenant_id,
                Miembro.deleted_at.is_(None),
                Miembro.activo.is_(True),
            )
            .group_by(Miembro.rol)
        ).all()
        gestores = session.scalar(
            select(func.count(Gestor.id)).where(
                Gestor.tenant_id == auth.tenant_id,
                Gestor.deleted_at.is_(None),
            )
        )
        contexto.datos["organizacion"] = {
            "miembros_por_rol": {str(rol): int(cantidad) for rol, cantidad in miembros},
            "gestores": int(gestores or 0),
        }
    elif auth.rol == RolMiembro.GERENTE and auth.miembro_id is not None:
        responsables = list(
            session.scalars(
                select(GerenteResponsable.responsable_id).where(
                    GerenteResponsable.tenant_id == auth.tenant_id,
                    GerenteResponsable.gerente_id == auth.miembro_id,
                    GerenteResponsable.activo.is_(True),
                )
            )
        )
        usuarios = _usuarios_visibles(session, auth) or []
        contexto.datos["organizacion"] = {
            "responsables_vinculados": len(responsables),
            "usuarios_bajo_gerencia": len(usuarios),
        }
    elif auth.rol == RolMiembro.RESPONSABLE and auth.miembro_id is not None:
        usuarios = _usuarios_visibles(session, auth) or []
        gestores = session.scalar(
            select(func.count(Gestor.id)).where(
                Gestor.tenant_id == auth.tenant_id,
                Gestor.usuario_id.in_(usuarios),
                Gestor.deleted_at.is_(None),
            )
        )
        contexto.datos["organizacion"] = {
            "usuarios_propios": len(usuarios),
            "gestores_de_sus_usuarios": int(gestores or 0),
        }
    elif auth.rol == RolMiembro.USUARIO and auth.usuario_id is not None:
        gestores = session.scalar(
            select(func.count(Gestor.id)).where(
                Gestor.tenant_id == auth.tenant_id,
                Gestor.usuario_id == auth.usuario_id,
                Gestor.deleted_at.is_(None),
            )
        )
        contexto.datos["organizacion"] = {"gestores_propios": int(gestores or 0)}
    else:
        contexto.advertencias.append("El rol actual no posee vista organizacional ampliada.")


def _agregar_pagos(
    session: Session,
    auth: ContextoAcceso,
    contexto: ContextoNexus,
    desde: date,
    hasta: date,
) -> None:
    if auth.rol not in {
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
    }:
        contexto.advertencias.append(
            "Pagos ERP está restringido; NEXUS no recibió datos económicos de ese módulo."
        )
        return

    consulta_pedidos = select(
        func.count(PedidoGerencia.id),
        func.coalesce(func.sum(PedidoGerencia.monto_solicitado), 0),
    ).where(
        PedidoGerencia.tenant_id == auth.tenant_id,
        PedidoGerencia.periodo_mes == desde,
        PedidoGerencia.estado != "CANCELADO",
    )
    if auth.rol == RolMiembro.GERENTE:
        consulta_pedidos = consulta_pedidos.where(PedidoGerencia.gerente_id == auth.miembro_id)
    pedidos = session.execute(consulta_pedidos).one()

    liquidaciones: dict[str, dict[str, object]] = {}
    if auth.rol != RolMiembro.GERENTE:
        pagos = session.execute(
            select(
                PagoERP.estado,
                func.count(PagoERP.id),
                func.coalesce(func.sum(PagoERP.saldo), 0),
            )
            .where(
                PagoERP.tenant_id == auth.tenant_id,
                PagoERP.periodo_hasta >= desde,
                PagoERP.periodo_desde <= hasta,
            )
            .group_by(PagoERP.estado)
        ).all()
        liquidaciones = {
            str(estado): {
                "cantidad": int(cantidad),
                "saldo": str(Decimal(saldo or 0)),
            }
            for estado, cantidad, saldo in pagos
        }
    contexto.datos["pagos"] = {
        "pedidos_mes": int(pedidos[0] or 0),
        "monto_solicitado_mes": str(Decimal(pedidos[1] or 0)),
        "liquidaciones_por_estado": liquidaciones,
    }


def _usuarios_visibles(
    session: Session,
    auth: ContextoAcceso,
) -> list[uuid.UUID] | None:
    if auth.rol == RolMiembro.USUARIO:
        return [auth.usuario_id] if auth.usuario_id is not None else []
    if auth.rol == RolMiembro.RESPONSABLE and auth.miembro_id is not None:
        return list(
            session.scalars(
                select(Miembro.id).where(
                    Miembro.tenant_id == auth.tenant_id,
                    Miembro.responsable_id == auth.miembro_id,
                    Miembro.rol == RolMiembro.USUARIO,
                    Miembro.activo.is_(True),
                    Miembro.deleted_at.is_(None),
                )
            )
        )
    if auth.rol == RolMiembro.GERENTE and auth.miembro_id is not None:
        responsables = list(
            session.scalars(
                select(GerenteResponsable.responsable_id).where(
                    GerenteResponsable.tenant_id == auth.tenant_id,
                    GerenteResponsable.gerente_id == auth.miembro_id,
                    GerenteResponsable.activo.is_(True),
                )
            )
        )
        return list(
            session.scalars(
                select(Miembro.id).where(
                    Miembro.tenant_id == auth.tenant_id,
                    Miembro.responsable_id.in_(responsables),
                    Miembro.rol == RolMiembro.USUARIO,
                    Miembro.activo.is_(True),
                    Miembro.deleted_at.is_(None),
                )
            )
        )
    if auth.rol == "GESTOR":
        return [auth.usuario_id] if auth.usuario_id is not None else []
    return None


def condiciones_expedientes(
    session: Session,
    auth: ContextoAcceso,
) -> list[Any]:
    condiciones: list[Any] = []
    if auth.rol == "GESTOR":
        condiciones.append(Expediente.gestor_id == auth.gestor_id)
    else:
        usuarios = _usuarios_visibles(session, auth)
        if usuarios is not None:
            condiciones.append(Expediente.usuario_id.in_(usuarios))
    return condiciones


def puede_ver_expediente(
    session: Session,
    auth: ContextoAcceso,
    expediente: Expediente,
) -> bool:
    if auth.rol == "GESTOR":
        return expediente.gestor_id == auth.gestor_id

    usuarios = _usuarios_visibles(session, auth)
    if usuarios is not None:
        return expediente.usuario_id in usuarios
    return True


def puede_ver_empresa(
    session: Session,
    auth: ContextoAcceso,
    empresa: Empresa,
) -> bool:
    if empresa.tenant_id != auth.tenant_id or empresa.deleted_at is not None:
        return False
    if auth.rol in {RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR}:
        return True
    if auth.rol == RolMiembro.GERENTE and auth.miembro_id is not None:
        vinculada = session.scalar(
            select(GerenteEmpresa.id).where(
                GerenteEmpresa.tenant_id == auth.tenant_id,
                GerenteEmpresa.gerente_id == auth.miembro_id,
                GerenteEmpresa.empresa_id == empresa.id,
                GerenteEmpresa.activo.is_(True),
            )
        )
        if vinculada is not None:
            return True

    condiciones = condiciones_expedientes(session, auth)
    visible = session.scalar(
        select(Expediente.id)
        .where(
            Expediente.tenant_id == auth.tenant_id,
            Expediente.deleted_at.is_(None),
            *condiciones,
            ((Expediente.emisor_id == empresa.id) | (Expediente.receptor_id == empresa.id)),
        )
        .limit(1)
    )
    return visible is not None


def _primer_filtro(filtros: dict[str, list[str]], clave: str) -> str | None:
    valores = filtros.get(clave)
    if not valores:
        return None
    valor = valores[0].strip()
    return valor or None


def _uuid_filtro(filtros: dict[str, list[str]], clave: str) -> uuid.UUID | None:
    valor = _primer_filtro(filtros, clave)
    if valor is None:
        return None
    try:
        return uuid.UUID(valor)
    except ValueError:
        return None


def _fecha_filtro(filtros: dict[str, list[str]], clave: str) -> date | None:
    valor = _primer_filtro(filtros, clave)
    if valor is None:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def re_full_mes(valor: str) -> bool:
    if len(valor) != 7 or valor[4] != "-":
        return False
    try:
        anio = int(valor[:4])
        numero_mes = int(valor[5:])
    except ValueError:
        return False
    return anio >= 2000 and 1 <= numero_mes <= 12


def _seccion(path: str) -> str:
    limpio = path.strip("/").split("/", 1)[0].lower()
    return {
        "": "DASHBOARD",
        "dashboard": "DASHBOARD",
        "registros": "REGISTROS",
        "documentos": "DOCUMENTOS",
        "expedientes": "EXPEDIENTES",
        "pendientes": "DOCUMENTOS",
        "alertas": "DASHBOARD",
        "empresas": "EMPRESAS",
        "organizacion": "ORGANIZACION",
        "produccion": "PRODUCCION",
        "pagos": "PAGOS",
        "configuracion": "CONFIGURACION",
    }.get(limpio, "GENERAL")
