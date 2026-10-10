"""Visibilidad jerárquica y resumen de empresas según expedientes."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Miembro
from tests.conftest import AuthPrueba


@pytest.mark.parametrize("rol", ["GERENTE", "SECRETARIA"])
def test_gerencia_secretaria_crean_responsables_compartidos(
    client: TestClient, auth_prueba: AuthPrueba, rol: str
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    respuesta = client.post(
        "/api/v1/miembros/responsables-operativos",
        json={"nombre": "Responsable compartido"},
    )
    assert respuesta.status_code == 201, respuesta.text
    creado = respuesta.json()["miembro"]
    assert creado["rol"] == "RESPONSABLE"
    listado = client.get("/api/v1/miembros", params={"rol": "RESPONSABLE"})
    assert listado.status_code == 200, listado.text
    assert creado["id"] in [r["id"] for r in listado.json()]
    auth_prueba.como_admin()
    lista_admin = client.get("/api/v1/miembros", params={"rol": "RESPONSABLE"})
    assert creado["id"] in [r["id"] for r in lista_admin.json()]


def test_roles_no_autorizados_no_crean_responsables(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_usuario(auth_prueba.contexto.usuario_id)
    respuesta = client.post(
        "/api/v1/miembros/responsables-operativos",
        json={"nombre": "No debe crearse"},
    )
    assert respuesta.status_code == 403


def test_resumen_por_empresa_respeta_fechas_monedas_y_usuario(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant = auth_prueba.contexto.tenant_id
    usuario = session.query(Miembro).filter_by(tenant_id=tenant, codigo="TESTUSR").one()
    otra_cuenta = Miembro(tenant_id=tenant, codigo="OTRO-USER", nombre="Otro", rol="USUARIO")
    emisor = Empresa(tenant_id=tenant, ruc="20111111111", razon_social="Proveedor A")
    receptor = Empresa(tenant_id=tenant, ruc="20222222222", razon_social="Cliente B")
    session.add_all([otra_cuenta, emisor, receptor])
    session.flush()
    for uid, mes, monto, correlativo, moneda in [
        (usuario.id, date(2026, 10, 1), "100.50", "1", "PEN"),
        (usuario.id, date(2026, 9, 1), "90", "2", "PEN"),
        (otra_cuenta.id, date(2026, 10, 2), "999", "3", "PEN"),
        (usuario.id, date(2026, 10, 3), "5", "4", "USD"),
    ]:
        session.add(
            Expediente(
                tenant_id=tenant,
                usuario_id=uid,
                receptor_id=receptor.id,
                emisor_id=emisor.id,
                tipo_comprobante="01",
                serie="F001",
                correlativo=correlativo,
                fecha_emision=mes,
                moneda=moneda,
                importe_total=Decimal(monto),
            )
        )
    session.commit()
    auth_prueba.como_usuario(usuario.id)
    respuesta = client.get(
        "/api/v1/expedientes/resumen-empresas",
        params={"fecha_desde": "2026-10-01", "fecha_hasta": "2026-10-31", "moneda": "PEN"},
    )
    assert respuesta.status_code == 200, respuesta.text
    data = respuesta.json()
    assert len(data["proveedores"]) == 1
    assert len(data["clientes"]) == 1
    assert Decimal(data["proveedores"][0]["total"]) == Decimal("100.50")
    assert data["clientes"][0]["expedientes"] == 1
    assert data["proveedores"][0]["expedientes"] == 1
    assert Decimal(data["clientes"][0]["total"]) == Decimal("100.50")
    # Cada expediente se contabiliza una vez por perspectiva, no se suman ambas pestañas.
    segunda_consulta = client.get(
        "/api/v1/expedientes/resumen-empresas",
        params={"fecha_desde": "2026-10-01", "fecha_hasta": "2026-10-31", "moneda": "PEN"},
    )
    assert segunda_consulta.status_code == 200
    assert segunda_consulta.json() == data
    todas = client.get("/api/v1/expedientes/resumen-empresas")
    assert todas.status_code == 200
    acumulado = todas.json()
    assert sum(fila["expedientes"] for fila in acumulado["proveedores"]) == 3
    assert sum(fila["expedientes"] for fila in acumulado["clientes"]) == 3
    assert sum(Decimal(fila["total"]) for fila in acumulado["proveedores"] if fila["moneda"] == "PEN") == Decimal("190.50")
    assert sum(Decimal(fila["total"]) for fila in acumulado["clientes"] if fila["moneda"] == "USD") == Decimal("5")
    assert (
        client.get(
            "/api/v1/expedientes/resumen-empresas",
            params={"fecha_desde": "2026-11-01", "fecha_hasta": "2026-10-01"},
        ).status_code
        == 422
    )
