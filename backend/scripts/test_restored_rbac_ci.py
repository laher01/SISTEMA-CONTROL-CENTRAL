#!/usr/bin/env python3
"""Exercise FastAPI login and authorization against a restored CI database."""

import os

from fastapi.testclient import TestClient

url = os.environ.get("FC_DATABASE_URL", "")
if (
    os.getenv("GITHUB_ACTIONS") != "true"
    or os.getenv("FC_RECOVERY_SYNTHETIC_ONLY") != "YES"
    or not url.startswith(
        "postgresql+psycopg://fact:fact@localhost:5432/fact_restore_synthetic_"
    )
):
    raise SystemExit("Restored disposable CI database required")

from app.main import app  # noqa: E402

with TestClient(app, base_url="https://testserver") as admin:
    valid = admin.post(
        "/api/v1/auth/login",
        json={"espacio": "PRUEBAS", "login": "ADMIN01", "clave": "ClaveE2e123!"},
    )
    assert valid.status_code == 200, (valid.status_code, valid.text[:300])
    assert admin.get("/api/v1/configuracion/permisos").status_code == 200
    assert admin.get("/api/v1/configuracion/administraciones").status_code == 403
    crossed = admin.post(
        "/api/v1/auth/login",
        json={"espacio": "PLATFORM", "login": "ADMIN01", "clave": "ClaveE2e123!"},
    )
    assert crossed.status_code == 401

with TestClient(app, base_url="https://testserver") as platform:
    valid = platform.post(
        "/api/v1/auth/login",
        json={"espacio": "PLATFORM", "login": "SUPADMIN01", "clave": "ClaveE2e123!"},
    )
    assert valid.status_code == 200, (valid.status_code, valid.text[:300])
    assert platform.get("/api/v1/configuracion/administraciones").status_code == 200
    assert platform.get("/api/v1/configuracion/permisos").status_code == 403

print("RESTORED_FASTAPI_AUTHENTICATION_AND_RBAC_OK")
