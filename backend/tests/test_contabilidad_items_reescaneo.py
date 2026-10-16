"""Vista previa histórica: paginación, tenant e integridad de originales."""

import hashlib
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem
from app.models import Documento, Tenant
from app.services.contabilidad_items_reescaneo import (
    previsualizar_pagina,
    registrar_pagina_verificada,
)
from app.storage import AlmacenLocal

XML = b"""<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cac:InvoiceLine><cbc:InvoicedQuantity unitCode="KGM">2</cbc:InvoicedQuantity>
<cac:Item><cbc:Name>Pota</cbc:Name></cac:Item></cac:InvoiceLine>
</Invoice>"""


def _guardar(
    session: Session, almacen: AlmacenLocal, tenant_id: uuid.UUID, data: bytes
) -> Documento:
    digest = hashlib.sha256(data).hexdigest()
    ruta = almacen.guardar(tenant_id, digest, data)
    documento = Documento(
        tenant_id=tenant_id,
        estado="PENDIENTE_RELACION",
        sha256=digest,
        nombre_original="factura.xml",
        mime_type="text/xml",
        tamano_bytes=len(data),
        ruta_storage=ruta,
    )
    session.add(documento)
    session.flush()
    return documento


def test_vista_previa_paginada_aislada_sin_modificar_original(session: Session, tmp_path: Path):
    primero = Tenant(nombre="tenant_previsualizacion_a")
    segundo = Tenant(nombre="tenant_previsualizacion_b")
    session.add_all([primero, segundo])
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    a = _guardar(session, almacen, primero.id, XML)
    _guardar(session, almacen, segundo.id, XML)

    pagina = previsualizar_pagina(session, almacen, primero.id, limite=1)
    assert len(pagina) == 1
    assert pagina[0].documento_id == a.id
    assert pagina[0].estado == "XML_REVISADO"
    assert pagina[0].lineas_detectadas == 1
    assert previsualizar_pagina(session, almacen, primero.id, despues_id=a.id) == []
    assert almacen.leer(a.ruta_storage) == XML


@pytest.mark.parametrize(
    ("cambio", "estado"),
    [
        ("eliminar", "ARCHIVO_NO_DISPONIBLE"),
        ("alterar", "HASH_DIFERENTE"),
    ],
)
def test_vista_previa_informa_archivo_faltante_o_alterado(
    session: Session, tmp_path: Path, cambio: str, estado: str
):
    tenant = Tenant(nombre=f"vista_previa_{cambio}")
    session.add(tenant)
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    documento = _guardar(session, almacen, tenant.id, XML)
    ruta = almacen.ruta_absoluta(documento.ruta_storage)
    if cambio == "eliminar":
        ruta.unlink()
    else:
        ruta.write_bytes(b"<Invoice>alterado</Invoice>")

    resultado = previsualizar_pagina(session, almacen, tenant.id)
    assert len(resultado) == 1
    assert resultado[0].estado == estado
    assert resultado[0].lineas_detectadas == 0


@pytest.mark.parametrize("limite", [0, -1, 101])
def test_vista_previa_rechaza_limites_fuera_de_rango(session: Session, tmp_path: Path, limite: int):
    with pytest.raises(ValueError, match="límite"):
        previsualizar_pagina(session, AlmacenLocal(tmp_path), uuid.uuid4(), limite=limite)


def test_vista_previa_recupera_pagina_siguiente_sin_repetir_documentos(
    session: Session, tmp_path: Path
):
    tenant = Tenant(nombre="tenant_cursor_reescaneo")
    session.add(tenant)
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    documentos = [
        _guardar(session, almacen, tenant.id, XML + f"<!--{i}-->".encode()) for i in range(3)
    ]
    primer_lote = previsualizar_pagina(session, almacen, tenant.id, limite=2)
    assert len(primer_lote) == 2
    segundo_lote = previsualizar_pagina(
        session, almacen, tenant.id, despues_id=primer_lote[-1].documento_id, limite=2
    )
    assert len(segundo_lote) == 1
    ids = [fila.documento_id for fila in primer_lote + segundo_lote]
    assert len(ids) == len(set(ids)) == 3
    assert set(ids) == {documento.id for documento in documentos}
    assert all(fila.estado == "XML_REVISADO" for fila in primer_lote + segundo_lote)


