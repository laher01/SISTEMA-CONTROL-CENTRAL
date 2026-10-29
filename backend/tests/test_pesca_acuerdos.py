from datetime import date
from decimal import Decimal

from app.models import CuentaAcceso, Miembro
from app.pesca.models import AsignacionRolPesca, OperacionPesca
from app.security import ContextoAcceso
from app.services.expedientes import obtener_tenant


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


def test_usuario_de_otro_tenant_no_puede_listar_documentos_de_la_operacion(
    client, session, auth_prueba
):
    contexto = auth_prueba.contexto
    operacion = OperacionPesca(
        tenant_id=contexto.tenant_id,
        fecha_reporte=date(2026, 10, 29),
        puerto="Paita",
        muelle="Muelle 1",
        planta="Planta de prueba",
        responsable_id=contexto.codigo,
        estado="preparacion",
    )
    tenant_b = obtener_tenant(session, "otra-empresa-pesquera")
    miembro_b = Miembro(
        tenant_id=tenant_b.id,
        codigo="JEFE-B",
        nombre="Jefe de Bahía B",
        rol="USUARIO",
        activo=True,
    )
    session.add_all([operacion, miembro_b])
    session.flush()
    cuenta_b = CuentaAcceso(
        tenant_id=tenant_b.id,
        login="JEFE-B",
        password_hash="test-hash",
        miembro_id=miembro_b.id,
        gestor_id=None,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta_b)
    session.flush()
    session.add(
        AsignacionRolPesca(
            tenant_id=tenant_b.id,
            cuenta_id=cuenta_b.id,
            rol="JEFE_BAHIA",
            activa=True,
            asignado_por_cuenta_id=cuenta_b.id,
        )
    )
    session.commit()
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=cuenta_b.id,
        tenant_id=tenant_b.id,
        rol="USUARIO",
        miembro_id=miembro_b.id,
        gestor_id=None,
        usuario_id=miembro_b.id,
        codigo=miembro_b.codigo,
        nombre=miembro_b.nombre,
        cambio_clave_obligatorio=False,
    )

    response = client.get(f"/api/v1/pesca/operaciones/{operacion.id}/documentos")

    assert response.status_code == 404


def test_observacion_documental_exige_motivo_y_nueva_version_conserva_trazabilidad(
    client, session, auth_prueba
):
    contexto = auth_prueba.contexto
    for rol in ("ARMADOR", "JEFE_BAHIA"):
        session.add(
            AsignacionRolPesca(
                tenant_id=contexto.tenant_id,
                cuenta_id=contexto.cuenta_id,
                rol=rol,
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
        responsable_id=contexto.codigo,
        estado="preparacion",
    )
    session.add(operacion)
    session.commit()

    primera = client.post(
        f"/api/v1/pesca/operaciones/{operacion.id}/documentos",
        data={"tipo": "otro", "etapa": "GENERAL"},
        files={"archivo": ("permiso.pdf", b"%PDF-1.7 primera version", "application/pdf")},
    )
    assert primera.status_code == 201
    primera_doc = primera.json()
    assert primera_doc["version"] == 1
    assert primera_doc["estado_revision"] == "PENDIENTE"

    sin_motivo = client.put(
        f"/api/v1/pesca/documentos/{primera_doc['id']}/revision",
        json={"estado": "OBSERVADO"},
    )
    assert sin_motivo.status_code == 422

    observada = client.put(
        f"/api/v1/pesca/documentos/{primera_doc['id']}/revision",
        json={"estado": "OBSERVADO", "observacion": "Adjunta el permiso legible"},
    )
    assert observada.status_code == 200
    assert observada.json()["observacion_revision"] == "Adjunta el permiso legible"

    segunda = client.post(
        f"/api/v1/pesca/operaciones/{operacion.id}/documentos",
        data={
            "tipo": "otro",
            "etapa": "GENERAL",
            "reemplaza_documento_id": primera_doc["id"],
        },
        files={"archivo": ("permiso-v2.pdf", b"%PDF-1.7 segunda version", "application/pdf")},
    )
    assert segunda.status_code == 201
    segunda_doc = segunda.json()
    assert segunda_doc["version"] == 2
    assert segunda_doc["documento_anterior_id"] == primera_doc["id"]
