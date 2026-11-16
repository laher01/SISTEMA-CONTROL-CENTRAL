"""Exportación XLSX de los listados operativos."""

import re
from collections.abc import Iterable, Iterator
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from uuid import UUID
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import ColumnElement, Select

from app.models import Documento, Empresa, Expediente, Gestor, Miembro
from app.services.metadatos_documento import campos_individuales, metadatos_individuales

COLUMNAS = (
    "USUARIO",
    "PEDIDO",
    "RUC del Emisor",
    "Razón Social del Emisor",
    "Fecha de Emisión",
    "Razón Social del Receptor",
    "RUC del Receptor",
    "Importe Total",
    "Número Correlativo",
)
_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PAQUETE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_CARACTERES_INVALIDOS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_EXCEL_ESCAPE = re.compile(r"_x[0-9a-fA-F]{4}_")
Celda = str | Decimal | date | None


def _celda(valor: Celda, referencia: str) -> str:
    if isinstance(valor, Decimal):
        return f'<c r="{referencia}"><v>{valor:f}</v></c>'
    if isinstance(valor, date):
        dias = (valor - date(1899, 12, 30)).days
        return f'<c r="{referencia}" s="1"><v>{dias}</v></c>'
    texto = _CARACTERES_INVALIDOS.sub("", valor or "")[:32767]
    texto = _EXCEL_ESCAPE.sub(lambda m: "_x005F_" + m[0][1:], texto)
    return (
        f'<c r="{referencia}" t="inlineStr"><is><t xml:space="preserve">'
        f"{escape(texto)}</t></is></c>"
    )


def _xlsx(filas: Iterable[tuple[Celda, ...]]) -> bytes:
    memoria = BytesIO()
    with ZipFile(memoria, "w", ZIP_DEFLATED) as libro:
        libro.writestr(
            "[Content_Types].xml",
            """
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml"
 ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml"
 ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml"
 ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>""",
        )
        libro.writestr(
            "_rels/.rels",
            f'<Relationships xmlns="{_PAQUETE_REL}">'
            f'<Relationship Id="rId1" Type="{_REL}/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>',
        )
        libro.writestr(
            "xl/_rels/workbook.xml.rels",
            f'<Relationships xmlns="{_PAQUETE_REL}">'
            f'<Relationship Id="rId1" Type="{_REL}/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{_REL}/styles" Target="styles.xml"/>'
            "</Relationships>",
        )
        libro.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{_NS}" xmlns:r="{_REL}">'
            '<sheets><sheet name="Resultados" sheetId="1" r:id="rId1"/>'
            "</sheets></workbook>",
        )
        libro.writestr(
            "xl/styles.xml",
            f'<styleSheet xmlns="{_NS}">'
            """
<numFmts count="1"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/></numFmts>
<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="2"><xf numFmtId="0" xfId="0"/>
<xf numFmtId="164" xfId="0" applyNumberFormat="1"/></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>""",
        )
        anchos = (28, 38, 18, 38, 19, 38, 18, 17, 23)
        with libro.open("xl/worksheets/sheet1.xml", "w") as hoja:
            hoja.write(
                (
                    f'<worksheet xmlns="{_NS}">'
                    '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" '
                    'topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
                    "</sheetView></sheetViews><cols>"
                    + "".join(
                        f'<col min="{i}" max="{i}" width="{ancho}" customWidth="1"/>'
                        for i, ancho in enumerate(anchos, 1)
                    )
                    + "</cols><sheetData>"
                ).encode()
            )
            ultima = 1
            for ultima, fila in enumerate(_con_encabezado(filas), 1):
                celdas = "".join(
                    _celda(valor, f"{columna}{ultima}")
                    for columna, valor in zip("ABCDEFGHI", fila, strict=True)
                )
                hoja.write(f'<row r="{ultima}">{celdas}</row>'.encode())
            hoja.write(f'</sheetData><autoFilter ref="A1:I{ultima}"/></worksheet>'.encode())
    return memoria.getvalue()


def _con_encabezado(filas: Iterable[tuple[Celda, ...]]) -> Iterator[tuple[Celda, ...]]:
    yield COLUMNAS
    yield from filas