def test_vista_previa_no_lee_ruta_de_otro_tenant(session: Session, tmp_path: Path):
    propietario = Tenant(nombre="tenant_origen_ruta_xml")
    ajeno = Tenant(nombre="tenant_ruta_xml_ajena")
    session.add_all([propietario, ajeno])
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    documento_ajeno = _guardar(session, almacen, ajeno.id, XML)
    documento = _guardar(session, almacen, propietario.id, XML)
    documento.ruta_storage = documento_ajeno.ruta_storage
    session.flush()

    resultado = previsualizar_pagina(session, almacen, propietario.id)
    assert len(resultado) == 1
    assert resultado[0].documento_id == documento.id
    assert resultado[0].estado == "RUTA_FUERA_TENANT"
    assert resultado[0].lineas_detectadas == 0


def test_registrar_lote_xml_no_duplica_lineas_ni_altera_original(session: Session, tmp_path: Path):
    tenant = Tenant(nombre="tenant_lote_xml")
    session.add(tenant)
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    documento = _guardar(session, almacen, tenant.id, XML)

    primero = registrar_pagina_verificada(session, almacen, tenant.id)
    assert len(primero) == 1
    assert primero[0].estado == "PROCESADO"
    assert primero[0].lineas_nuevas == 1

    segundo = registrar_pagina_verificada(session, almacen, tenant.id)
    assert segundo[0].estado == "PROCESADO"
    assert segundo[0].lineas_nuevas == 0
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 1
    assert almacen.leer(documento.ruta_storage) == XML


def test_xml_que_supera_limite_es_rechazado_sin_registrar_items(session: Session, tmp_path: Path):
    tenant = Tenant(nombre="tenant_xml_excede_limite")
    session.add(tenant)
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    xml_grande = XML + b" " * (5 * 1024 * 1024)
    documento = _guardar(session, almacen, tenant.id, xml_grande)

    previa = previsualizar_pagina(session, almacen, tenant.id)
    assert previa[0].estado == "EXCEDE_LIMITE"
    lote = registrar_pagina_verificada(session, almacen, tenant.id)
    assert lote[0].estado == "EXCEDE_LIMITE"
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 0
    assert almacen.leer(documento.ruta_storage) == xml_grande


@pytest.mark.parametrize("contenido", [b"<Invoice>", b"<nota>Sin lineas</nota>"])
def test_xml_invalido_o_sin_items_no_genera_lineas(
    session: Session, tmp_path: Path, contenido: bytes
):
    tenant = Tenant(nombre="tenant_xml_sin_items_" + hashlib.sha256(contenido).hexdigest()[:8])
    session.add(tenant)
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    _guardar(session, almacen, tenant.id, contenido)

    previa = previsualizar_pagina(session, almacen, tenant.id)
    assert len(previa) == 1
    assert previa[0].estado == "SIN_ITEMS_UBL"
    lote = registrar_pagina_verificada(session, almacen, tenant.id)
    assert lote[0].estado == "SIN_ITEMS_UBL"
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 0


def test_ruta_con_traversal_no_procesa_archivo_de_otro_tenant(
    session: Session, tmp_path: Path
):
    propietario = Tenant(nombre="tenant_traversal_a")
    ajeno = Tenant(nombre="tenant_traversal_b")
    session.add_all([propietario, ajeno])
    session.flush()
    almacen = AlmacenLocal(tmp_path)
    ajeno_doc = _guardar(session, almacen, ajeno.id, XML)
    doc = _guardar(session, almacen, propietario.id, XML)
    doc.ruta_storage = f"{propietario.id}/../{ajeno_doc.ruta_storage}"
    session.flush()

    previa = previsualizar_pagina(session, almacen, propietario.id)
    assert previa[0].estado == "RUTA_FUERA_TENANT"
    lote = registrar_pagina_verificada(session, almacen, propietario.id)
    assert lote[0].estado == "RUTA_FUERA_TENANT"
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 0
