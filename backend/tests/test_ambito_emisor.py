"""Pruebas de aislamiento y atribución provisional del emisor."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    AsignacionEmpresaGestor,
    AsignacionPedidoGerencia,
    Empresa,
    Gestor,
    Miembro,
    PedidoGerencia,
    Tenant,
)
from app.services.ambito_emisor import EstadoAmbitoEmisor, revisar_asignaciones_emisor


def test_emisor_sin_asignacion_no_se_autoriza_automaticamente(session: Session, auth_prueba):
    tenant_id = auth_prueba.contexto.tenant_id
    empresa = Empresa(
        tenant_id=tenant_id,
        ruc="20111111111",
        razon_social="Emisor de prueba",
        tipo_relacion="PROVEEDOR",
    )
    session.add(empresa)
    session.commit()

    resultado = revisar_asignaciones_emisor(
        session,
        tenant_id,
        empresa.ruc,
        None,
        None,
    )
    assert resultado.estado == EstadoAmbitoEmisor.SIN_ASIGNACION


def test_emisor_asignado_a_otro_gestor_se_identifica_sin_mutaciones(
    session: Session,
    auth_prueba,
):
    tenant_id = auth_prueba.contexto.tenant_id
    empresa = Empresa(
        tenant_id=tenant_id,
        ruc="20222222222",
        razon_social="Proveedor protegido",
        tipo_relacion="PROVEEDOR",
    )
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-EMISOR-TEST",
        nombre="Responsable protegido",
        rol="RESPONSABLE",
        activo=True,
    )
    usuario = Miembro(
        tenant_id=tenant_id,
        codigo="USR-EMISOR-TEST",
        nombre="Usuario protegido",
        rol="USUARIO",
        activo=True,
    )
    session.add_all([empresa, responsable, usuario])
    session.flush()
    gestor = Gestor(
        tenant_id=tenant_id,
        codigo="GEST-EMISOR-TEST",
        nombre="Gestor protegido",
        usuario_id=usuario.id,
    )
    pedido = PedidoGerencia(
        tenant_id=tenant_id,
        cliente_id=empresa.id,
        responsable_id=responsable.id,
        periodo_mes=date(2026, 10, 1),
        moneda="PEN",
        monto_solicitado=Decimal("100"),
        estado="ACTIVO",
    )
    session.add_all([gestor, pedido])
    session.flush()
    session.add(
        AsignacionPedidoGerencia(
            tenant_id=tenant_id,
            pedido_id=pedido.id,
            usuario_id=usuario.id,
            gestor_id=gestor.id,
            proveedor_id=empresa.id,
            monto_asignado=Decimal("100"),
        )
    )
    session.commit()

    ajeno = revisar_asignaciones_emisor(
        session,
        tenant_id,
        empresa.ruc,
        None,
        None,
    )
    assert ajeno.estado == EstadoAmbitoEmisor.ASIGNADO_A_OTRO_GRUPO
    assert ajeno.gestor_propietario_id == gestor.id
    assert ajeno.responsable_propietario_id == responsable.id

    propio = revisar_asignaciones_emisor(
        session,
        tenant_id,
        empresa.ruc,
        usuario.id,
        gestor.id,
    )
    assert propio.estado == EstadoAmbitoEmisor.ASIGNADO_AL_GRUPO

    externo = Tenant(nombre="TENANT EXTERNO EMISOR", codigo="EXTERNO-EMISOR")
    session.add(externo)
    session.commit()
    aislado = revisar_asignaciones_emisor(
        session,
        externo.id,
        empresa.ruc,
        usuario.id,
        gestor.id,
    )
    assert aislado.estado == EstadoAmbitoEmisor.SIN_ASIGNACION


def test_api_bloquea_xml_de_otro_gestor_sin_documentos_ni_expedientes(
    client,
    session: Session,
    auth_prueba,
    settings,
):
    from sqlalchemy import func, select

    from app.models import Documento, Expediente, SolicitudCargaEmisor
    from tests.xml import factura

    tenant_id = auth_prueba.contexto.tenant_id
    empresa = Empresa(
        tenant_id=tenant_id,
        ruc="20444444444",
        razon_social="Emisor de otro grupo",
        tipo_relacion="PROVEEDOR",
    )
    propietario = Miembro(
        tenant_id=tenant_id,
        codigo="USR-OTRO-GRUPO",
        nombre="Usuario dueño",
        rol="USUARIO",
        activo=True,
    )
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-OTRO-GRUPO",
        nombre="Responsable dueño",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add_all([empresa, propietario, responsable])
    session.flush()
    gestor = Gestor(
        tenant_id=tenant_id,
        codigo="GEST-OTRO-GRUPO",
        nombre="Gestor dueño",
        usuario_id=propietario.id,
    )
    pedido = PedidoGerencia(
        tenant_id=tenant_id,
        cliente_id=empresa.id,
        responsable_id=responsable.id,
        periodo_mes=date(2026, 10, 1),
        moneda="PEN",
        monto_solicitado=Decimal("100"),
        estado="ACTIVO",
    )
    session.add_all([gestor, pedido])
    session.flush()
    session.add(
        AsignacionPedidoGerencia(
            tenant_id=tenant_id,
            pedido_id=pedido.id,
            usuario_id=propietario.id,
            gestor_id=gestor.id,
            proveedor_id=empresa.id,
            monto_asignado=Decimal("100"),
        )
    )
    session.commit()

    anterior_documentos = session.scalar(
        select(func.count()).select_from(Documento).where(Documento.tenant_id == tenant_id)
    )
    anterior_expedientes = session.scalar(
        select(func.count()).select_from(Expediente).where(Expediente.tenant_id == tenant_id)
    )

    respuesta = client.post(
        "/api/v1/documentos",
        files={
            "archivo": (
                "factura_ajena.xml",
                factura(
                    numero="F001-00000851",
                    emisor=empresa.ruc,
                ),
                "application/xml",
            )
        },
    )
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["detail"]["codigo"] == "EMISOR_REQUIERE_AUTORIZACION"

    session.expire_all()
    assert (
        session.scalar(
            select(func.count()).select_from(Documento).where(Documento.tenant_id == tenant_id)
        )
        == anterior_documentos
    )
    assert (
        session.scalar(
            select(func.count()).select_from(Expediente).where(Expediente.tenant_id == tenant_id)
        )
        == anterior_expedientes
    )
    solicitud = session.scalar(
        select(SolicitudCargaEmisor).where(
            SolicitudCargaEmisor.tenant_id == tenant_id,
            SolicitudCargaEmisor.ruc_emisor == empresa.ruc,
        )
    )
    assert solicitud is not None
    assert solicitud.estado == "PENDIENTE"
    assert respuesta.json()["detail"]["solicitud_id"] == str(solicitud.id)
    assert solicitud.ruta_temporal is not None
    ruta_temporal = settings.storage_dir / solicitud.ruta_temporal
    assert ruta_temporal.is_file()

    auth_prueba.como_admin()
    rechazo = client.post(
        f"/api/v1/solicitudes-carga-emisor/{solicitud.id}/rechazar",
        json={"observacion": "No autorizado"},
    )
    assert rechazo.status_code == 200, rechazo.text
    assert rechazo.json()["estado"] == "RECHAZADA"
    assert not ruta_temporal.exists()

def test_admin_asigna_empresa_y_bloquea_ajenos(
    client,
    session: Session,
    auth_prueba,
):
    tenant_id = auth_prueba.contexto.tenant_id
    emisor = Empresa(
        tenant_id=tenant_id,
        ruc="20555555555",
        razon_social="Emisor formal",
        tipo_relacion="PROVEEDOR",
    )
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-FORMAL",
        nombre="Responsable formal",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add_all([emisor, responsable])
    session.flush()
    usuario = Miembro(
        tenant_id=tenant_id,
        codigo="USUARIO-FORMAL",
        nombre="Usuario formal",
        rol="USUARIO",
        activo=True,
        responsable_id=responsable.id,
    )
    session.add(usuario)
    session.flush()
    gestor = Gestor(
        tenant_id=tenant_id,
        codigo="GESTOR-FORMAL",
        nombre="Gestor formal",
        usuario_id=usuario.id,
    )
    session.add(gestor)
    session.commit()
    payload = {
        "empresa_id": str(emisor.id),
        "gestor_id": str(gestor.id),
        "responsable_id": str(responsable.id),
    }
    auth_prueba.como_usuario(usuario.id)
    denegado = client.put(f"/api/v1/asignaciones-emisores/{emisor.id}", json=payload)
    assert denegado.status_code == 403

    auth_prueba.como_admin()
    creado = client.put(f"/api/v1/asignaciones-emisores/{emisor.id}", json=payload)
    assert creado.status_code == 200, creado.text
    assert creado.json()["gestor_id"] == str(gestor.id)
    asignacion = session.query(AsignacionEmpresaGestor).filter_by(empresa_id=emisor.id).one()
    assert asignacion.tenant_id == tenant_id

    ajeno = revisar_asignaciones_emisor(session, tenant_id, emisor.ruc, None, None)
    assert ajeno.estado == EstadoAmbitoEmisor.ASIGNADO_A_OTRO_GRUPO
    assert ajeno.responsable_propietario_id == responsable.id

    propio = revisar_asignaciones_emisor(session, tenant_id, emisor.ruc, usuario.id, gestor.id)
    assert propio.estado == EstadoAmbitoEmisor.ASIGNADO_AL_GRUPO
