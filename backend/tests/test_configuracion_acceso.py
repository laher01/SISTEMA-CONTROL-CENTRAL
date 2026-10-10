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
