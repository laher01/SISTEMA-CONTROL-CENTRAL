"""Regresión aislada #240: expedientes pendientes no deben financiar liquidaciones.

No altera la función de cálculo compartida con PR #102.
La prueba pendiente queda xfail estricto hasta corregir la regla de aprobación.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Miembro
from tests.conftest import AuthPrueba


@pytest.mark.parametrize(
    ("pendiente_aprobacion", "produccion_esperada"),
    [
        (False, Decimal("1000.00")),
        pytest.param(
            True,
            Decimal("0.00"),
            marks=pytest.mark.xfail(
                strict=True,
                reason="Issue #240: producción pendiente incluida en la cotización",
            ),
        ),
    ],
)
def test_cotizacion_excluye_expediente_pendiente(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
    pendiente_aprobacion: bool,
    produccion_esperada: Decimal,
) -> None:
    auth_prueba.como_admin()
    tenant_id = auth_prueba.contexto.tenant_id
    usuario = session.query(Miembro).filter_by(tenant_id=tenant_id, codigo="TESTUSR").one()
    usuario.porcentaje_con_agente = Decimal("2.00")
    usuario.porcentaje_sin_agente = Decimal("2.00")
    emisor = Empresa(tenant_id=tenant_id, ruc="20123456789", razon_social="Emisor prueba")
    receptor = Empresa(
        tenant_id=tenant_id,
        ruc="20987654321",
        razon_social="Receptor prueba",
        agente_retencion=False,
    )
    session.add_all([emisor, receptor])
    session.flush()
    session.add(
        Expediente(
            tenant_id=tenant_id,
            receptor_id=receptor.id,
            emisor_id=emisor.id,
            usuario_id=usuario.id,
            tipo_comprobante="01",
            serie="F001",
            correlativo="000001",
            fecha_emision=date(2026, 9, 10),
            moneda="PEN",
            importe_total=Decimal("1000.00"),
            pendiente_aprobacion=pendiente_aprobacion,
        )
    )
    session.commit()
    respuesta = client.post(
        "/api/v1/responsable/pagos/cotizar",
        json={
            "usuario_id": str(usuario.id),
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": "PEN",
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    real = Decimal(respuesta.json()["produccion"])
    assert real == produccion_esperada
