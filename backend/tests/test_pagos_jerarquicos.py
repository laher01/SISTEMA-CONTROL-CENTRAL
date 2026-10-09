from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Gestor, Miembro, PlanLiquidacion
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_pagos_por_jerarquia(client: TestClient, auth_prueba: AuthPrueba, session: Session) -> None:
    tid = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tid,
        codigo="RESPR",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    usuario = Miembro(
        tenant_id=tid,
        codigo="USPR",
        nombre="Usuario",
        rol="USUARIO",
        activo=True,
    )
    ajeno = Miembro(
        tenant_id=tid,
        codigo="USOTRO",
        nombre="Otro",
        rol="USUARIO",
        activo=True,
    )
    proveedor = Empresa(
        tenant_id=tid,
        ruc="20900000001",
        razon_social="Proveedor",
    )
    receptor = Empresa(
        tenant_id=tid,
        ruc="20900000002",
        razon_social="Cliente",
    )
    session.add_all([responsable, usuario, ajeno, proveedor, receptor])
    session.flush()
    usuario.responsable_id = responsable.id
    gestor = Gestor(
        tenant_id=tid,
        codigo="GESPR",
        nombre="Gestor",
        usuario_id=usuario.id,
        porcentaje_comision=Decimal("0.5000"),
    )
    otro_gestor = Gestor(
        tenant_id=tid,
        codigo="GESOTRO",
        nombre="Otro gestor",
        usuario_id=ajeno.id,
        porcentaje_comision=Decimal("2.0000"),
    )
    plan = PlanLiquidacion(
        tenant_id=tid,
        usuario_id=usuario.id,
        nombre="Tasa usuario",
        porcentaje=Decimal("1.5000"),
        vigencia_desde=date(2026, 10, 1),
        activo=True,
    )
    session.add_all([gestor, otro_gestor, plan])
    session.flush()
    session.add_all(
        [
            Expediente(
                tenant_id=tid,
                receptor_id=receptor.id,
                emisor_id=proveedor.id,
                tipo_comprobante="01",
                serie="F001",
                correlativo="00000001",
                fecha_emision=date(2026, 10, 5),
                moneda="PEN",
                importe_total=Decimal("400.00"),
                usuario_id=usuario.id,
                gestor_id=gestor.id,
            ),
            Expediente(
                tenant_id=tid,
                receptor_id=receptor.id,
                emisor_id=proveedor.id,
                tipo_comprobante="01",
                serie="F001",
                correlativo="00000002",
                fecha_emision=date(2026, 10, 7),
                moneda="PEN",
                importe_total=Decimal("600.00"),
                usuario_id=usuario.id,
            ),
        ]
    )
    session.commit()

    datos = {
        "usuario_id": str(usuario.id),
        "desde": "2026-10-01",
        "hasta": "2026-10-31",
        "moneda": "PEN",
    }
    auth_prueba.como_admin()
    # Administración puede intervenir excepcionalmente y liberar la liquidación.
    programado_admin = client.post("/api/v1/responsable/pagos/programar", json=datos)
    assert programado_admin.status_code == 201, programado_admin.text
    pago_admin_id = programado_admin.json()["id"]
    assert client.delete(f"/api/v1/responsable/pagos/{pago_admin_id}").status_code == 204
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=auth_prueba.contexto.cuenta_id,
        tenant_id=tid,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        gestor_id=None,
        usuario_id=None,
        codigo=responsable.codigo,
        nombre=responsable.nombre,
        cambio_clave_obligatorio=False,
    )
    cotizacion = client.post("/api/v1/responsable/pagos/cotizar", json=datos)
    assert cotizacion.status_code == 200, cotizacion.text
    assert cotizacion.json()["bruto"] == "15.00"
    programado = client.post("/api/v1/responsable/pagos/programar", json=datos)
    assert programado.status_code == 201, programado.text
    assert programado.json()["saldo"] == "15.00"
    assert client.post("/api/v1/responsable/pagos/programar", json=datos).status_code == 409
    assert client.delete(f"/api/v1/responsable/pagos/{programado.json()['id']}").status_code == 204

    auth_prueba.como_usuario(usuario.id)
    datos_gestor = {
        "gestor_id": str(gestor.id),
        "desde": "2026-10-01",
        "hasta": "2026-10-31",
        "moneda": "PEN",
    }
    ajeno_datos = {**datos_gestor, "gestor_id": str(otro_gestor.id)}
    assert client.post("/api/v1/pagos-gestores/cotizar", json=ajeno_datos).status_code == 403
    cotizado_gestor = client.post("/api/v1/pagos-gestores/cotizar", json=datos_gestor)
    assert cotizado_gestor.status_code == 200, cotizado_gestor.text
    assert cotizado_gestor.json()["bruto"] == "2.00"
    programado_gestor = client.post("/api/v1/pagos-gestores/programar", json=datos_gestor)
    assert programado_gestor.status_code == 201, programado_gestor.text
    assert client.post("/api/v1/pagos-gestores/programar", json=datos_gestor).status_code == 409
    assert (
        client.delete(f"/api/v1/pagos-gestores/{programado_gestor.json()['id']}").status_code == 204
    )
