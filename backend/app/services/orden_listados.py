"""Orden estable para las consultas documentales paginadas."""

import re
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Numeric, Select, String, case, cast, func, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.enums import Moneda
from app.models import Documento, Empresa, Expediente, Gestor, Miembro
from app.services.metadatos_documento import NUMERO_EN_ARCHIVO, campos_individuales

OrdenListado = Literal[
    "monto",
    "emisor",
    "receptor",
    "correlativo",
    "tipo_empresa",
    "fecha_documento",
    "fecha_carga",
    "gestor",
    "usuario",
    "responsable",
]
DireccionListado = Literal["asc", "desc"]
IMPORTE_VALIDO = r"^[+-]?[0-9]{1,32}([.][0-9]{1,12})?$"


def importe_individual(documento: Documento) -> dict[str, Decimal | str | None]:
    campo = campos_individuales(documento)
    importe = campo("importe_total")
    valor = Decimal(importe) if importe and re.fullmatch(IMPORTE_VALIDO, importe) else None
    moneda = campo("moneda")
    if documento.tipo_documento in ("FACT", "RHE") and documento.expediente is not None:
        valor = documento.importe_total if documento.importe_total is not None else valor
        moneda = documento.moneda or moneda
    return {"importe_total": valor, "moneda": Moneda(moneda) if moneda in ("PEN", "USD") else None}


def campo_documento(clave: str) -> ColumnElement[str]:
    datos = Documento.datos_extraidos
    fuentes = (
        datos["extraccion_confirmada"]["campos"][clave],
        datos[clave],
        datos["procesamiento_documental"]["extraccion_estructurada"]["campos"][clave],
    )
    return func.coalesce(
        *(
            func.nullif(func.trim(valor), "")
            for fuente in fuentes
            for valor in (fuente["valor"].as_string(), fuente.as_string())
        )
    )


def importe_documento(expediente: type[Expediente]) -> ColumnElement[Decimal]:
    propio = campo_documento("importe_total")
    importe = case((propio.regexp_match(IMPORTE_VALIDO), cast(propio, Numeric())))
    return func.coalesce(
        case((Documento.tipo_documento.in_(("FACT", "RHE")), expediente.importe_total)), importe
    )


def ordenar_listado[Fila: tuple[Any, ...]](
    consulta: Select[Fila],
    tenant_id: UUID,
    orden: OrdenListado,
    direccion: DireccionListado,
    *,
    documento: bool = False,
    postgres: bool = True,
) -> Select[Fila]:
    modelo = Documento if documento else Expediente
    expediente = aliased(Expediente) if documento else Expediente
    if documento and orden in {
        "monto",
        "emisor",
        "receptor",
        "tipo_empresa",
        "fecha_documento",
        "correlativo",
    }:
        consulta = consulta.outerjoin(
            expediente,
            (Documento.expediente_id == expediente.id) & (expediente.tenant_id == tenant_id),
        )
    campos: tuple[ColumnElement[Any] | InstrumentedAttribute[Any], ...]
    if orden in ("gestor", "usuario", "responsable"):
        usuario = aliased(Miembro)
        persona: type[Miembro] | type[Gestor]
        if orden == "gestor":
            persona = aliased(Gestor)
            consulta = consulta.outerjoin(
                persona, (persona.id == modelo.gestor_id) & (persona.tenant_id == tenant_id)
            )
        else:
            consulta = consulta.outerjoin(
                usuario, (usuario.id == modelo.usuario_id) & (usuario.tenant_id == tenant_id)
            )
            persona = usuario
            if orden == "responsable":
                persona = aliased(Miembro)
                consulta = consulta.outerjoin(
                    persona,
                    (persona.id == usuario.responsable_id) & (persona.tenant_id == tenant_id),
                )
        campos = (func.lower(persona.nombre), func.lower(persona.codigo))
    elif orden in ("emisor", "receptor", "tipo_empresa"):
        empresa = aliased(Empresa)
        empresa_id = expediente.receptor_id if orden == "receptor" else expediente.emisor_id
        consulta = consulta.outerjoin(
            empresa, (empresa.id == empresa_id) & (empresa.tenant_id == tenant_id)
        )
        if orden == "tipo_empresa":
            campos = (empresa.clasificacion_proveedor,)
        elif documento:
            ruc = func.coalesce(empresa.ruc, campo_documento(f"ruc_{orden}"))
            nombre = func.coalesce(
                func.nullif(empresa.razon_social, empresa.ruc),
                Documento.datos_extraidos[orden]["razon_social"].as_string(),
                campo_documento(f"razon_social_{orden}"),
                ruc,
            )
            campos = (func.lower(nombre), ruc)
        else:
            campos = (func.lower(empresa.razon_social), empresa.ruc)
    elif orden == "monto":
        campos = (importe_documento(expediente) if documento else expediente.importe_total,)
    elif orden == "fecha_carga":
        fecha_carga = (
            Documento.created_at
            if documento
            else (
                select(func.min(Documento.created_at))
                .where(
                    Documento.tenant_id == tenant_id,
                    Documento.expediente_id == Expediente.id,
                    Documento.deleted_at.is_(None),
                )
                .scalar_subquery()
            )
        )
        campos = (fecha_carga,)
    elif orden == "fecha_documento":
        if documento:
            fecha = func.substr(campo_documento("fecha_emision"), 1, 10)
            campos = (
                func.coalesce(
                    case((fecha.regexp_match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"), fecha)),
                    case(
                        (
                            Documento.tipo_documento.in_(("FACT", "RHE")),
                            cast(expediente.fecha_emision, String),
                        )
                    ),
                ),
            )
        else:
            campos = (expediente.fecha_emision,)
    else:
        serie: ColumnElement[str] | InstrumentedAttribute[str] = expediente.serie
        numero: ColumnElement[str] | InstrumentedAttribute[str] = expediente.correlativo
        if documento:
            principal = Documento.tipo_documento.in_(("FACT", "RHE"))
            serie = func.coalesce(campo_documento("serie"), case((principal, serie)))
            numero = func.coalesce(campo_documento("correlativo"), case((principal, numero)))
            if postgres:
                coincidencia = func.regexp_match(
                    func.upper(Documento.nombre_original),
                    NUMERO_EN_ARCHIVO.pattern[4:],
                    type_=ARRAY(String),
                )
                serie = func.coalesce(serie, coincidencia[1])
                numero = func.coalesce(numero, coincidencia[2])
        numerico = case((numero.regexp_match(r"^[0-9]{1,32}$"), cast(numero, Numeric())))
        campos = (func.upper(serie), numerico, func.upper(numero))
    return consulta.order_by(
        *((campo.asc() if direccion == "asc" else campo.desc()).nulls_last() for campo in campos),
        modelo.id,
    )
