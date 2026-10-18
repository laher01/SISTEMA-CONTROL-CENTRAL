"""PostgreSQL concurrent UBL ingestion must persist one fiscal line exactly once."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem
from app.models import Documento
from app.services.contabilidad_items_ubl import registrar_items_ubl

UBL = b"""<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cac:InvoiceLine><cbc:InvoicedQuantity unitCode="KGM">3</cbc:InvoicedQuantity>
<cbc:LineExtensionAmount>27.00</cbc:LineExtensionAmount>
<cac:Item><cbc:Description>Pota para prueba sintetica</cbc:Description></cac:Item>
</cac:InvoiceLine></Invoice>"""


def test_dos_transacciones_ubl_no_duplican_lineas(engine, auth_prueba):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires actual PostgreSQL row locking")
    tenant_id = auth_prueba.contexto.tenant_id
    with Session(engine) as session:
        doc = Documento(
            tenant_id=tenant_id,
            sha256="e" * 64,
            nombre_original="factura-prueba.xml",
            mime_type="application/xml",
            tamano_bytes=len(UBL),
            ruta_storage="test/ubl",
            tipo_documento="FACT",
            estado="PENDIENTE",
        )
        session.add(doc)
        session.commit()
        doc_id = doc.id

    barrier = Barrier(2, timeout=20)

    def worker(_):
        with Session(engine) as session:
            barrier.wait()
            count = registrar_items_ubl(session, tenant_id, doc_id, UBL)
            session.commit()
            return count

    with ThreadPoolExecutor(max_workers=2) as pool:
        counts = list(pool.map(worker, (0, 1)))
    assert sorted(counts) == [0, 1]
    with Session(engine) as session:
        lineas = list(
            session.scalars(
                select(LineaComprobanteItem).where(
                    LineaComprobanteItem.tenant_id == tenant_id,
                    LineaComprobanteItem.documento_id == doc_id,
                )
            )
        )
        assert len(lineas) == 1
        assert lineas[0].importe_linea == Decimal("27.00")
        assert lineas[0].cantidad == Decimal("3")
        assert (
            session.scalar(
                select(func.count())
                .select_from(LineaComprobanteItem)
                .where(LineaComprobanteItem.documento_id == doc_id)
            )
            == 1
        )
