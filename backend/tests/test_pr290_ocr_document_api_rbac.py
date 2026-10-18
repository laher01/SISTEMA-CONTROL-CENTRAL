"""Two-tenant document API boundary checks with synthetic fiscal dossiers."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CuentaAcceso, Documento, Empresa, Expediente, Miembro, Tenant


def test_cross_tenant_ocr_document_operations_denied(client, session: Session, auth_prueba):
    context_a = auth_prueba.contexto
    tenant_b = Tenant(nombre="Aislamiento OCR B", codigo="OCR-PR290-B", estado="ACTIVO")
    session.add(tenant_b)
    session.flush()
    member_b = Miembro(
        tenant_id=tenant_b.id, codigo="OCR-B", nombre="OCR B", rol="USUARIO", activo=True
    )
    session.add(member_b)
    session.flush()
    account_b = CuentaAcceso(
        tenant_id=tenant_b.id,
        miembro_id=member_b.id,
        login="OCR-B",
        password_hash="synthetic",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    emisor = Empresa(tenant_id=tenant_b.id, ruc="20611111001", razon_social="Emisor B")
    receptor = Empresa(tenant_id=tenant_b.id, ruc="20611111002", razon_social="Receptor B")
    session.add_all([account_b, emisor, receptor])
    session.flush()
    dossier = Expediente(
        tenant_id=tenant_b.id,
        emisor_id=emisor.id,
        receptor_id=receptor.id,
        tipo_comprobante="FACT",
        serie="F001",
        correlativo="00000888",
        fecha_emision=date(2026, 10, 18),
        moneda="PEN",
        importe_total=Decimal("12.00"),
        estado="NARANJA",
        usuario_id=member_b.id,
    )
    session.add(dossier)
    session.flush()
    document = Documento(
        tenant_id=tenant_b.id,
        expediente_id=dossier.id,
        usuario_id=member_b.id,
        tipo_documento="OTRO",
        estado="PENDIENTE_RELACION",
        sha256="f" * 64,
        nombre_original="ocr-evidencia.pdf",
        mime_type="application/pdf",
        tamano_bytes=3,
        ruta_storage="synthetic/not-accessible.pdf",
    )
    session.add_all([dossier, document])
    session.commit()

    auth_prueba.contexto = context_a
    url = f"/api/v1/documentos/{document.id}"
    assert client.get(url).status_code == 404
    assert client.get(f"{url}/archivo").status_code == 404
    assert client.put(f"{url}/extraccion-confirmada", json={"serie": "F001"}).status_code == 404
    assert (
        client.post(
            f"{url}/vincular",
            json={"expediente_id": str(dossier.id), "tipo_documento": "OTRO"},
        ).status_code
        == 404
    )

    # Even a document owned by tenant A cannot link to an alien dossier.
    owned = client.post(
        "/api/v1/documentos",
        files={"archivo": ("propio.bin", b"contenido-propio", "application/octet-stream")},
        data={"tipo_documento": "OTRO"},
    )
    assert owned.status_code == 201, owned.text
    own_id = owned.json()["id"]
    denied = client.post(
        f"/api/v1/documentos/{own_id}/vincular",
        json={"expediente_id": str(dossier.id), "tipo_documento": "OTRO"},
    )
    assert denied.status_code == 404
    session.expire_all()
    assert session.scalar(select(Documento.expediente_id).where(Documento.id == own_id)) is None
    assert session.get(Documento, document.id).datos_extraidos is None
    assert session.get(Documento, document.id).expediente_id == dossier.id

    # Different tenant's real context can read its own record.
    auth_prueba.contexto = replace(
        context_a,
        tenant_id=tenant_b.id,
        cuenta_id=account_b.id,
        miembro_id=member_b.id,
        usuario_id=member_b.id,
        codigo="OCR-B",
        nombre="OCR B",
    )
    assert client.get(url).status_code == 200
    assert client.get(f"/api/v1/documentos/{own_id}").status_code == 404
