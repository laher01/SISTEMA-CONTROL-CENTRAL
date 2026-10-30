"""Regresión transversal: importes documentales y base vigente de comisiones.

No modifica reglas económicas: documenta explícitamente la diferencia entre
resúmenes autorizados y producción utilizada por el módulo de comisiones.
"""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente
from tests.conftest import AuthPrueba, completar_facturas_de_prueba


def test_resumen_autorizado_y_produccion_comisiones_con_pendiente(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    emisor = Empresa(tenant_id=tenant_id, ruc="20111111111", razon_social="Emisor prueba")
    receptor = Empresa(
        tenant_id=tenant_id,
        ruc="20222222222",
        razon_social="Receptor autorizado",
        autorizada=True,
    )
    session.add_all([emisor, receptor])
    session.flush()
    expedientes = [
        Expediente(
            tenant_id=tenant_id,
            emisor_id=emisor.id,
            receptor_id=receptor.id,
            tipo_comprobante="01",
            serie="F001",
            correlativo=correlativo,
            fecha_emision=date(2026, 10, 19),
            moneda="PEN",
            importe_total=importe,
            usuario_id=usuario_id,
            pendiente_aprobacion=pendiente,
        )
        for correlativo, importe, pendiente in (
            ("00000001", Decimal("300.00"), False),
            ("00000002", Decimal("125.00"), True),
        )
    ]
    session.add_all(expedientes)
    completar_facturas_de_prueba(session)
    session.commit()

    resumen = client.get("/api/v1/expedientes/resumen")
    assert resumen.status_code == 200, resumen.text
    assert Decimal(str(resumen.json()["total_pen"])) == Decimal("425.00")
    assert Decimal(str(resumen.json()["total_pen_autorizado"])) == Decimal("300.00")

    parametros = {
        "usuario_id": str(usuario_id),
        "desde": "2026-10-01",
        "hasta": "2026-10-31",
        "moneda": "PEN",
    }
    produccion = client.get("/api/v1/comisiones/produccion-receptores", params=parametros)
    assert produccion.status_code == 200, produccion.text
    # Comportamiento VIGENTE: este endpoint suma expedientes por receptor autorizado,
    # sin filtrar el campo pendiente_aprobacion del expediente.
    # La diferencia con el resumen autorizado se documenta, no se altera.
    assert len(produccion.json()) == 1
    assert Decimal(produccion.json()[0]["produccion"]) == Decimal("425.00")

    expedientes[1].pendiente_aprobacion = False
    completar_facturas_de_prueba(session)
    session.commit()
    aprobado = client.get("/api/v1/expedientes/resumen")
    assert aprobado.status_code == 200, aprobado.text
    assert Decimal(str(aprobado.json()["total_pen_autorizado"])) == Decimal("425.00")

    expedientes[1].pendiente_aprobacion = True
    completar_facturas_de_prueba(session)
    session.commit()
    revocado = client.get("/api/v1/expedientes/resumen")
    assert revocado.status_code == 200, revocado.text
    assert Decimal(str(revocado.json()["total_pen_autorizado"])) == Decimal("300.00")
    assert Decimal(str(revocado.json()["total_pen"])) == Decimal("425.00")
