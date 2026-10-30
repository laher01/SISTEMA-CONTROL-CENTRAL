from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Documento, Expediente, Miembro
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba
from tests.xml import factura


def _subir_factura(client: TestClient, numero: str = "F001-00000991") -> dict[str, object]:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": (numero + ".xml", factura(numero=numero, importe="123.45"))},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_eliminar_ultimo_documento_elimina_expediente_y_permite_reingreso(
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
) -> None:
    documento = _subir_factura(client)
    expediente_id = UUID(str(documento["expediente_id"]))
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 200

    auth_prueba.como_admin()
    eliminacion = client.delete(f"/api/v1/documentos/{documento['id']}")
    assert eliminacion.status_code == 200, eliminacion.text
    assert session.get(Expediente, expediente_id) is None
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 404
    assert client.get("/api/v1/expedientes").json() == []

    resumen = client.get("/api/v1/expedientes/resumen")
    assert resumen.status_code == 200, resumen.text
    assert resumen.json()["total_expedientes"] == 0
    assert Decimal(resumen.json()["total_pen"]) == Decimal("0")

    auth_prueba.como_usuario(auth_prueba.usuario_id)
    nuevo = _subir_factura(client)
    assert nuevo["expediente_id"] != str(expediente_id)


def test_reingreso_no_reutiliza_expediente_vacio_y_asigna_al_gestor_actual(
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
) -> None:
    numero = "F001-00000882"
    creado = client.post(
        "/api/v1/expedientes",
        json={
            "receptor": {"ruc": "20100000001", "razon_social": "CLIENTE SAC"},
            "emisor": {"ruc": "20500000002", "razon_social": "PROVEEDOR SAC"},
            "tipo_comprobante": "FACT",
            "serie": "F001",
            "correlativo": "00000882",
            "fecha_emision": "2026-09-10",
            "moneda": "PEN",
            "importe_total": "123.45",
            "requiere_guia": False,
        },
    )
    assert creado.status_code == 201, creado.text
    expediente_vacio_id = UUID(creado.json()["id"])

    documento = _subir_factura(client, numero)
    expediente_nuevo_id = UUID(str(documento["expediente_id"]))
    assert expediente_nuevo_id != expediente_vacio_id
    assert session.get(Expediente, expediente_vacio_id) is None

    expediente_nuevo = session.get(Expediente, expediente_nuevo_id)
    assert expediente_nuevo is not None
    assert expediente_nuevo.gestor_id == auth_prueba.gestor_id
    assert expediente_nuevo.usuario_id == auth_prueba.usuario_id


def test_previsualizacion_de_vacios_es_admin_y_solo_lectura(
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
) -> None:
    creado = client.post(
        "/api/v1/expedientes",
        json={
            "receptor": {"ruc": "20100000001", "razon_social": "CLIENTE SAC"},
            "emisor": {"ruc": "20500000002", "razon_social": "PROVEEDOR SAC"},
            "tipo_comprobante": "FACT",
            "serie": "F001",
            "correlativo": "00000883",
            "fecha_emision": "2026-09-10",
            "moneda": "PEN",
            "importe_total": "123.45",
            "requiere_guia": False,
        },
    )
    assert creado.status_code == 201, creado.text
    expediente_id = UUID(creado.json()["id"])

    no_autorizado = client.get("/api/v1/expedientes/previsualizar-vacios")
    assert no_autorizado.status_code == 403

    auth_prueba.como_admin()
    respuesta = client.get("/api/v1/expedientes/previsualizar-vacios")
    assert respuesta.status_code == 200, respuesta.text
    resultado = next(
        fila
        for fila in respuesta.json()["resultados"]
        if fila["expediente_id"] == str(expediente_id)
    )
    assert respuesta.json()["solo_lectura"] is True
    assert resultado["documentos_activos"] == 0
    assert resultado["documentos_historicos"] == 0
    assert resultado["apto_limpieza_atomica"] is True
    assert session.get(Expediente, expediente_id) is not None


def test_resumen_de_responsable_respeta_filtros_de_usuario_y_gestor(
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
) -> None:
    documento = _subir_factura(client, "F001-00000992")
    usuario = session.get(Miembro, auth_prueba.usuario_id)
    assert usuario is not None
    responsable = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="RESP-TEST",
        nombre="Responsable de pruebas",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    usuario.responsable_id = responsable.id
    session.commit()

    actual = auth_prueba.contexto
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=actual.cuenta_id,
        tenant_id=actual.tenant_id,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        gestor_id=None,
        usuario_id=None,
        codigo=responsable.codigo,
        nombre=responsable.nombre,
        cambio_clave_obligatorio=False,
    )
    params = {"usuario_id": str(usuario.id), "gestor_id": str(auth_prueba.gestor_id)}
    lista = client.get("/api/v1/expedientes", params=params)
    resumen = client.get("/api/v1/expedientes/resumen", params=params)

    assert lista.status_code == 200, lista.text
    assert resumen.status_code == 200, resumen.text
    assert len(lista.json()) == resumen.json()["total_expedientes"] == 1
    assert lista.json()[0]["id"] == documento["expediente_id"]
    assert Decimal(resumen.json()["total_pen"]) == Decimal("123.45")


