from fastapi.testclient import TestClient

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


def test_configuracion_acceso_es_exclusiva_de_superadmin(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()
    respuesta = client.get("/api/v1/configuracion/acceso")
    assert respuesta.status_code == 403

    auth_prueba.como_superadmin()
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
    auth_prueba.como_superadmin()

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
    auth_prueba.como_superadmin()
    config = client.put(
        "/api/v1/configuracion/acceso",
        json={
            "registro_publico": True,
            "requiere_aprobacion": True,
            "solo_correos_autorizados": True,
            "requiere_email_verificado": False,
            "acceso_cloudflare_activo": True,
        },
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
    auth_prueba.como_superadmin()
    respuesta = client.put(
        "/api/v1/configuracion/acceso",
        json=configuracion_payload(registro_publico=True, requiere_aprobacion=False),
    )
    assert respuesta.status_code == 409
