from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente
from tests.conftest import AuthPrueba


def test_produccion_por_receptor_usa_documentos_del_usuario_y_periodo(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    emisor = Empresa(tenant_id=tenant_id, ruc="20111111111", razon_social="Proveedor")
    receptor = Empresa(tenant_id=tenant_id, ruc="20222222222", razon_social="Cliente A")
    session.add_all([emisor, receptor])
    session.flush()
    session.add(
        Expediente(
            tenant_id=tenant_id,
            receptor_id=receptor.id,
            emisor_id=emisor.id,
            tipo_comprobante="01",
            serie="F001",
            correlativo="00000001",
            fecha_emision=date(2026, 10, 5),
            moneda="PEN",
            importe_total=Decimal("120.00"),
            usuario_id=usuario_id,
        )
    )
    session.commit()

    parametros = {
        "usuario_id": str(usuario_id),
        "desde": "2026-10-01",
        "hasta": "2026-10-31",
        "moneda": "PEN",
    }
    respuesta = client.get("/api/v1/comisiones/produccion-receptores", params=parametros)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == [
        {
            "id": str(receptor.id),
            "ruc": receptor.ruc,
            "nombre": receptor.razon_social,
            "expedientes": 1,
            "produccion": "120.00",
        }
    ]
    fuera = client.get(
        "/api/v1/comisiones/produccion-receptores",
        params={**parametros, "desde": "2026-09-01", "hasta": "2026-09-30"},
    )
    assert fuera.status_code == 200
    assert fuera.json() == []
    invalido = client.get(
        "/api/v1/comisiones/produccion-receptores",
        params={**parametros, "usuario_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert invalido.status_code == 404
