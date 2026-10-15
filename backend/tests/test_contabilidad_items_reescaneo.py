"""Vista previa histórica: paginación, tenant e integridad de originales."""

import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Documento, Tenant
from app.services.contabilidad_items_reescaneo import previsualizar_pagina
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
