"""Regresión: GRTEGLOBAL conserva expedientes históricos no atribuidos."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_gerente_global_ve_historicos_sin_ver_otros_gerentes(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    gerente_global = uuid4()
    otro_gerente = uuid4()
    empresa = Empresa(
        tenant_id=tenant_id, ruc="20995556666",
        razon_social="CLIENTE HISTORICO", tipo_relacion="CLIENTE"
    )
    session.add(empresa)
    session.flush()
    for n, origen in [("100", None), ("101", gerente_global), ("102", otro_gerente)]:
        session.add(
            Expediente(
                tenant_id=tenant_id, receptor_id=empresa.id, emisor_id=empresa.id,
                tipo_comprobante="FACT", serie="F001", correlativo=n,
                fecha_emision=date(2026, 9, 30), moneda="PEN",
                importe_total=Decimal("100"), gerente_id=origen,
            )
        )
    session.commit()

    def ingresar(codigo: str, gerente_id) -> None:
        anterior = auth_prueba.contexto
        auth_prueba.contexto = ContextoAcceso(
            cuenta_id=anterior.cuenta_id, tenant_id=tenant_id, rol="GERENTE",
            miembro_id=gerente_id, usuario_id=None, gestor_id=None,
            codigo=codigo, nombre=codigo, cambio_clave_obligatorio=False,
        )

    ingresar("GRTEGLOBAL", gerente_global)
    registros = client.get("/api/v1/registros")
    assert registros.status_code == 200, registros.text
    assert {f["correlativo"] for f in registros.json()["filas"]} == {"100", "101"}
    expedientes = client.get("/api/v1/expedientes")
    assert expedientes.status_code == 200, expedientes.text
    assert expedientes.json()["total_registros"] == 2

    ingresar("GERENTE02", otro_gerente)
    registros_otros = client.get("/api/v1/registros")
    assert registros_otros.status_code == 200
    assert {f["correlativo"] for f in registros_otros.json()["filas"]} == {"102"}
