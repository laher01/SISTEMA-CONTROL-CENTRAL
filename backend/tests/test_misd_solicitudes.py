"""Solicitud persistente y autorización MISD: sin borrar expedientes."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Auditoria, ChatMensaje, Expediente, SolicitudRetiroMISD
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_solicitud_aprobacion_no_borra_expediente(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("solicitud-misd.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    expediente_id = respuesta.json()["expediente_id"]
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Factura ingresada por error"},
    )
    assert creada.status_code == 201, creada.text
    solicitud_id = creada.json()["id"]
    contexto_solicitante = auth_prueba.contexto
    assert creada.json()["estado"] == "PENDIENTE"
    duplicada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Factura ingresada por error"},
    )
    assert duplicada.status_code == 409

    from dataclasses import replace

    from app.models import CuentaAcceso, Miembro

    administrador = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="ADMIN-MISD",
        nombre="Aprobador MISD",
        rol="ADMINISTRADOR",
        activo=True,
    )
    session.add(administrador)
    session.flush()
    cuenta_admin = CuentaAcceso(
        tenant_id=auth_prueba.contexto.tenant_id,
        login="ADMIN-MISD",
        password_hash="hash-pruebas",
        miembro_id=administrador.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta_admin)
    session.commit()
    auth_prueba.contexto = replace(
        auth_prueba.contexto,
        cuenta_id=cuenta_admin.id,
        miembro_id=administrador.id,
        rol="ADMINISTRADOR",
        usuario_id=None,
        gestor_id=None,
    )
    lista = client.get("/api/v1/misd/solicitudes")
    assert lista.status_code == 200, lista.text
    assert any(item["id"] == solicitud_id for item in lista.json())
    decision = client.post(
        f"/api/v1/misd/solicitudes/{solicitud_id}/resolver",
        json={"aprobar": True, "motivo": "Confirmado para revisión MISD"},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["estado"] == "APROBADA"
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 200
    assert session.query(SolicitudRetiroMISD).count() == 1
    assert (
        session.query(Auditoria).filter(Auditoria.accion == "MISD_SOLICITUD_RESUELTA").count() == 1
    )
    assert session.get(Expediente, expediente_id).deleted_at is None
    repeticion = client.post(
        f"/api/v1/misd/solicitudes/{solicitud_id}/resolver",
        json={"aprobar": True, "motivo": "Segunda resolución no permitida"},
    )
    assert repeticion.status_code == 409
    auth_prueba.contexto = contexto_solicitante
    ejecutada = client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar")
    assert ejecutada.status_code == 200, ejecutada.text
    assert ejecutada.json()["estado"] == "EJECUTADA"
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 404
    assert client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar").status_code == 409


def test_secretaria_no_puede_solicitar_retiro(client: TestClient, auth_prueba: AuthPrueba) -> None:
    from dataclasses import replace

    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("secretaria-misd.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    auth_prueba.contexto = replace(auth_prueba.contexto, rol="SECRETARIA")
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={
            "expediente_id": respuesta.json()["expediente_id"],
            "motivo": "Documento equivocado",
        },
    )
    assert creada.status_code in (403, 404)


def test_misd_solicitud_tenant_ajeno_no_se_puede_consultar_ni_resolver(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    from dataclasses import replace
    from uuid import uuid4

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("misd-tenant.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": subida.json()["expediente_id"], "motivo": "Carga equivocada"},
    )
    assert creada.status_code == 201, creada.text
    solicitud_id = creada.json()["id"]
    auth_prueba.como_admin()
    anterior = auth_prueba.contexto
    auth_prueba.contexto = replace(anterior, tenant_id=uuid4())
    try:
        assert client.get("/api/v1/misd/solicitudes").json() == []
        decision = client.post(
            f"/api/v1/misd/solicitudes/{solicitud_id}/resolver",
            json={"aprobar": True, "motivo": "No corresponde a esta empresa"},
        )
        assert decision.status_code == 404
    finally:
        auth_prueba.contexto = anterior
    assert client.get(f"/api/v1/expedientes/{subida.json()['expediente_id']}").status_code == 200


def test_misd_tenant_ajeno_no_puede_ejecutar_retiro(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    from dataclasses import replace
    from uuid import uuid4

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("misd-ejecutar-tenant.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Corrección documental requerida"},
    )
    assert creada.status_code == 201, creada.text
    solicitud_id = creada.json()["id"]
    original = auth_prueba.contexto
    try:
        auth_prueba.contexto = replace(original, tenant_id=uuid4())
        ajeno = client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar")
        assert ajeno.status_code == 404, ajeno.text
    finally:
        auth_prueba.contexto = original
    assert session.get(Expediente, expediente_id).deleted_at is None
    assert session.get(SolicitudRetiroMISD, solicitud_id).estado == "PENDIENTE"


def test_ejecutar_misd_en_ventana_sin_pagos_consume_solicitud(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("misd-correccion.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Carga realizada por equivocación"},
    )
    assert creada.status_code == 201, creada.text
    solicitud_id = creada.json()["id"]
    ejecutada = client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar")
    assert ejecutada.status_code == 200, ejecutada.text
    assert ejecutada.json()["estado"] == "EJECUTADA"
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 404
    assert client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar").status_code == 409
    assert session.query(Auditoria).filter(Auditoria.accion == "MISD_RETIRO_EJECUTADO").count() == 1


def test_misd_fuera_de_ventana_exige_aprobacion(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    from datetime import timedelta

    from app.models import ahora

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("misd-expirada.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    expediente = session.get(Expediente, expediente_id)
    assert expediente is not None
    expediente.created_at = ahora() - timedelta(minutes=31)
    session.commit()
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": expediente_id, "motivo": "Documento ajeno a la operación"},
    )
    assert creada.status_code == 201, creada.text
    solicitud_id = creada.json()["id"]
    bloqueada = client.post(f"/api/v1/misd/solicitudes/{solicitud_id}/ejecutar")
    assert bloqueada.status_code == 409, bloqueada.text
    assert client.delete(f"/api/v1/expedientes/{expediente_id}").status_code == 409
    assert client.delete(f"/api/v1/documentos/{subida.json()['id']}").status_code == 409
    lote = client.post(
        "/api/v1/documentos/retirar-lote",
        json={"documentos_ids": [subida.json()["id"]]},
    )
    assert lote.status_code == 200, lote.text
    assert lote.json()["retirados"] == 0
    assert lote.json()["resultados"][0]["codigo"] == "409"
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 200


def test_misd_envia_notificaciones_chat_al_aprobar(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    from dataclasses import replace

    from app.models import CuentaAcceso, Miembro

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("misd-avisos.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": subida.json()["expediente_id"], "motivo": "Verificación documental"},
    )
    assert creada.status_code == 201, creada.text
    solicitante = auth_prueba.contexto.cuenta_id
    administrador = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="ADMIN-AVISOS",
        nombre="Administrador Avisos",
        rol="ADMINISTRADOR",
        activo=True,
    )
    session.add(administrador)
    session.flush()
    cuenta = CuentaAcceso(
        tenant_id=auth_prueba.contexto.tenant_id,
        login="admin-avisos",
        password_hash="hash-pruebas",
        miembro_id=administrador.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta)
    session.commit()
    auth_prueba.contexto = replace(
        auth_prueba.contexto,
        cuenta_id=cuenta.id,
        miembro_id=administrador.id,
        rol="ADMINISTRADOR",
        usuario_id=None,
        gestor_id=None,
    )
    resuelta = client.post(
        f"/api/v1/misd/solicitudes/{creada.json()['id']}/resolver",
        json={"aprobar": True, "motivo": "Autorizado para revisión final"},
    )
    assert resuelta.status_code == 200, resuelta.text
    assert (
        session.query(ChatMensaje)
        .filter(
            ChatMensaje.tenant_id == auth_prueba.contexto.tenant_id,
            ChatMensaje.destinatario_cuenta_id == solicitante,
        )
        .count()
        >= 1
    )


def test_misd_cambio_de_rol_invalida_solicitud_original(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    from dataclasses import replace

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("misd-rol-inmutable.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={
            "expediente_id": subida.json()["expediente_id"],
            "motivo": "Verificación de autoría",
        },
    )
    assert creada.status_code == 201, creada.text
    auth_prueba.contexto = replace(auth_prueba.contexto, rol="ADMINISTRADOR")
    respuesta = client.post(f"/api/v1/misd/solicitudes/{creada.json()['id']}/ejecutar")
    assert respuesta.status_code == 404
    assert client.get(f"/api/v1/expedientes/{subida.json()['expediente_id']}").status_code == 200


def test_aprobacion_revocada_no_es_valida_para_ejecutar(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    from app.api.routes.solicitudes_retiro_misd import _aprobacion_sigue_vigente
    from app.models import CuentaAcceso, Miembro

    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("misd-revocacion.xml", factura())},
    )
    assert subida.status_code == 201, subida.text
    expediente = session.get(Expediente, subida.json()["expediente_id"])
    assert expediente is not None
    creada = client.post(
        "/api/v1/misd/solicitudes",
        json={"expediente_id": str(expediente.id), "motivo": "Retiro bajo aprobación"},
    )
    assert creada.status_code == 201, creada.text
    solicitud = session.get(SolicitudRetiroMISD, creada.json()["id"])
    assert solicitud is not None

    miembro = Miembro(
        tenant_id=expediente.tenant_id,
        codigo="APROBADOR-REV",
        nombre="Aprobador Revocado",
        rol="ADMINISTRADOR",
        activo=True,
    )
    session.add(miembro)
    session.flush()
    cuenta = CuentaAcceso(
        tenant_id=expediente.tenant_id,
        miembro_id=miembro.id,
        login="aprobador-rev",
        password_hash="hash-pruebas",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta)
    session.flush()
    solicitud.aprobado_por_cuenta_id = cuenta.id
    solicitud.estado = "APROBADA"
    session.flush()
    assert _aprobacion_sigue_vigente(solicitud, expediente, session)
    cuenta.activo = False
    session.flush()
    assert not _aprobacion_sigue_vigente(solicitud, expediente, session)
    # Liberar los bloqueos de la sesión del test antes de abrir otra sesión HTTP.
    session.commit()

    ejecutada = client.post(f"/api/v1/misd/solicitudes/{solicitud.id}/ejecutar")
    assert ejecutada.status_code == 409, ejecutada.text
    assert client.get(f"/api/v1/expedientes/{expediente.id}").status_code == 200
