from datetime import date
from decimal import Decimal

from app.pesca.models import AsignacionRolPesca, OperacionPesca


def test_precio_requiere_confirmacion_de_embarcacion_y_rol_autorizado(client, session, auth_prueba):
    contexto = auth_prueba.contexto
    session.add(
        AsignacionRolPesca(
            tenant_id=contexto.tenant_id,
            cuenta_id=contexto.cuenta_id,
            rol="ARMADOR",
            activa=True,
            asignado_por_cuenta_id=contexto.cuenta_id,
        )
    )
    operacion = OperacionPesca(
        tenant_id=contexto.tenant_id,
        fecha_reporte=date(2026, 10, 29),
        puerto="Paita",
        muelle="Muelle 1",
        planta="Planta de prueba",
        precio_propuesto=Decimal("5.25"),
        responsable_id=contexto.codigo,
        estado="preparacion",
    )
    session.add(operacion)
    session.commit()

    auth_prueba.como_admin()
    response = client.post(
        f"/api/v1/pesca/operaciones/{operacion.id}/confirmar-precio",
        json={"acepta_acuerdo": True},
    )
    assert response.status_code == 403

    auth_prueba.contexto = contexto
    respuesta_embarcacion = client.post(
        f"/api/v1/pesca/operaciones/{operacion.id}/confirmar-acuerdo-embarcacion",
        json={"confirma_precio_acordado": True},
    )
    assert respuesta_embarcacion.status_code == 200
    assert respuesta_embarcacion.json()["precio_acuerdo_embarcacion_confirmado"] is True
    assert respuesta_embarcacion.json()["precio_confirmado"] is None

    session.add(
        AsignacionRolPesca(
            tenant_id=contexto.tenant_id,
            cuenta_id=contexto.cuenta_id,
            rol="JEFE_BAHIA",
            activa=True,
            asignado_por_cuenta_id=contexto.cuenta_id,
        )
    )
    session.commit()
    respuesta_jefatura = client.post(
        f"/api/v1/pesca/operaciones/{operacion.id}/confirmar-precio",
        json={"acepta_acuerdo": True},
    )
    assert respuesta_jefatura.status_code == 200
    assert respuesta_jefatura.json()["precio_confirmado"] == "5.25"
