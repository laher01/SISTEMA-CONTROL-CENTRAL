"""Excepción manual y segura para facturas que no requieren guía remitente."""

from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Miembro
from tests.conftest import AuthPrueba
from tests.test_api import expediente, subir
from tests.xml import factura


def test_guia_no_aplica_mantiene_expediente_pendiente_hasta_completar_resto(
    client: TestClient,
) -> None:
    factura_subida = subir(client, "factura-2500.xml", factura(importe="2500.00"))
    expediente_id = factura_subida["expediente_id"]
    detalle_inicial = expediente(client, expediente_id)
    assert detalle_inicial["faltantes"] == ["GRR", "VCHR"]
    assert detalle_inicial["estado"] == "NARANJA"

    confirmacion = client.patch(
        f"/api/v1/expedientes/{expediente_id}/guia-no-aplica",
        json={"confirmado": True},
    )
    assert confirmacion.status_code == 200, confirmacion.text
    assert confirmacion.json()["guia_no_aplica_confirmada"] is True
    assert confirmacion.json()["faltantes"] == ["VCHR"]
    assert confirmacion.json()["estado"] == "NARANJA"

    subir(
        client,
        "voucher.png",
        b"\x89PNG voucher",
        tipo_documento="VCHR",
        expediente_id=str(expediente_id),
    )
    detalle_final = expediente(client, expediente_id)
    assert detalle_final["faltantes"] == []
    assert detalle_final["estado"] == "VERDE"

    lista = client.get("/api/v1/expedientes").json()
    factura_listada = next(item for item in lista if item["id"] == expediente_id)
    assert factura_listada["documentos_count"] == 2


def test_responsable_puede_confirmar_guia_en_expediente_de_su_usuario(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    factura_subida = subir(client, "factura-responsable.xml", factura(importe="2500.00"))
    responsable = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="RESP-GUIA",
        nombre="Responsable de prueba",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    usuario = session.get(Miembro, auth_prueba.usuario_id)
    assert usuario is not None
    usuario.responsable_id = responsable.id
    session.commit()

    auth_prueba.contexto = replace(
        auth_prueba.contexto,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        usuario_id=None,
        codigo=responsable.codigo,
        nombre=responsable.nombre,
    )
    respuesta = client.patch(
        f"/api/v1/expedientes/{factura_subida['expediente_id']}/guia-no-aplica",
        json={"confirmado": True},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["guia_no_aplica_confirmada"] is True
