import re
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.models import Documento, Empresa, Expediente

REFERENCIA = re.compile(r"\b([A-Z0-9]{4})\s*[-–—]\s*0*(\d{1,8})\b", re.IGNORECASE)
RUC = re.compile(r"(?<!\d)(\d{11})(?!\d)")


@dataclass(frozen=True)
class RelacionSugerida:
    expediente: Expediente
    puntaje: float
    evidencias: tuple[str, ...]


def sugerir_relaciones(
    session: Session, documento: Documento, limite: int = 10
) -> list[RelacionSugerida]:
    texto = _texto_extraido(documento)
    if not texto:
        return []
    texto_mayusculas = " ".join(texto.upper().split())
    referencias = {(serie.upper(), str(int(numero))) for serie, numero in REFERENCIA.findall(texto)}
    rucs = set(RUC.findall(texto))
    if not referencias and not rucs:
        return []

    emisor = aliased(Empresa)
    receptor = aliased(Empresa)
    filtros: list[ColumnElement[bool]] = []
    if referencias:
        filtros.extend(
            (Expediente.serie == serie) & (Expediente.correlativo == correlativo)
            for serie, correlativo in referencias
        )
    if rucs:
        filtros.append(or_(emisor.ruc.in_(rucs), receptor.ruc.in_(rucs)))
    consulta = (
        select(Expediente)
        .join(emisor, Expediente.emisor_id == emisor.id)
        .join(receptor, Expediente.receptor_id == receptor.id)
        .options(selectinload(Expediente.emisor), selectinload(Expediente.receptor))
        .where(
            Expediente.tenant_id == documento.tenant_id,
            Expediente.deleted_at.is_(None),
            or_(*filtros),
        )
        .limit(200)
    )
    sugerencias = [
        sugerencia
        for expediente in session.scalars(consulta).unique()
        if (sugerencia := _puntuar(expediente, referencias, rucs, texto_mayusculas)) is not None
    ]
    sugerencias.sort(key=lambda item: (-item.puntaje, item.expediente.fecha_emision), reverse=False)
    return sugerencias[:limite]


def _puntuar(
    expediente: Expediente,
    referencias: set[tuple[str, str]],
    rucs: set[str],
    texto: str,
) -> RelacionSugerida | None:
    puntaje = 0.0
    evidencias: list[str] = []
    referencia = (expediente.serie.upper(), expediente.correlativo)
    if referencia in referencias:
        puntaje += 0.65
        evidencias.append(f"Comprobante {expediente.serie}-{expediente.correlativo}")
    if expediente.emisor.ruc in rucs:
        puntaje += 0.2
        evidencias.append(f"RUC emisor {expediente.emisor.ruc}")
    if expediente.receptor.ruc in rucs:
        puntaje += 0.1
        evidencias.append(f"RUC receptor {expediente.receptor.ruc}")
    if _importe_en_texto(expediente.importe_total, texto):
        puntaje += 0.05
        evidencias.append(f"Importe {expediente.moneda} {expediente.importe_total:.2f}")
    if puntaje < 0.15:
        return None
    return RelacionSugerida(expediente, round(min(puntaje, 1.0), 4), tuple(evidencias))


def _importe_en_texto(importe: Decimal, texto: str) -> bool:
    numero = f"{importe:.2f}"
    entero, decimales = numero.split(".")
    miles_coma = f"{int(entero):,}.{decimales}"
    miles_punto = miles_coma.replace(",", "X").replace(".", ",").replace("X", ".")
    variantes = {numero, numero.replace(".", ","), miles_coma, miles_punto}
    return any(variante in texto for variante in variantes)


def _texto_extraido(documento: Documento) -> str:
    datos = documento.datos_extraidos or {}
    procesamiento = datos.get("procesamiento_documental")
    if not isinstance(procesamiento, dict):
        return ""
    texto = procesamiento.get("texto")
    return texto if isinstance(texto, str) else ""


def documento_del_tenant(
    session: Session, tenant_id: uuid.UUID, documento_id: uuid.UUID
) -> Documento | None:
    documento = session.get(Documento, documento_id)
    if documento is None or documento.tenant_id != tenant_id or documento.deleted_at:
        return None
    return documento