def test_exp_vacio_no_aparece_ni_suma_en_responsable_o_administrador(
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
) -> None:
    documento = _subir_factura(client, "F001-00000993")
    creado = client.post(
        "/api/v1/expedientes",
        json={
            "receptor": {"ruc": "20100000001", "razon_social": "CLIENTE SAC"},
            "emisor": {"ruc": "20500000002", "razon_social": "PROVEEDOR SAC"},
            "tipo_comprobante": "FACT",
            "serie": "F001",
            "correlativo": "00000994",
            "fecha_emision": "2026-09-10",
            "moneda": "PEN",
            "importe_total": "999.00",
            "requiere_guia": False,
        },
    )
    assert creado.status_code == 201, creado.text
    expediente_vacio_id = creado.json()["id"]

    usuario = session.get(Miembro, auth_prueba.usuario_id)
    assert usuario is not None
    responsable = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="RESP-GHOST-TEST",
        nombre="Responsable de prueba",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    usuario.responsable_id = responsable.id
    session.commit()

    contexto_usuario = auth_prueba.contexto
    auth_responsable = ContextoAcceso(
        cuenta_id=contexto_usuario.cuenta_id,
        tenant_id=contexto_usuario.tenant_id,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        gestor_id=None,
        usuario_id=None,
        codigo=responsable.codigo,
        nombre=responsable.nombre,
        cambio_clave_obligatorio=False,
    )

    for rol in ("RESPONSABLE", "ADMINISTRADOR"):
        auth_prueba.contexto = auth_responsable if rol == "RESPONSABLE" else contexto_usuario
        if rol == "ADMINISTRADOR":
            auth_prueba.como_admin()

        lista = client.get("/api/v1/expedientes")
        resumen = client.get("/api/v1/expedientes/resumen")
        dashboard = client.get("/api/v1/dashboard/resumen")
        desglose = client.get("/api/v1/dashboard/desglose", params={"agrupar_por": "usuario"})
        alertas = client.get("/api/v1/alertas")

        assert lista.status_code == resumen.status_code == 200
        assert dashboard.status_code == desglose.status_code == 200
        assert alertas.status_code == 200
        assert [fila["id"] for fila in lista.json()] == [documento["expediente_id"]]
        assert resumen.json()["total_expedientes"] == 1
        assert Decimal(resumen.json()["total_pen"]) == Decimal("123.45")
        assert dashboard.json()["expedientes_total"] == 1
        assert Decimal(
            str(
                next(item for item in dashboard.json()["montos"] if item["moneda"] == "PEN")[
                    "no_bancarizable"
                ]
            )
        ) == Decimal("123.45")
        assert len(desglose.json()["filas"]) == 1
        assert Decimal(str(desglose.json()["filas"][0]["total_pen"])) == Decimal("123.45")
        assert expediente_vacio_id not in {fila["id"] for fila in lista.json()}
        assert expediente_vacio_id not in {fila["expediente_id"] for fila in alertas.json()}


def test_limpieza_de_previsualizacion_purga_solo_expedientes_aun_vacios(
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
) -> None:
    creado = client.post(
        "/api/v1/expedientes",
        json={
            "receptor": {"ruc": "20100000001", "razon_social": "CLIENTE SAC"},
            "emisor": {"ruc": "20500000002", "razon_social": "PROVEEDOR SAC"},
            "tipo_comprobante": "FACT",
            "serie": "F001",
            "correlativo": "00000995",
            "fecha_emision": "2026-09-10",
            "moneda": "PEN",
            "importe_total": "999.00",
            "requiere_guia": False,
        },
    )
    assert creado.status_code == 201, creado.text
    vacio_id = creado.json()["id"]
    historico = _subir_factura(client, "F001-00000997")
    documento_historico = session.get(Documento, UUID(str(historico["id"])))
    assert documento_historico is not None
    documento_historico_id = documento_historico.id
    documento_historico.deleted_at = datetime.now(UTC)
    session.commit()
    activo = _subir_factura(client, "F001-00000996")

    auth_prueba.como_admin()
    preview = client.get("/api/v1/expedientes/previsualizar-vacios")
    assert preview.status_code == 200, preview.text
    candidato = next(
        fila for fila in preview.json()["resultados"] if fila["expediente_id"] == vacio_id
    )
    assert candidato["apto_limpieza_atomica"] is True
    candidato_historico = next(
        fila
        for fila in preview.json()["resultados"]
        if fila["expediente_id"] == historico["expediente_id"]
    )
    assert candidato_historico["documentos_activos"] == 0
    assert candidato_historico["documentos_historicos"] == 1
    assert candidato_historico["requiere_limpieza_historica"] is True
    assert client.get(f"/api/v1/expedientes/{vacio_id}").status_code == 404

    rechazo = client.post(
        "/api/v1/expedientes/previsualizar-vacios/limpiar",
        json=[vacio_id, historico["expediente_id"], activo["expediente_id"]],
    )
    assert rechazo.status_code == 409
    assert session.get(Expediente, UUID(vacio_id)) is not None
    assert session.get(Expediente, UUID(str(activo["expediente_id"]))) is not None

    limpieza = client.post(
        "/api/v1/expedientes/previsualizar-vacios/limpiar",
        json=[vacio_id, historico["expediente_id"]],
    )
    assert limpieza.status_code == 200, limpieza.text
    assert limpieza.json()["expedientes_eliminados"] == 2
    assert session.get(Expediente, UUID(vacio_id)) is None
    assert session.get(Expediente, UUID(str(historico["expediente_id"]))) is None
    assert session.get(Documento, documento_historico_id) is None
    assert session.get(Expediente, UUID(str(activo["expediente_id"]))) is not None