def _importe(texto: str | None) -> Decimal | None:
    if texto:
        try:
            numero = Decimal(texto.replace(",", ""))
            return numero if numero.is_finite() else None
        except InvalidOperation:
            pass
    return None


def exportar_listado(
    session: Session, tenant_id: UUID, ids: Select[tuple[UUID]], origen: str
) -> Response:
    emisor = aliased(Empresa)
    receptor = aliased(Empresa)
    documento = origen == "documentos"
    consulta = select(
        Miembro.nombre,
        Expediente,
        emisor.ruc,
        emisor.razon_social,
        receptor.razon_social,
        receptor.ruc,
    )
    usuario_id: ColumnElement[UUID | None] = Expediente.usuario_id.__clause_element__()
    gestor_id: ColumnElement[UUID | None] = Expediente.gestor_id.__clause_element__()
    if documento:
        consulta = (
            consulta.add_columns(Documento)
            .select_from(Documento)
            .outerjoin(
                Expediente,
                (Documento.expediente_id == Expediente.id)
                & (Expediente.tenant_id == tenant_id)
                & Expediente.deleted_at.is_(None),
            )
            .where(Documento.tenant_id == tenant_id, Documento.id.in_(ids))
            .order_by(Documento.created_at.desc(), Documento.id)
        )
        usuario_id = func.coalesce(Documento.usuario_id, Expediente.usuario_id)
        gestor_id = func.coalesce(Documento.gestor_id, Expediente.gestor_id)
    else:
        consulta = (
            consulta.select_from(Expediente)
            .where(Expediente.tenant_id == tenant_id, Expediente.id.in_(ids))
            .order_by(Expediente.fecha_emision.desc(), Expediente.created_at.desc(), Expediente.id)
        )
    consulta = (
        consulta.outerjoin(
            emisor, (emisor.id == Expediente.emisor_id) & (emisor.tenant_id == tenant_id)
        )
        .outerjoin(
            receptor, (receptor.id == Expediente.receptor_id) & (receptor.tenant_id == tenant_id)
        )
        .outerjoin(Gestor, (Gestor.id == gestor_id) & (Gestor.tenant_id == tenant_id))
        .outerjoin(
            Miembro,
            (Miembro.id == func.coalesce(usuario_id, Gestor.usuario_id))
            & (Miembro.tenant_id == tenant_id),
        )
    )

    def filas() -> Iterator[tuple[Celda, ...]]:
        for fila in session.execute(consulta.execution_options(yield_per=500)):
            nombre, expediente, ruc_e, nombre_e, nombre_r, ruc_r = fila[:6]
            pedido = (
                str(expediente.pedido_gerencia_id)
                if expediente and expediente.pedido_gerencia_id
                else None
            )
            if documento:
                doc = fila[6]
                ficha = metadatos_individuales(doc, expediente=expediente, usar_relacion=False)
                serie, correlativo = ficha["serie_documento"], ficha["correlativo_documento"]
                fecha = ficha["fecha_documento"]
                campo = campos_individuales(doc)
                principal = expediente and doc.tipo_documento in ("FACT", "RHE")
                importe = _importe(campo("importe_total"))
                if principal:
                    importe = expediente.importe_total
                    correlativo = (
                        expediente.correlativo_original or correlativo or expediente.correlativo
                    )
                else:
                    ruc_e = nombre_e = nombre_r = ruc_r = None
                ruc_e = ruc_e or campo("ruc_emisor")
                nombre_e = nombre_e or campo("razon_social_emisor")
                nombre_r = nombre_r or campo("razon_social_receptor")
                ruc_r = ruc_r or campo("ruc_receptor")
            else:
                serie = expediente.serie
                correlativo = expediente.correlativo_original or expediente.correlativo
                fecha, importe = expediente.fecha_emision, expediente.importe_total
            numero = f"{serie}-{correlativo}" if serie and correlativo else correlativo
            yield (nombre, pedido, ruc_e, nombre_e, fecha, nombre_r, ruc_r, importe, numero)

    return Response(
        _xlsx(filas()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{origen}-filtrados.xlsx"',
            "Cache-Control": "no-store",
        },
    )
