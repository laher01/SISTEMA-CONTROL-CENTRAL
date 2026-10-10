"""Regresión: los resúmenes históricos de GRTEGLOBAL no desaparecen al activar gerencias."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Miembro
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_pagos_consolidados_historicos_y_privacidad(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    gerente_global = Miembro(
        tenant_id=tenant_id, codigo="GRTEGLOBAL", nombre="Gerente histórico", rol="GERENTE"
    )
    gerente_dos = Miembro(
        tenant_id=tenant_id, codigo="GERENTE02", nombre="Otro gerente", rol="GERENTE"
    )
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-HIST",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    usuario = Miembro(
        tenant_id=tenant_id, codigo="US-HIST", nombre="Usuario", rol="USUARIO", activo=True
    )
    cliente = Empresa(
        tenant_id=tenant_id,
        ruc="20998887711",
        razon_social="CLIENTE HISTORICO",
        tipo_relacion="CLIENTE",
    )
    session.add_all([gerente_global, gerente_dos, responsable, usuario, cliente])
    session.flush()
    usuario.responsable_id = responsable.id

    for numero, gerente, monto in [
        ("100", None, "100"),
        ("101", gerente_global.id, "200"),
        ("102", gerente_dos.id, "300"),
    ]:
        session.add(
            Expediente(
                tenant_id=tenant_id,
                emisor_id=cliente.id,
                receptor_id=cliente.id,
                tipo_comprobante="FACT",
                serie="F001",
                correlativo=numero,
                fecha_emision=date(2026, 9, 18),
                moneda="PEN",
                importe_total=Decimal(monto),
                usuario_id=usuario.id,
                gerente_id=gerente,
            )
        )
    session.add(
        Expediente(
            tenant_id=tenant_id,
            emisor_id=cliente.id,
            receptor_id=cliente.id,
            tipo_comprobante="FACT",
            serie="F001",
            correlativo="103",
            fecha_emision=date(2026, 9, 19),
            moneda="PEN",
            importe_total=Decimal("50"),
            usuario_id=None,
            gerente_id=None,
        )
    )
    session.commit()

    def iniciar(gerente: Miembro) -> None:
        anterior = auth_prueba.contexto
        auth_prueba.contexto = ContextoAcceso(
            cuenta_id=anterior.cuenta_id,
            tenant_id=tenant_id,
            rol="GERENTE",
            miembro_id=gerente.id,
            usuario_id=None,
            gestor_id=None,
            codigo=gerente.codigo,
            nombre=gerente.nombre,
            cambio_clave_obligatorio=False,
        )

    params = {"desde": "2026-09-01", "hasta": "2026-09-30", "moneda": "PEN"}
    iniciar(gerente_global)
    consolidado = client.get("/api/v1/pagos/consolidado", params={**params, "agrupar": "CLIENTE"})
    assert consolidado.status_code == 200, consolidado.text
    assert Decimal(consolidado.json()["total"]) == Decimal("350")
    assert consolidado.json()["filas"][0]["registros"] == 3

    por_responsable = client.get(
        "/api/v1/pagos/consolidado", params={**params, "agrupar": "RESPONSABLE"}
    )
    assert por_responsable.status_code == 200, por_responsable.text
    assert Decimal(por_responsable.json()["total"]) == Decimal("350")
    assert any(f["id"] == "sin-responsable" for f in por_responsable.json()["filas"])

    clientes = client.get("/api/v1/pagos/clientes")
    responsables = client.get("/api/v1/pagos/responsables")
    assert clientes.status_code == 200, clientes.text
    assert responsables.status_code == 200, responsables.text
    assert any(c["id"] == str(cliente.id) for c in clientes.json())
    assert any(c["id"] == str(responsable.id) for c in responsables.json())

    liquidacion = client.get("/api/v1/pagos-responsables/resumen", params=params)
    assert liquidacion.status_code == 200, liquidacion.text
    assert Decimal(liquidacion.json()["total_produccion"]) == Decimal("200")
    assert Decimal(liquidacion.json()["total_pendiente_atribucion"]) == Decimal("150")
    assert Decimal(liquidacion.json()["total_comisiones"]) < Decimal("100")
    detalle = liquidacion.json()["detalle_historico_clientes"]
    assert len(detalle) == 1
    assert detalle[0]["responsable_id"] == str(responsable.id)
    assert detalle[0]["cliente_id"] == str(cliente.id)
    assert Decimal(detalle[0]["produccion"]) == Decimal("100")
    assert Decimal(detalle[0]["porcentaje"]) == Decimal("3.5")
    assert Decimal(detalle[0]["comision_referencial"]) == Decimal("3.50")

    iniciar(gerente_dos)
    otro = client.get("/api/v1/pagos/consolidado", params=params)
    assert otro.status_code == 200, otro.text
    assert Decimal(otro.json()["total"]) == Decimal("300")
    otro_liquidacion = client.get("/api/v1/pagos-responsables/resumen", params=params)
    assert otro_liquidacion.status_code == 200, otro_liquidacion.text
    assert "total_pendiente_atribucion" not in otro_liquidacion.json()
