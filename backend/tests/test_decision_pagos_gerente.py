"""El Gerente decide qué expedientes históricos incorpora sin tocar otras gerencias."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Miembro
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_gerente_incorpora_historicos_con_auditoria_y_aislamiento(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tid = auth_prueba.contexto.tenant_id
    global_g = Miembro(tenant_id=tid, codigo="GRTEGLOBAL", nombre="Global", rol="GERENTE")
    other_g = Miembro(tenant_id=tid, codigo="G-OTRO", nombre="Otro", rol="GERENTE")
    responsable = Miembro(
        tenant_id=tid, codigo="RESP-H", nombre="Responsable", rol="RESPONSABLE", activo=True
    )
    usuario = Miembro(tenant_id=tid, codigo="US-H", nombre="Usuario", rol="USUARIO")
    empresa = Empresa(
        tenant_id=tid, ruc="20990001111", razon_social="CLIENTE PRUEBA",
        tipo_relacion="CLIENTE",
    )
    session.add_all([global_g, other_g, responsable, usuario, empresa])
    session.flush()
    usuario.responsable_id = responsable.id
    pendientes = []
    for correlativo, gerente in [("101", None), ("102", other_g.id)]:
        item = Expediente(
            tenant_id=tid, emisor_id=empresa.id, receptor_id=empresa.id,
            tipo_comprobante="FACT", serie="F001", correlativo=correlativo,
            fecha_emision=date(2026, 8, 10), moneda="PEN",
            importe_total=Decimal("100"), usuario_id=usuario.id, gerente_id=gerente,
        )
        session.add(item)
        pendientes.append(item)
    session.commit()

    def sesion_gerente(m: Miembro) -> None:
        anterior = auth_prueba.contexto
        auth_prueba.contexto = ContextoAcceso(
            cuenta_id=anterior.cuenta_id, tenant_id=tid, rol="GERENTE",
            miembro_id=m.id, usuario_id=None, gestor_id=None,
            codigo=m.codigo, nombre=m.nombre, cambio_clave_obligatorio=False,
        )

    args = {
        "responsable_id": str(responsable.id), "desde": "2026-08-01",
        "hasta": "2026-08-31", "moneda": "PEN",
    }
    sesion_gerente(other_g)
    assert (
        client.post("/api/v1/pagos-responsables/incorporar-historicos", json=args).status_code
        == 403
    )
    sesion_gerente(global_g)
    r = client.post("/api/v1/pagos-responsables/incorporar-historicos", json=args)
    assert r.status_code == 200, r.text
    assert r.json()["cantidad"] == 1
    session.refresh(pendientes[0])
    session.refresh(pendientes[1])
    assert pendientes[0].gerente_id == global_g.id
    assert pendientes[1].gerente_id == other_g.id
    assert (
        client.post("/api/v1/pagos-responsables/incorporar-historicos", json=args).status_code
        == 422
    )
    resumen = client.get("/api/v1/pagos-responsables/resumen", params={
        "desde": "2026-08-01", "hasta": "2026-08-31", "moneda": "PEN",
    })
    assert resumen.status_code == 200, resumen.text
    assert Decimal(resumen.json()["total_produccion"]) == Decimal("100")
    assert Decimal(resumen.json()["total_comisiones"]) == Decimal("3.5")
