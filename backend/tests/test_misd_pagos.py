"""Regresión MISD: los pagos generados congelan su producción de origen."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Documento,
    Expediente,
    Gestor,
    Miembro,
    PagoERP,
    PagoGestor,
    PagoResponsableERP,
)
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_pago_generado_bloquea_documento_y_expediente_incluso_para_admin(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("congelada.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = respuesta.json()
    expediente = session.get(Expediente, documento["expediente_id"])
    assert expediente is not None
    assert expediente.usuario_id is not None
    pago = PagoERP(
        tenant_id=expediente.tenant_id,
        usuario_id=expediente.usuario_id,
        periodo_desde=date(2026, 1, 1),
        periodo_hasta=date(2026, 12, 31),
        moneda=expediente.moneda,
        produccion_total=Decimal("100.00"),
        porcentaje=Decimal("10"),
        bruto=Decimal("10.00"),
        saldo=Decimal("10.00"),
        estado="PROGRAMADO",
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()

    expedientes = client.get("/api/v1/expedientes")
    assert expedientes.status_code == 200, expedientes.text
    vista = next(f for f in expedientes.json() if f["id"] == str(expediente.id))
    assert vista["puede_eliminar"] is False

    registros = client.get("/api/v1/registros")
    assert registros.status_code == 200, registros.text
    fila = next(f for f in registros.json()["filas"] if f["expediente_id"] == str(expediente.id))
    assert fila["puede_eliminar"] is False

    ruta_documento = f"/api/v1/documentos/{documento['id']}"
    ruta_expediente = f"/api/v1/expedientes/{expediente.id}"
    documento_bloqueado = client.delete(ruta_documento)
    expediente_bloqueado = client.delete(ruta_expediente)
    assert documento_bloqueado.status_code == 409, documento_bloqueado.text
    assert expediente_bloqueado.status_code == 409, expediente_bloqueado.text
    assert "Liquidación" in documento_bloqueado.text
    previsualizacion = client.post(
        "/api/v1/documentos/previsualizar-retirada",
        json={"documentos_ids": [documento["id"]]},
    )
    assert previsualizacion.status_code == 200, previsualizacion.text
    assert previsualizacion.json()["aptos"] == 0
    assert previsualizacion.json()["resultados"][0]["estado"] == "BLOQUEADO"
    assert client.get(ruta_documento).status_code == 200
    assert client.get(ruta_expediente).status_code == 200

    session.delete(pago)
    session.commit()
    assert client.delete(ruta_expediente).status_code == 204


def test_voucher_vinculado_a_pago_no_puede_retirarse(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("voucher.pdf", b"%PDF-1.7 voucher generado")},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = respuesta.json()
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    pago = PagoERP(
        tenant_id=auth_prueba.contexto.tenant_id,
        usuario_id=usuario_id,
        periodo_desde=date(2026, 9, 1),
        periodo_hasta=date(2026, 9, 30),
        moneda="PEN",
        produccion_total=Decimal("100.00"),
        porcentaje=Decimal("10"),
        bruto=Decimal("10.00"),
        saldo=Decimal("10.00"),
        estado="PROGRAMADO",
        voucher_documento_id=documento["id"],
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()
    eliminado = client.delete(f"/api/v1/documentos/{documento['id']}")
    assert eliminado.status_code == 409, eliminado.text
    assert "Voucher" in eliminado.text
    assert client.get(f"/api/v1/documentos/{documento['id']}").status_code == 200


def test_pago_gestor_generado_bloquea_expediente(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura-gestor.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    expediente = session.get(Expediente, respuesta.json()["expediente_id"])
    assert expediente is not None
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    gestor = Gestor(
        tenant_id=expediente.tenant_id,
        codigo="GEST-MISD",
        nombre="Gestor MISD",
        usuario_id=usuario_id,
    )
    session.add(gestor)
    session.flush()
    expediente.gestor_id = gestor.id
    pago = PagoGestor(
        tenant_id=expediente.tenant_id,
        gestor_id=gestor.id,
        usuario_id=usuario_id,
        periodo_desde=date(2026, 1, 1),
        periodo_hasta=date(2026, 12, 31),
        moneda=expediente.moneda,
        produccion_total=Decimal("100.00"),
        porcentaje=Decimal("10"),
        bruto=Decimal("10.00"),
        saldo=Decimal("10.00"),
        estado="PROGRAMADO",
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()
    resultado = client.delete(f"/api/v1/expedientes/{expediente.id}")
    assert resultado.status_code == 409, resultado.text
    assert "GESTOR" in resultado.text


def test_pago_responsable_generado_bloquea_expediente(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura-responsable.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    expediente = session.get(Expediente, respuesta.json()["expediente_id"])
    assert expediente is not None
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    responsable = Miembro(
        tenant_id=expediente.tenant_id,
        codigo="RESP-MISD",
        nombre="Responsable MISD",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    usuario = session.get(Miembro, usuario_id)
    assert usuario is not None
    usuario.responsable_id = responsable.id
    pago = PagoResponsableERP(
        tenant_id=expediente.tenant_id,
        gerente_id=None,
        responsable_id=responsable.id,
        periodo_desde=date(2026, 1, 1),
        periodo_hasta=date(2026, 12, 31),
        moneda=expediente.moneda,
        produccion_total=Decimal("100.00"),
        comision_total=Decimal("10.00"),
        detalle={},
        estado="PROGRAMADO",
        creado_por_cuenta_id=auth_prueba.contexto.cuenta_id,
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()
    resultado = client.delete(f"/api/v1/expedientes/{expediente.id}")
    assert resultado.status_code == 409, resultado.text
    assert "RESPONSABLE" in resultado.text



def test_voucher_de_otro_periodo_bloquea_retiro_integral_misd(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    factura_subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("expediente-voucher.xml", factura())},
    )
    assert factura_subida.status_code == 201, factura_subida.text
    expediente_id = factura_subida.json()["expediente_id"]
    voucher_subido = client.post(
        "/api/v1/documentos",
        files={"archivo": ("voucher-misd.pdf", b"%PDF-1.7 voucher")},
    )
    assert voucher_subido.status_code == 201, voucher_subido.text
    voucher = session.get(Documento, voucher_subido.json()["id"])
    assert voucher is not None
    voucher.expediente_id = expediente_id
    session.flush()
    solicitud = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Retiro pendiente de revisión"},
    )
    assert solicitud.status_code == 201, solicitud.text
    pago = PagoERP(
        tenant_id=auth_prueba.contexto.tenant_id,
        usuario_id=auth_prueba.contexto.usuario_id,
        periodo_desde=date(2025, 1, 1),
        periodo_hasta=date(2025, 12, 31),
        moneda="PEN",
        produccion_total=Decimal("100"),
        porcentaje=Decimal("10"),
        bruto=Decimal("10"),
        saldo=Decimal("10"),
        estado="PROGRAMADO",
        voucher_documento_id=voucher.id,
    )
    session.add(pago)
    session.commit()
    retirada = client.post(f"/api/v1/misd/solicitudes/{solicitud.json()['id']}/ejecutar")
    assert retirada.status_code == 409, retirada.text
    auth_prueba.como_admin()
    assert client.delete(f"/api/v1/expedientes/{expediente_id}").status_code == 409
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 200
