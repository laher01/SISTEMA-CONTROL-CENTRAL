from fastapi.testclient import TestClient

from tests.xml import RECEPTOR, factura


def crear_usuario_y_gestor(client: TestClient) -> tuple[dict[str, object], dict[str, object]]:
    usuario_resp = client.post(
        "/api/v1/miembros",
        json={"codigo": "WILL01", "nombre": "Willy", "rol": "USUARIO"},
    )
    assert usuario_resp.status_code == 201, usuario_resp.text
    usuario = usuario_resp.json()

    gestor_resp = client.post(
        "/api/v1/gestores",
        json={
            "codigo": "GES01",
            "nombre": "José",
            "usuario_id": usuario["id"],
        },
    )
    assert gestor_resp.status_code == 201, gestor_resp.text
    return usuario, gestor_resp.json()


def test_gestor_pertenece_a_usuario_y_propaga_propiedad(client: TestClient) -> None:
    usuario, gestor = crear_usuario_y_gestor(client)

    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("f.xml", factura())},
        data={"gestor_id": gestor["id"]},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = respuesta.json()

    assert documento["gestor_id"] == gestor["id"]
    assert documento["usuario_id"] == usuario["id"]

    detalle = client.get(f"/api/v1/expedientes/{documento['expediente_id']}").json()
    assert detalle["gestor_id"] == gestor["id"]
    assert detalle["usuario_id"] == usuario["id"]

    produccion = client.get("/api/v1/produccion/resumen")
    assert produccion.status_code == 200, produccion.text
    filas = produccion.json()["filas"]
    assert len(filas) == 1
    assert filas[0]["usuario_codigo"] == "WILL01"
    assert filas[0]["gestor_codigo"] == "GES01"
    assert filas[0]["expedientes"] == 1


def test_gestor_solo_puede_pertenecer_a_rol_usuario(client: TestClient) -> None:
    gerente = client.post(
        "/api/v1/miembros",
        json={"codigo": "GER01", "nombre": "Gerencia", "rol": "GERENTE"},
    ).json()

    respuesta = client.post(
        "/api/v1/gestores",
        json={"codigo": "GES02", "nombre": "María", "usuario_id": gerente["id"]},
    )
    assert respuesta.status_code == 422


def test_factura_menor_al_umbral_no_exige_voucher_ni_guia(client: TestClient) -> None:
    _, gestor = crear_usuario_y_gestor(client)
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("menor.xml", factura(importe="1500.00"))},
        data={"gestor_id": gestor["id"]},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = respuesta.json()

    detalle = client.get(f"/api/v1/expedientes/{documento['expediente_id']}").json()
    assert detalle["requiere_guia"] is False
    assert "VCHR" not in detalle["faltantes"]
    assert "GRR" not in detalle["faltantes"]


def test_rhe_se_busca_con_prefijo_rhe(client: TestClient) -> None:
    usuario, gestor = crear_usuario_y_gestor(client)
    respuesta = client.post(
        "/api/v1/expedientes",
        json={
            "receptor": {"ruc": RECEPTOR, "razon_social": "CLIENTE SAC"},
            "emisor": {"ruc": "10456789012", "razon_social": "JUAN PEREZ"},
            "tipo_comprobante": "RHE",
            "serie": "E001",
            "correlativo": "15",
            "fecha_emision": "2026-09-05",
            "importe_total": "1200.00",
            "gestor_id": gestor["id"],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    creado = respuesta.json()
    assert creado["usuario_id"] == usuario["id"]

    busqueda = client.get("/api/v1/expedientes", params={"buscar": "RHE-E001-15"})
    assert busqueda.status_code == 200, busqueda.text
    assert [item["id"] for item in busqueda.json()] == [creado["id"]]


def test_editar_usuario(client: TestClient) -> None:
    usuario, _ = crear_usuario_y_gestor(client)
    respuesta = client.patch(
        f"/api/v1/miembros/{usuario['id']}",
        json={"codigo": "WILL02", "nombre": "Willy Actualizado", "rol": "USUARIO"},
    )
    assert respuesta.status_code == 200, respuesta.text
    actualizado = respuesta.json()
    assert actualizado["codigo"] == "WILL02"
    assert actualizado["nombre"] == "Willy Actualizado"


def test_editar_y_reasignar_gestor(client: TestClient) -> None:
    _, gestor = crear_usuario_y_gestor(client)
    otro = client.post(
        "/api/v1/miembros",
        json={"codigo": "JOSE01", "nombre": "José Carlos", "rol": "USUARIO"},
    ).json()

    respuesta = client.patch(
        f"/api/v1/gestores/{gestor['id']}",
        json={
            "codigo": "GES99",
            "nombre": "Gestor Actualizado",
            "usuario_id": otro["id"],
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    actualizado = respuesta.json()
    assert actualizado["codigo"] == "GES99"
    assert actualizado["nombre"] == "Gestor Actualizado"
    assert actualizado["usuario_id"] == otro["id"]
