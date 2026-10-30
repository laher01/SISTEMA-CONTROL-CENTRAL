"""Regresiones de comisiones por receptor y pago exclusivo a Responsable."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    ChatMensaje,
    CuentaAcceso,
    Empresa,
    Expediente,
    GerenteEmpresa,
    GerenteResponsable,
    Miembro,
    PedidoGerencia,
)
from tests.conftest import AuthPrueba, completar_facturas_de_prueba


def _preparar(session: Session, auth_prueba: AuthPrueba) -> tuple[str, str]:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-01",
        nombre="Responsable prueba",
        rol="RESPONSABLE",
        activo=True,
    )
    usuario = Miembro(
        tenant_id=tenant_id,
        codigo="USU-01",
        nombre="Usuario prueba",
        rol="USUARIO",
        activo=True,
    )
    cliente = Empresa(
        tenant_id=tenant_id,
        ruc="20538821374",
        razon_social="CLIENTE PRUEBA",
        autorizada=True,
        tipo_relacion="CLIENTE",
        agente_retencion=False,
    )
    session.add_all([responsable, usuario, cliente])
    session.flush()
    usuario.responsable_id = responsable.id
    factura = Expediente(
        tenant_id=tenant_id,
        emisor_id=cliente.id,
        receptor_id=cliente.id,
        tipo_comprobante="FACT",
        serie="F001",
        correlativo="00001",
        fecha_emision=date(2026, 9, 15),
        moneda="PEN",
        importe_total=Decimal("1000.00"),
        usuario_id=usuario.id,
        gerente_id=auth_prueba.contexto.miembro_id,
    )
    session.add(factura)
    completar_facturas_de_prueba(session)
    session.commit()
    return str(responsable.id), str(cliente.id)


def test_comisiones_gerencia_por_cliente_y_autorizacion(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
) -> None:
    responsable_id, cliente_id = _preparar(session, auth_prueba)
    auth_prueba.como_gerente()
    url = "/api/v1/pagos-responsables"
    params = {"desde": "2026-09-01", "hasta": "2026-09-30", "moneda": "PEN"}
    resumen = client.get(url + "/resumen", params=params)
    assert resumen.status_code == 200, resumen.text
    datos = resumen.json()
    assert datos["total_produccion"] == "1000.00"
    assert datos["total_comisiones"] == "35.00"
    assert datos["filas"][0]["cliente_id"] == cliente_id
    assert datos["filas"][0]["exceso"] == "1000.00"

    cambio = client.put(
        url + "/comision",
        json={
            "responsable_id": responsable_id,
            "cliente_id": cliente_id,
            "porcentaje": "4.0",
            "motivo": "Condición especial de Gerencia",
        },
    )
    assert cambio.status_code == 403  # El Gerente no altera una regla financiera global.
    modificado = client.get(url + "/resumen", params=params).json()
    assert modificado["total_comisiones"] == "35.00"

    historial = client.get(f"{url}/comision/{responsable_id}/{cliente_id}/historial")
    assert historial.status_code == 403

    programado = client.post(
        url + "/programar",
        json={
            "responsable_id": responsable_id,
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": "PEN",
        },
    )
    assert programado.status_code == 201, programado.text
    pago_id = programado.json()["id"]

    repetido = client.post(
        url + "/programar",
        json={
            "responsable_id": responsable_id,
            "desde": "2026-09-15",
            "hasta": "2026-10-15",
            "moneda": "PEN",
        },
    )
    assert repetido.status_code == 409

    confirmar = client.post(
        f"{url}/{pago_id}/confirmar",
        json={"fecha_pago": "2026-10-09", "referencia_pago": "BANCO-01234"},
    )
    assert confirmar.status_code == 200, confirmar.text
    assert confirmar.json()["estado"] == "PAGADO"

    auth_prueba.como_admin()
    prohibido = client.post(
        f"{url}/{pago_id}/confirmar",
        json={"fecha_pago": "2026-10-09", "referencia_pago": "BANCO-99999"},
    )
    assert prohibido.status_code == 403


def test_resumen_responsable_por_gerente_y_solicitud_de_cobro(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-COBROS",
        nombre="Responsable cobros",
        rol="RESPONSABLE",
        activo=True,
    )
    gerente = Miembro(
        tenant_id=tenant_id,
        codigo="GER-COBROS",
        nombre="Gerente cobros",
        rol="GERENTE",
        activo=True,
    )
    usuario = Miembro(
        tenant_id=tenant_id,
        codigo="USR-COBROS",
        nombre="Usuario cobros",
        rol="USUARIO",
        responsable_id=responsable.id,
        porcentaje_con_agente=Decimal("2.0"),
        porcentaje_sin_agente=Decimal("1.5"),
        activo=True,
    )
    cliente_agente = Empresa(
        tenant_id=tenant_id,
        ruc="20111111111",
        razon_social="CLIENTE AGENTE",
        autorizada=True,
        tipo_relacion="CLIENTE",
        agente_retencion=True,
    )
    cliente_sin_agente = Empresa(
        tenant_id=tenant_id,
        ruc="20222222222",
        razon_social="CLIENTE NORMAL",
        autorizada=True,
        tipo_relacion="CLIENTE",
        agente_retencion=False,
    )
    cliente_no_autorizado = Empresa(
        tenant_id=tenant_id,
        ruc="20444444444",
        razon_social="CLIENTE PENDIENTE DE AUTORIZAR",
        autorizada=False,
        tipo_relacion="CLIENTE",
        agente_retencion=False,
    )
    cliente_pedido = Empresa(
        tenant_id=tenant_id,
        ruc="20555555555",
        razon_social="CLIENTE CON PEDIDO POSTERIOR",
        autorizada=True,
        tipo_relacion="CLIENTE",
        agente_retencion=False,
    )
    proveedor = Empresa(
        tenant_id=tenant_id,
        ruc="20333333333",
        razon_social="PROVEEDOR",
        autorizada=True,
        tipo_relacion="PROVEEDOR",
        agente_retencion=False,
    )
    session.add_all(
        [
            responsable,
            gerente,
            usuario,
            cliente_agente,
            cliente_sin_agente,
            cliente_no_autorizado,
            cliente_pedido,
            proveedor,
        ]
    )
    session.flush()
    usuario.responsable_id = responsable.id
    session.add(
        GerenteResponsable(
            tenant_id=tenant_id,
            gerente_id=gerente.id,
            responsable_id=responsable.id,
            activo=True,
        )
    )
    for serie, correlativo, receptor, monto in (
        ("F001", "00001", cliente_agente, Decimal("1000.00")),
        ("F002", "00002", cliente_sin_agente, Decimal("2000.00")),
    ):
        session.add(
            Expediente(
                tenant_id=tenant_id,
                emisor_id=proveedor.id,
                receptor_id=receptor.id,
                tipo_comprobante="FACT",
                serie=serie,
                correlativo=correlativo,
                fecha_emision=date(2026, 9, 15),
                moneda="PEN",
                importe_total=monto,
                usuario_id=usuario.id,
                gerente_id=gerente.id,
            )
        )
    # Un documento activo sin pedido inequívoco debe quedar visible para revisión,
    # pero jamás mezclarse en el cobro atribuido al Gerente.
    session.add(
        Expediente(
            tenant_id=tenant_id,
            emisor_id=proveedor.id,
            receptor_id=cliente_sin_agente.id,
            tipo_comprobante="FACT",
            serie="F003",
            correlativo="00003",
            fecha_emision=date(2026, 9, 15),
            moneda="PEN",
            importe_total=Decimal("500.00"),
            usuario_id=usuario.id,
        )
    )
    # Documento cargado antes de que se cree su pedido mensual.
    session.add(
        Expediente(
            tenant_id=tenant_id,
            emisor_id=proveedor.id,
            receptor_id=cliente_pedido.id,
            tipo_comprobante="FACT",
            serie="F005",
            correlativo="00005",
            fecha_emision=date(2026, 9, 15),
            moneda="PEN",
            importe_total=Decimal("700.00"),
            usuario_id=usuario.id,
        )
    )
    session.add_all(
        [
            GerenteEmpresa(
                tenant_id=tenant_id,
                gerente_id=gerente.id,
                empresa_id=cliente_pedido.id,
                activo=True,
            ),
            PedidoGerencia(
                tenant_id=tenant_id,
                gerente_id=gerente.id,
                responsable_id=responsable.id,
                cliente_id=cliente_pedido.id,
                periodo_mes=date(2026, 9, 1),
                moneda="PEN",
                monto_solicitado=Decimal("1000.00"),
                modalidad="POR_PEDIDO",
                modo_distribucion="MANUAL",
                estado="ACTIVO",
            ),
        ]
    )
    # La producción de un receptor pendiente de autorización también debe
    # aparecer como excluida, sin formar parte de la comisión.
    session.add(
        Expediente(
            tenant_id=tenant_id,
            emisor_id=proveedor.id,
            receptor_id=cliente_no_autorizado.id,
            tipo_comprobante="FACT",
            serie="F004",
            correlativo="00004",
            fecha_emision=date(2026, 9, 15),
            moneda="PEN",
            importe_total=Decimal("250.00"),
            usuario_id=usuario.id,
            gerente_id=gerente.id,
        )
    )
    cuenta_responsable = CuentaAcceso(
        tenant_id=tenant_id,
        login="RESP-COBROS",
        password_hash="hash-pruebas",
        miembro_id=responsable.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    cuenta_gerente = CuentaAcceso(
        tenant_id=tenant_id,
        login="GER-COBROS",
        password_hash="hash-pruebas",
        miembro_id=gerente.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add_all([cuenta_responsable, cuenta_gerente])
    completar_facturas_de_prueba(session)
    session.commit()
    auth_prueba.contexto = replace(
        auth_prueba.contexto,
        cuenta_id=cuenta_responsable.id,
        miembro_id=responsable.id,
        rol="RESPONSABLE",
        usuario_id=None,
        gestor_id=None,
    )

    sincronizacion = client.post(
        "/api/v1/pagos-responsables/equipo-sincronizar",
        json={"desde": "2026-09-01", "hasta": "2026-09-30", "moneda": "PEN"},
    )
    assert sincronizacion.status_code == 200, sincronizacion.text
    assert sincronizacion.json() == {"vinculados": 1, "produccion": "700.00"}

    params = {
        "desde": "2026-09-01",
        "hasta": "2026-09-30",
        "moneda": "PEN",
        "gerente_ids": str(gerente.id),
    }
    resumen = client.get("/api/v1/pagos-responsables/equipo-resumen", params=params)
    assert resumen.status_code == 200, resumen.text
    datos = resumen.json()
    assert datos["gerentes"] == [
        {
            "gerente_id": str(gerente.id),
            "gerente_codigo": "GER-COBROS",
            "gerente_nombre": "Gerente cobros",
            "produccion": "3700.00",
            "comision": "124.50",
        }
    ]
    assert len(datos["clientes"]) == 3
    assert {fila["porcentaje"] for fila in datos["clientes"]} == {"3.0", "3.5"}
    assert len(datos["proveedores"]) == 1
    assert datos["proveedores"][0]["produccion"] == "3700.00"
    assert len(datos["usuarios"]) == 1
    assert datos["usuarios"][0]["produccion"] == "3700.00"
    assert datos["usuarios"][0]["comision_referencial_usuario"] == "60.50"
    assert datos["pendientes_revision"]["cantidad"] == 2
    assert datos["pendientes_revision"]["produccion"] == "750.00"
    assert {fila["motivo"] for fila in datos["pendientes_revision"]["expedientes"]} == {
        "GERENCIA_SIN_VINCULO",
        "RECEPTOR_NO_AUTORIZADO",
    }

    solicitud = client.post(
        "/api/v1/pagos-responsables/solicitudes-cobro",
        json={
            "gerente_id": str(gerente.id),
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": "PEN",
        },
    )
    assert solicitud.status_code == 201, solicitud.text
    assert solicitud.json()["comision"] == "124.50"
    assert (
        session.query(ChatMensaje).filter_by(destinatario_cuenta_id=cuenta_gerente.id).count() == 1
    )
    auth_prueba.contexto = replace(
        auth_prueba.contexto,
        cuenta_id=cuenta_gerente.id,
        miembro_id=gerente.id,
        rol="GERENTE",
        usuario_id=None,
        gestor_id=None,
    )
    recibidas = client.get("/api/v1/pagos-responsables/solicitudes-cobro")
    assert recibidas.status_code == 200, recibidas.text
    assert recibidas.json()[0]["id"] == solicitud.json()["id"]
