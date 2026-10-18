import pytest

from recovery_drill_offline import (
    DocumentReference, validate_synthetic_drill, verify_migration_transitions,
    verify_references, verify_synthetic_rbac,
)


def fixture():
    rows = [DocumentReference("tenant-a", "exp-1", "tenant-a/factura.xml", "a" * 64),
            DocumentReference("tenant-b", "exp-2", "tenant-b/guia.pdf", "b" * 64)]
    files = {r.path: {"sha256": r.sha256, "size": 10} for r in rows}
    return files, rows


def test_valid_synthetic_drill():
    files, rows = fixture()
    assert validate_synthetic_drill(files, rows, ["0038", "0039", "0038", "0039"]) == {
        "tenant-a": 1, "tenant-b": 1,
    }


def test_cross_tenant_document_rejected():
    files, rows = fixture()
    rows[0] = DocumentReference("tenant-b", "exp-1", "tenant-a/factura.xml", "a" * 64)
    with pytest.raises(ValueError, match="Cross-tenant"):
        verify_references(files, rows)


def test_missing_document_rejected():
    files, rows = fixture()
    files.pop("tenant-b/guia.pdf")
    with pytest.raises(ValueError, match="Missing"):
        verify_references(files, rows)


def test_orphan_document_rejected():
    files, rows = fixture()
    files["tenant-a/orphan.txt"] = {"sha256": "a" * 64, "size": 1}
    with pytest.raises(ValueError, match="Unreferenced"):
        verify_references(files, rows)


def test_synthetic_rbac_and_rollback_denial():
    with pytest.raises(ValueError):
        verify_synthetic_rbac("tenant-a", "tenant-b", True)
    with pytest.raises(ValueError):
        verify_migration_transitions(["0038", "0039", "0039"])


@pytest.mark.parametrize("bad_path", ["tenant-a/../secret", "/tenant-a/absolute", "tenant-a\\\\evil"])
def test_unsafe_reference_path_rejected(bad_path):
    files, rows = fixture()
    rows[0] = DocumentReference("tenant-a", "exp-1", bad_path, "a" * 64)
    with pytest.raises(ValueError):
        verify_references(files, rows)


def test_invalid_tenant_identifier_rejected():
    files, rows = fixture()
    rows[0] = DocumentReference("../tenant-a", "exp-1", "tenant-a/factura.xml", "a" * 64)
    with pytest.raises(ValueError):
        verify_references(files, rows)
