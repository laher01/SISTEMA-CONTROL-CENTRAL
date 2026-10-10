from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CuentaAcceso, CuentaPagoERP, Miembro, PlanLiquidacion
from tests.conftest import AuthPrueba


def configuracion_payload(
    *,
    registro_publico: bool,
    requiere_aprobacion: bool = True,
) -> dict[str, object]:
    return {
        "registro_publico": registro_publico,
        "requiere_aprobacion": requiere_aprobacion,
        "solo_correos_autorizados": True,
        "requiere_email_verificado": False,
        "acceso_cloudflare_activo": True,
        "duracion_sesion_horas": 12,
        "intentos_fallidos_max": 5,
        "bloqueo_minutos": 15,
        "clave_min_longitud": 10,
        "clave_requiere_letra": True,
        "clave_requiere_numero": True,
    }


def test_configuracion_acceso_es_exclusiva_de_administrador(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_superadmin()
    respuesta = client.get("/api/v1/configuracion/acceso")
    assert respuesta.status_code == 403

    auth_prueba.como_admin()
    respuesta = client.get("/api/v1/configuracion/acceso")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["registro_publico"] is False
    assert datos["requiere_aprobacion"] is True
    assert datos["solo_correos_autorizados"] is True
    assert datos["proveedor_email_configurado"] is False


def test_superadmin_autoriza_correo_y_habilita_solicitudes(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()

    correo = client.post(
        "/api/v1/configuracion/acceso/correos",
        json={"email": "usuario@empresa.com", "rol_sugerido": "USUARIO"},
    )
    assert correo.status_code == 201, correo.text
    assert correo.json()["email"] == "usuario@empresa.com"

    config = client.put(
        "/api/v1/configuracion/acceso",
        json=configuracion_payload(registro_publico=True),
    )
    assert config.status_code == 200, config.text

    publico = client.get("/api/v1/auth/acceso-publico")
    assert publico.status_code == 200
    assert publico.json() == {"registro_publico": True}

    solicitud = client.post(
        "/api/v1/auth/solicitar-acceso",
        json={
            "email": "usuario@empresa.com",
            "nombre": "Usuario Nuevo",
            "codigo_solicitado": "USUARIO01",
        },
    )
    assert solicitud.status_code == 201, solicitud.text
    assert solicitud.json()["estado"] == "PENDIENTE"


def test_no_permite_solicitud_con_correo_no_autorizado(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()
    config = client.put(
        "/api/v1/configuracion/acceso",
        json=configuracion_payload(registro_publico=True),
    )
    assert config.status_code == 200, config.text

    respuesta = client.post(
        "/api/v1/auth/solicitar-acceso",
        json={
            "email": "noautorizado@empresa.com",
            "nombre": "No Autorizado",
            "codigo_solicitado": "NOAUT01",
        },
    )
    assert respuesta.status_code == 403


def test_no_permite_desactivar_aprobacion_sin_verificacion_email(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()
    respuesta = client.put(
        "/api/v1/configuracion/acceso",
        json=configuracion_payload(registro_publico=True, requiere_aprobacion=False),
    )
    assert respuesta.status_code == 409


def test_mantenimiento_es_exclusivo_de_administrador(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_superadmin()
    respuesta = client.get("/api/v1/configuracion/mantenimiento/administradores")
    assert respuesta.status_code == 403
    auth_prueba.como_admin()
    respuesta = client.get("/api/v1/configuracion/mantenimiento/administradores")
    assert respuesta.status_code == 200, respuesta.text


def test_administrador_previsualiza_y_limpia_su_tenant(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    administrador = Miembro(
        tenant_id=tenant_id,
        codigo="ADMIN02",
        nombre="Administrador dos",
        rol="ADMINISTRADOR",
        activo=True,
    )
    usuario = Miembro(
        tenant_id=tenant_id,
        codigo="USR-MANT",
        nombre="Usuario mantenimiento",
        rol="USUARIO",
        activo=True,
    )
    session.add_all([administrador, usuario])
    session.flush()
    cuenta = CuentaAcceso(
        tenant_id=tenant_id,
        login="ADMIN02",
        password_hash="test-hash",
        miembro_id=administrador.id,
        gestor_id=None,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta)
    session.flush()
    plan = PlanLiquidacion(
        tenant_id=tenant_id,
        usuario_id=usuario.id,
        creado_por_cuenta_id=cuenta.id,
        nombre="Plan de prueba",
        porcentaje=Decimal("2.2"),
        vigencia_desde=date(2026, 10, 1),
        vigencia_hasta=None,
        activo=True,
    )
    cuenta_pago = CuentaPagoERP(
        tenant_id=tenant_id,
        usuario_id=usuario.id,
        creado_por_cuenta_id=cuenta.id,
        titular="Usuario mantenimiento",
        banco="Banco prueba",
        tipo_cuenta="AHORROS",
        moneda="PEN",
        numero_cuenta="123",
        cci=None,
        porcentaje_distribucion=Decimal("100"),
        activa=True,
    )
    session.add_all([plan, cuenta_pago])
    session.commit()

    auth_prueba.como_admin()
    listado = client.get("/api/v1/configuracion/mantenimiento/administradores")
    assert listado.status_code == 200, listado.text
    fila = next(item for item in listado.json() if item["login"] == "ADMIN02")
    assert fila["registros"]["planes"] == 1
    assert fila["registros"]["cuentas_pago"] == 1

    seleccion = {
        "cuenta_ids": [str(cuenta.id)],
        "incluir_sin_trazabilidad": False,
        "tipos": ["planes", "cuentas_pago"],
        "fecha_desde": None,
        "fecha_hasta": None,
    }
    previa = client.post(
        "/api/v1/configuracion/mantenimiento/vista-previa",
        json=seleccion,
    )
    assert previa.status_code == 200, previa.text
    assert previa.json()["totales"] == {"planes": 1, "cuentas_pago": 1}

    limpieza = client.post(
        "/api/v1/configuracion/mantenimiento/limpiar",
        json={**seleccion, "confirmacion": "ELIMINAR-DATOS-OPERATIVOS"},
    )
    assert limpieza.status_code == 200, limpieza.text
    assert limpieza.json()["eliminados"] == {"planes": 1, "cuentas_pago": 1}



def test_administrador_no_puede_modificar_cuenta_ni_revocar_sesion_de_otro_tenant(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.models import SesionAcceso, Tenant

    tenant_externo = Tenant(
        nombre="TENANT EXTERNO AISLADO", codigo="EXTERNO-E2E", estado="ACTIVO"
    )
    session.add(tenant_externo)
    session.flush()
    miembro_externo = Miembro(
        tenant_id=tenant_externo.id,
        codigo="ADMIN-EXTERNO",
        nombre="Administrador externo",
        rol="ADMINISTRADOR",
        activo=True,
    )
    session.add(miembro_externo)
    session.flush()
    cuenta_externa = CuentaAcceso(
        tenant_id=tenant_externo.id,
        login="ADMIN-EXTERNO",
        password_hash="test-hash",
        miembro_id=miembro_externo.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta_externa)
    session.flush()
    sesion_externa = SesionAcceso(
        tenant_id=tenant_externo.id,
        cuenta_id=cuenta_externa.id,
        token_hash="a" * 64,
        rol_activo="ADMINISTRADOR",
        expira_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(sesion_externa)
    session.commit()

    auth_prueba.como_admin()
    base = "/api/v1/configuracion/acceso"
    assert client.get(f"{base}/cuentas").status_code == 200
    assert all(
        item["id"] != str(cuenta_externa.id)
        for item in client.get(f"{base}/cuentas").json()
    )
    assert client.patch(
        f"{base}/cuentas/{cuenta_externa.id}", json={"activo": False}
    ).status_code == 404
    assert client.post(
        f"{base}/cuentas/{cuenta_externa.id}/restablecer-clave"
    ).status_code == 404
    assert client.delete(f"{base}/sesiones/{sesion_externa.id}").status_code == 404

    session.refresh(cuenta_externa)
    session.refresh(sesion_externa)
    assert cuenta_externa.activo is True
    assert sesion_externa.revocada_at is None



def test_administrador_no_modifica_ni_elimina_empresas_ajenas(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    from app.models import Empresa, Tenant

    ajeno = Tenant(nombre="OTRO ESPACIO EMPRESAS", codigo="OTRO-EMP", estado="ACTIVO")
    session.add(ajeno)
    session.flush()
    empresa = Empresa(
        tenant_id=ajeno.id,
        ruc="20123456789",
        razon_social="Empresa externa de prueba",
        tipo_relacion="PROVEEDOR",
    )
    session.add(empresa)
    session.commit()

    auth_prueba.como_admin()
    listado = client.get("/api/v1/empresas")
    assert listado.status_code == 200, listado.text
    assert all(fila["id"] != str(empresa.id) for fila in listado.json())

    respuesta = client.patch(
        f"/api/v1/empresas/{empresa.id}",
        json={"razon_social": "No debe aplicarse"},
    )
    assert respuesta.status_code == 404, respuesta.text

    respuesta = client.post(
        "/api/v1/empresas/eliminar-seleccion",
        json={"empresa_ids": [str(empresa.id)]},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["eliminadas"] == 0
    session.refresh(empresa)
    assert empresa.deleted_at is None
    assert empresa.razon_social == "Empresa externa de prueba"



def test_administrador_no_accede_a_documento_de_otro_tenant(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    from app.models import Documento, Tenant

    externo = Tenant(nombre="OTRO ESPACIO DOCUMENTAL", codigo="OTRO-DOC", estado="ACTIVO")
    session.add(externo)
    session.flush()
    documento = Documento(
        tenant_id=externo.id,
        sha256="b" * 64,
        nombre_original="externo.pdf",
        mime_type="application/pdf",
        tamano_bytes=10,
        ruta_storage="externo/no-accesible.pdf",
        estado="PENDIENTE",
    )
    session.add(documento)
    session.commit()

    auth_prueba.como_admin()
    for sufijo in ("", "/archivo"):
        respuesta = client.get(f"/api/v1/documentos/{documento.id}{sufijo}")
        assert respuesta.status_code == 404, respuesta.text

    respuesta = client.delete(f"/api/v1/documentos/{documento.id}")
    assert respuesta.status_code == 404, respuesta.text

    session.refresh(documento)
    assert documento.deleted_at is None
