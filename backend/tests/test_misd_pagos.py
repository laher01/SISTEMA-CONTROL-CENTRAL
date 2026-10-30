"""Regresión MISD: los pagos generados congelan su producción de origen."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.models import (
    Documento,
    Expediente,
    Gestor,
    Miembro,
    PagoERP,
    PagoGestor,
    PagoResponsableERP,
    PermisoConfigurado,
)
from tests.conftest import AuthPrueba
from tests.xml import factura


@pytest.fixture(autouse=True)
def habilitar_retiro_usuario(session: Session, auth_prueba: AuthPrueba) -> None:
    session.add(
        PermisoConfigurado(
            tenant_id=auth_prueba.contexto.tenant_id,
            rol="USUARIO",
            permiso="ELIMINAR_REGISTROS",
            habilitado=True,
        )
    )
    session.commit()


def test_pago_generado_no_bloquea_eliminacion_operativa_para_admin(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("congelada.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = respuesta.json()
    expediente = session.get(Expediente, UUID(documento["expediente_id"]))
    assert expediente is not None
    assert expediente.usuario_id is not None
    pago = PagoERP(
        tenant_id=expediente.tenant_id,
        usuario_id=expediente.usuario_id,
        periodo_desde=date(2026, 1, 1),
        periodo_hasta=date(2026, 12, 31),
        moneda=expediente.moneda,
        produccion_total=Decimal("100.00"),
        porcentaje=Decimal("10"),
        bruto=Decimal("10.00"),
        saldo=Decimal("10.00"),
        estado="PROGRAMADO",
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()

    expedientes = client.get("/api/v1/expedientes")
    assert expedientes.status_code == 200, expedientes.text
    vista = next(f for f in expedientes.json() if f["id"] == str(expediente.id))
    assert vista["puede_eliminar"] is True

    registros = client.get("/api/v1/registros")
    assert registros.status_code == 200, registros.text
    fila = next(f for f in registros.json()["filas"] if f["expediente_id"] == str(expediente.id))
    assert fila["puede_eliminar"] is True

    ruta_documento = f"/api/v1/documentos/{documento['id']}"
    ruta_expediente = f"/api/v1/expedientes/{expediente.id}"
    previsualizacion = client.post(
        "/api/v1/documentos/previsualizar-retirada",
        json={"documentos_ids": [documento["id"]]},
    )
    assert previsualizacion.status_code == 200, previsualizacion.text
    assert previsualizacion.json()["aptos"] == 1
    assert previsualizacion.json()["resultados"][0]["estado"] == "APTO_ELIMINACION"
    assert client.delete(ruta_documento).status_code == 200
    assert client.get(ruta_documento).status_code == 404
    assert client.delete(ruta_expediente).status_code == 200
    assert client.get(ruta_expediente).status_code == 404
    assert session.get(PagoERP, pago.id) is not None


def test_voucher_vinculado_a_pago_se_desacopla_al_retirarlo(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("voucher.pdf", b"%PDF-1.7 voucher generado")},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = respuesta.json()
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    pago = PagoERP(
        tenant_id=auth_prueba.contexto.tenant_id,
        usuario_id=usuario_id,
        periodo_desde=date(2026, 9, 1),
        periodo_hasta=date(2026, 9, 30),
        moneda="PEN",
        produccion_total=Decimal("100.00"),
        porcentaje=Decimal("10"),
        bruto=Decimal("10.00"),
        saldo=Decimal("10.00"),
        estado="PROGRAMADO",
        voucher_documento_id=UUID(documento["id"]),
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()
    eliminado = client.delete(f"/api/v1/documentos/{documento['id']}")
    assert eliminado.status_code == 200, eliminado.text
    session.expire_all()
    assert session.get(PagoERP, pago.id).voucher_documento_id is None
    assert client.get(f"/api/v1/documentos/{documento['id']}").status_code == 404


def test_pago_gestor_generado_no_bloquea_eliminacion_del_admin(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura-gestor.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    expediente = session.get(Expediente, UUID(respuesta.json()["expediente_id"]))
    assert expediente is not None
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    gestor = Gestor(
        tenant_id=expediente.tenant_id,
        codigo="GEST-MISD",
        nombre="Gestor MISD",
        usuario_id=usuario_id,
    )
    session.add(gestor)
    session.flush()
    expediente.gestor_id = gestor.id
    pago = PagoGestor(
        tenant_id=expediente.tenant_id,
        gestor_id=gestor.id,
        usuario_id=usuario_id,
        periodo_desde=date(2026, 1, 1),
        periodo_hasta=date(2026, 12, 31),
        moneda=expediente.moneda,
        produccion_total=Decimal("100.00"),
        porcentaje=Decimal("10"),
        bruto=Decimal("10.00"),
        saldo=Decimal("10.00"),
        estado="PROGRAMADO",
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()
    resultado = client.delete(f"/api/v1/expedientes/{expediente.id}")
    assert resultado.status_code == 200, resultado.text
    assert client.get(f"/api/v1/expedientes/{expediente.id}").status_code == 404


def test_pago_responsable_generado_no_bloquea_eliminacion_del_admin(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura-responsable.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    expediente = session.get(Expediente, UUID(respuesta.json()["expediente_id"]))
    assert expediente is not None
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    responsable = Miembro(
        tenant_id=expediente.tenant_id,
        codigo="RESP-MISD",
        nombre="Responsable MISD",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    usuario = session.get(Miembro, usuario_id)
    assert usuario is not None
    usuario.responsable_id = responsable.id
    pago = PagoResponsableERP(
        tenant_id=expediente.tenant_id,
        gerente_id=None,
        responsable_id=responsable.id,
        periodo_desde=date(2026, 1, 1),
        periodo_hasta=date(2026, 12, 31),
        moneda=expediente.moneda,
        produccion_total=Decimal("100.00"),
        comision_total=Decimal("10.00"),
        detalle={},
        estado="PROGRAMADO",
        creado_por_cuenta_id=auth_prueba.contexto.cuenta_id,
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()
    resultado = client.delete(f"/api/v1/expedientes/{expediente.id}")
    assert resultado.status_code == 200, resultado.text
    assert client.get(f"/api/v1/expedientes/{expediente.id}").status_code == 404


def test_voucher_de_otro_periodo_no_bloquea_eliminacion_del_expediente(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    factura_subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("expediente-voucher.xml", factura())},
    )
    assert factura_subida.status_code == 201, factura_subida.text
    expediente_id = factura_subida.json()["expediente_id"]
    voucher_subido = client.post(
        "/api/v1/documentos",
        files={"archivo": ("voucher-misd.pdf", b"%PDF-1.7 voucher")},
    )
    assert voucher_subido.status_code == 201, voucher_subido.text
    voucher = session.get(Documento, UUID(voucher_subido.json()["id"]))
    assert voucher is not None
    voucher.expediente_id = UUID(expediente_id)
    # Evitar retener bloqueos de escritura al abrir la sesión HTTP de MISD.
    session.commit()
    pago = PagoERP(
        tenant_id=auth_prueba.contexto.tenant_id,
        usuario_id=auth_prueba.contexto.usuario_id,
        periodo_desde=date(2025, 1, 1),
        periodo_hasta=date(2025, 12, 31),
        moneda="PEN",
        produccion_total=Decimal("100"),
        porcentaje=Decimal("10"),
        bruto=Decimal("10"),
        saldo=Decimal("10"),
        estado="PROGRAMADO",
        voucher_documento_id=voucher.id,
    )
    session.add(pago)
    session.commit()
    auth_prueba.como_admin()
    assert client.delete(f"/api/v1/expedientes/{expediente_id}").status_code == 200
    session.expire_all()
    assert session.get(PagoERP, pago.id).voucher_documento_id is None
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 404


@pytest.mark.parametrize("primer_evento", ["pago", "retirada"])
def test_bloqueo_compartido_serialize_pago_y_retirada_postgresql(
    client: TestClient,
    engine: Engine,
    primer_evento: str,
) -> None:
    """Dos transacciones reales prueban el contrato en ambos órdenes."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from app.services.bloqueo_financiero_misd import bloquear_tenant_financiero
    from app.services.misd_pagos import motivo_bloqueo_liquidacion

    if engine.dialect.name != "postgresql":
        pytest.skip("La prueba requiere advisory locks transaccionales PostgreSQL")
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("contrato-carrera.xml", factura())},
    )
    assert respuesta.status_code == 201, respuesta.text
    expediente_id = respuesta.json()["expediente_id"]
    fabrica = sessionmaker(engine, expire_on_commit=False)
    listo = Event()
    intenta_bloquear = Event()
    liberar = Event()

    def primero() -> None:
        with fabrica() as sesion:
            exp = sesion.get(Expediente, UUID(expediente_id))
            assert exp is not None
            bloquear_tenant_financiero(sesion, exp.tenant_id)
            if primer_evento == "pago":
                sesion.add(
                    PagoERP(
                        tenant_id=exp.tenant_id,
                        usuario_id=exp.usuario_id,
                        periodo_desde=date(2026, 1, 1),
                        periodo_hasta=date(2026, 12, 31),
                        moneda=exp.moneda,
                        produccion_total=Decimal("100"),
                        porcentaje=Decimal("10"),
                        bruto=Decimal("10"),
                        saldo=Decimal("10"),
                        estado="PROGRAMADO",
                    )
                )
            else:
                exp.deleted_at = exp.created_at
            sesion.flush()
            listo.set()
            assert liberar.wait(timeout=30)
            sesion.commit()

    def segundo() -> str:
        assert listo.wait(timeout=30)
        with fabrica() as sesion:
            exp = sesion.get(Expediente, UUID(expediente_id))
            assert exp is not None
            intenta_bloquear.set()
            bloquear_tenant_financiero(sesion, exp.tenant_id)
            sesion.refresh(exp)
            if primer_evento == "pago":
                resultado = motivo_bloqueo_liquidacion(sesion, exp)
                assert resultado is not None
                return "RETIRO_BLOQUEADO"
            visibles = list(
                sesion.scalars(
                    select(Expediente.id).where(
                        Expediente.tenant_id == exp.tenant_id,
                        Expediente.id == exp.id,
                        Expediente.deleted_at.is_(None),
                    )
                )
            )
            assert not visibles
            return "PRODUCCION_RETIRADA"

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuro_primero = ejecutor.submit(primero)
        futuro_segundo = ejecutor.submit(segundo)
        assert listo.wait(timeout=30)
        assert intenta_bloquear.wait(timeout=30)
        liberar.set()
        resultado = futuro_segundo.result(timeout=45)
        futuro_primero.result(timeout=45)
    assert resultado == ("RETIRO_BLOQUEADO" if primer_evento == "pago" else "PRODUCCION_RETIRADA")
