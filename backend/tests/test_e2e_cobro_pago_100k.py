"""End-to-end synthetic test for document ingestion, manager collections, and user payout."""

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CuentaAcceso,
    Documento,
    Empresa,
    Expediente,
    GerenteEmpresa,
    GerenteResponsable,
    Miembro,
    PagoERP,
    PagoResponsableERP,
)
from tests.conftest import AuthPrueba
from tests.xml import factura


@pytest.mark.parametrize(
    ("scenario", "expected_by_manager"),
    [
        ("un_solo_gerente", (Decimal("100000.00"), Decimal("0.00"))),
        ("mitad_y_mitad", (Decimal("50000.00"), Decimal("50000.00"))),
    ],
)
def test_flujo_e2e_documentos_cobro_a_gerentes_y_pago_a_usuario(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
    scenario: str,
    expected_by_manager: tuple[Decimal, Decimal],
) -> None:
    """Run the same S/ 100,000 production through both manager allocation options."""
    tenant_id = auth_prueba.contexto.tenant_id
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None

    usuario = session.get(Miembro, usuario_id)
    assert usuario is not None
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo=f"RESP-E2E-{scenario}",
        nombre="Responsable E2E",
        rol="RESPONSABLE",
        activo=True,
    )
    gerentes = [
        Miembro(
            tenant_id=tenant_id,
            codigo=f"GER-E2E-{index}-{scenario}",
            nombre=f"Gerente E2E {index}",
            rol="GERENTE",
            activo=True,
        )
        for index in (1, 2)
    ]
    clientes = [
        Empresa(
            tenant_id=tenant_id,
            ruc=f"201111111{index:02d}",
            razon_social=f"CLIENTE E2E {index}",
            autorizada=True,
            tipo_relacion="CLIENTE",
            agente_retencion=False,
        )
        for index in (1, 2)
    ]
    usuario.responsable_id = responsable.id
    usuario.porcentaje_con_agente = Decimal("2.0")
    usuario.porcentaje_sin_agente = Decimal("1.5")

    cuenta_responsable = CuentaAcceso(
        tenant_id=tenant_id,
        login=f"RESP-E2E-{scenario}",
        password_hash="hash-e2e",
        miembro_id=responsable.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    cuentas_gerentes = [
        CuentaAcceso(
            tenant_id=tenant_id,
            login=f"GER-E2E-{index}-{scenario}",
            password_hash="hash-e2e",
            miembro_id=gerente.id,
            activo=True,
            cambio_clave_obligatorio=False,
        )
        for index, gerente in enumerate(gerentes, start=1)
    ]
    session.add_all([responsable, *gerentes, *clientes, cuenta_responsable, *cuentas_gerentes])
    session.flush()

    for gerente in gerentes:
        session.add(
            GerenteResponsable(
                tenant_id=tenant_id,
                gerente_id=gerente.id,
                responsable_id=responsable.id,
                activo=True,
            )
        )
    for index, gerente in enumerate(gerentes):
        session.add(
            GerenteEmpresa(
                tenant_id=tenant_id,
                gerente_id=gerente.id,
                empresa_id=clientes[index].id,
                activo=True,
            )
        )
    session.commit()

    # Ingest actual synthetic UBL invoices through the same upload API as the application.
    invoice_number = 1000
    for gerente_index, production in enumerate(expected_by_manager):
        invoice_count = int(production / Decimal("10000.00"))
        for _ in range(invoice_count):
            numero = f"F001-{invoice_number:08d}"
            cliente = clientes[gerente_index]
            response = client.post(
                "/api/v1/documentos",
                files={
                    "archivo": (
                        f"{numero}.xml",
                        factura(
                            numero=numero,
                            importe="10000.00",
                            receptor=cliente.ruc,
                            fecha="2026-09-15",
                        ),
                    )
                },
            )
            assert response.status_code == 201, response.text
            invoice_number += 1

    session.expire_all()
    expedientes = list(
        session.scalars(
            select(Expediente).where(
                Expediente.tenant_id == tenant_id,
                Expediente.usuario_id == usuario_id,
                Expediente.deleted_at.is_(None),
            )
        )
    )
    assert len(expedientes) == 10
    total_produccion = sum((Decimal(e.importe_total) for e in expedientes), Decimal("0"))
    assert total_produccion == Decimal("100000.00")
    assert all(
        any(documento.deleted_at is None for documento in expediente.documentos)
        for expediente in expedientes
    )
    expediente_ids = [str(expediente.id) for expediente in expedientes]

    # The Responsible sees exactly the intended portfolio split and asks each
    # participating Manager to settle their share.
    auth_prueba.contexto = replace(
        auth_prueba.contexto,
        cuenta_id=cuenta_responsable.id,
        miembro_id=responsable.id,
        rol="RESPONSABLE",
        usuario_id=None,
        gestor_id=None,
        codigo=responsable.codigo,
        nombre=responsable.nombre,
    )
    periodo = {"desde": "2026-09-01", "hasta": "2026-09-30", "moneda": "PEN"}
    pagos_gerentes: list[str] = []
    for index, produccion_esperada in enumerate(expected_by_manager):
        if produccion_esperada == 0:
            continue
        gerente = gerentes[index]
        cuenta_gerente = cuentas_gerentes[index]

        resumen = client.get(
            "/api/v1/pagos-responsables/equipo-resumen",
            params={**periodo, "gerente_ids": str(gerente.id)},
        )
        assert resumen.status_code == 200, resumen.text
        assert resumen.json()["gerentes"][0]["produccion"] == str(produccion_esperada)

        solicitud = client.post(
            "/api/v1/pagos-responsables/solicitudes-cobro",
            json={"gerente_id": str(gerente.id), **periodo},
        )
        assert solicitud.status_code == 201, solicitud.text
        assert solicitud.json()["produccion"] == str(produccion_esperada)

        auth_prueba.contexto = replace(
            auth_prueba.contexto,
            cuenta_id=cuenta_gerente.id,
            miembro_id=gerente.id,
            rol="GERENTE",
            usuario_id=None,
            gestor_id=None,
            codigo=gerente.codigo,
            nombre=gerente.nombre,
        )
        recibidas = client.get("/api/v1/pagos-responsables/solicitudes-cobro")
        assert recibidas.status_code == 200, recibidas.text
        assert any(item["id"] == solicitud.json()["id"] for item in recibidas.json())

        programado = client.post(
            "/api/v1/pagos-responsables/programar",
            json={"responsable_id": str(responsable.id), **periodo},
        )
        assert programado.status_code == 201, programado.text
        assert Decimal(programado.json()["comision_total"]) == Decimal(solicitud.json()["comision"])
        pago_gerente_id = programado.json()["id"]
        confirmado = client.post(
            f"/api/v1/pagos-responsables/{pago_gerente_id}/confirmar",
            json={
                "fecha_pago": "2026-09-30",
                "referencia_pago": f"E2E-{scenario}-GER-{index + 1}",
            },
        )
        assert confirmado.status_code == 200, confirmado.text
        assert confirmado.json()["estado"] == "PAGADO"
        pagos_gerentes.append(pago_gerente_id)

        auth_prueba.contexto = replace(
            auth_prueba.contexto,
            cuenta_id=cuenta_responsable.id,
            miembro_id=responsable.id,
            rol="RESPONSABLE",
            usuario_id=None,
            gestor_id=None,
            codigo=responsable.codigo,
            nombre=responsable.nombre,
        )

    # The Responsible quotes, schedules, and confirms the User's invoice-based
    # commission once across all ten ingested invoices.
    pago_usuario_datos = {
        "usuario_id": str(usuario_id),
        **periodo,
        "expediente_ids": expediente_ids,
    }
    cotizacion = client.post("/api/v1/responsable/pagos/cotizar", json=pago_usuario_datos)
    assert cotizacion.status_code == 200, cotizacion.text
    assert cotizacion.json()["produccion"] == "100000.00"
    assert cotizacion.json()["bruto"] == "1500.00"
    assert cotizacion.json()["neto"] == "1500.00"

    pago_usuario = client.post("/api/v1/responsable/pagos/programar", json=pago_usuario_datos)
    assert pago_usuario.status_code == 201, pago_usuario.text
    assert pago_usuario.json()["saldo"] == "1500.00"
    confirmado_usuario = client.post(
        f"/api/v1/responsable/pagos/{pago_usuario.json()['id']}/confirmar",
        json={
            "fecha_pago": "2026-09-30",
            "referencia_pago": f"E2E-{scenario}-PAGO-USUARIO",
        },
    )
    assert confirmado_usuario.status_code == 200, confirmado_usuario.text

    session.expire_all()
    pago_usuario_db = session.get(PagoERP, UUID(pago_usuario.json()["id"]))
    assert pago_usuario_db is not None and pago_usuario_db.estado == "PAGADO"
    pagos_gerentes_db = [
        session.get(PagoResponsableERP, UUID(pago_id)) for pago_id in pagos_gerentes
    ]
    assert all(pago is not None and pago.estado == "PAGADO" for pago in pagos_gerentes_db)
    assert (
        session.scalar(
            select(Documento.id).where(
                Documento.tenant_id == tenant_id,
                Documento.expediente_id.in_([expediente.id for expediente in expedientes]),
                Documento.deleted_at.is_(None),
            )
        )
        is not None
    )
