"""Actual login/cookie authentication across isolated tenants; synthetic-only fixtures."""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_contexto_actual, get_hoy
from app.core.config import get_settings
from app.core.db import get_session
from app.main import app
from app.models import CuentaAcceso, Documento, Miembro, Tenant
from app.security import hash_clave


def test_cookie_sessions_cannot_read_other_tenants_documents(engine, settings, reloj, auth_prueba):
    """Exercise real login and cookie resolution, not the mocked identity fixture."""
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        tenant_a = session.get(Tenant, auth_prueba.contexto.tenant_id)
        assert tenant_a is not None
        tenant_b = Tenant(nombre="Seguridad E2E B", codigo="E2E-B", estado="ACTIVO")
        session.add(tenant_b)
        session.flush()
        miembro_b = Miembro(
            tenant_id=tenant_b.id,
            codigo="E2EUSERB",
            nombre="Usuario E2E B",
            rol="USUARIO",
            activo=True,
        )
        session.add(miembro_b)
        session.flush()
        account_a = session.get(CuentaAcceso, auth_prueba.contexto.cuenta_id)
        assert account_a is not None
        account_a.password_hash = hash_clave("ClaveDePrueba-A-2026!")
        account_a.cambio_clave_obligatorio = False
        account_b = CuentaAcceso(
            tenant_id=tenant_b.id,
            login="E2EUSERB",
            miembro_id=miembro_b.id,
            password_hash=hash_clave("ClaveDePrueba-B-2026!"),
            activo=True,
            cambio_clave_obligatorio=False,
        )
        session.add(account_b)
        doc_a = Documento(
            tenant_id=tenant_a.id,
            usuario_id=auth_prueba.contexto.usuario_id,
            nombre_original="doc-a.bin",
            mime_type="application/octet-stream",
            sha256="1" * 64,
            tamano_bytes=4,
            ruta_storage="synthetic/a",
            tipo_documento="OTRO",
            estado="PENDIENTE_RELACION",
        )
        doc_b = Documento(
            tenant_id=tenant_b.id,
            usuario_id=miembro_b.id,
            nombre_original="doc-b.bin",
            mime_type="application/octet-stream",
            sha256="2" * 64,
            tamano_bytes=4,
            ruta_storage="synthetic/b",
            tipo_documento="OTRO",
            estado="PENDIENTE_RELACION",
        )
        session.add_all([doc_a, doc_b])
        session.commit()
        doc_a_id, doc_b_id = doc_a.id, doc_b.id
        espacio_a = tenant_a.codigo or tenant_a.nombre

    def session_override() -> Iterator[Session]:
        with factory() as session:
            yield session

    # The ordinary test 'client' fixture overrides auth: deliberately do NOT use it.
    app.dependency_overrides.pop(get_contexto_actual, None)
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_hoy] = lambda: reloj.hoy
    try:
        with (
            TestClient(app, base_url="https://testserver") as first,
            TestClient(app, base_url="https://testserver") as second,
        ):
            login_a = first.post(
                "/api/v1/auth/login",
                json={
                    "espacio": espacio_a,
                    "login": "TESTUSR",
                    "clave": "ClaveDePrueba-A-2026!",
                },
            )
            assert login_a.status_code == 200, login_a.text
            login_b = second.post(
                "/api/v1/auth/login",
                json={
                    "espacio": "E2E-B",
                    "login": "E2EUSERB",
                    "clave": "ClaveDePrueba-B-2026!",
                },
            )
            assert login_b.status_code == 200, login_b.text
            assert first.get(f"/api/v1/documentos/{doc_a_id}").status_code == 200
            assert first.get(f"/api/v1/documentos/{doc_b_id}").status_code == 404
            assert second.get(f"/api/v1/documentos/{doc_b_id}").status_code == 200
            assert second.get(f"/api/v1/documentos/{doc_a_id}").status_code == 404
            assert first.get(f"/api/v1/documentos/{doc_b_id}/archivo").status_code == 404
            assert second.get(f"/api/v1/documentos/{doc_a_id}/archivo").status_code == 404
    finally:
        app.dependency_overrides.clear()
