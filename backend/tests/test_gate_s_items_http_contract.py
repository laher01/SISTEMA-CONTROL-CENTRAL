"""Read-only API smoke checks with synthetic test DB and auth fixtures.

These run the existing HTTP route only. They do not combine PR #186/#281/#211/#212
or claim to validate end-to-end order progress.
"""

from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba


def test_items_endpoint_empty_tenant_readable_to_authorized_admin(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    response = client.get("/api/v1/contabilidad-items")
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_items_endpoint_invalid_date_range_rejected(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    response = client.get(
        "/api/v1/contabilidad-items",
        params={"desde": "2026-10-15", "hasta": "2026-10-14"},
    )
    assert response.status_code == 422, response.text


def test_items_endpoint_superadmin_is_not_an_operational_role(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_superadmin()
    response = client.get("/api/v1/contabilidad-items")
    assert response.status_code == 403, response.text


def test_items_endpoint_rejects_invalid_pagination_limit(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    response = client.get("/api/v1/contabilidad-items", params={"limite": 501})
    assert response.status_code == 422, response.text


def test_items_endpoint_unknown_emisor_returns_no_records(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    response = client.get(
        "/api/v1/contabilidad-items",
        params={"emisor_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == []


def test_items_endpoint_unknown_receptor_returns_no_records(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    response = client.get(
        "/api/v1/contabilidad-items",
        params={"receptor_id": "00000000-0000-0000-0000-000000000002"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == []
