"""Recovery pair auditor: offline tests with synthetic files only."""
import hashlib
import io
import tarfile
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deploy.recovery_pair_audit import compare, inspect_tar  # noqa: E402


def archive(tmp_path, members):
    p = tmp_path / "documents.tar.gz"
    with tarfile.open(p, "w:gz") as output:
        for name, data, kind in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(data)
                output.addfile(info, io.BytesIO(data))
            else:
                info.type = tarfile.SYMTYPE
                info.linkname = "../escape"
                output.addfile(info)
    return p


def test_manifest_valid_pair(tmp_path):
    data = b"synthetic-doc"
    path = archive(tmp_path, [("tenant-a/invoice.pdf", data, "file")])
    expected = {"tenant-a/invoice.pdf": {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}}
    assert inspect_tar(path) == expected
    compare({"files": expected}, inspect_tar(path))


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute", "nested/../escape", "a\\b"])
def test_reject_traversal(tmp_path, unsafe):
    path = archive(tmp_path, [(unsafe, b"test", "file")])
    with pytest.raises(ValueError):
        inspect_tar(path)


def test_reject_symlink_and_duplicate(tmp_path):
    with pytest.raises(ValueError):
        inspect_tar(archive(tmp_path, [("link", b"", "link")]))
    with pytest.raises(ValueError):
        inspect_tar(archive(tmp_path, [("a", b"a", "file"), ("a", b"b", "file")]))


def test_reject_manifest_hash_mismatch(tmp_path):
    path = archive(tmp_path, [("a", b"a", "file")])
    with pytest.raises(ValueError):
        compare({"files": {"a": {"size": 1, "sha256": "0" * 64}}}, inspect_tar(path))


def test_reject_empty_archive(tmp_path):
    with pytest.raises(ValueError):
        inspect_tar(archive(tmp_path, []))


def test_reject_many_archive_members(tmp_path):
    p = tmp_path / "many.tar.gz"
    with tarfile.open(p, "w:gz") as output:
        for i in range(10001):
            info = tarfile.TarInfo(f"test/{i}.txt")
            info.size = 1
            output.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="limits"):
        inspect_tar(p)


def test_pair_audit_rejects_tenant_file_substitution_even_if_size_matches(tmp_path):
    """An equally sized document from another tenant is not the paired backup."""
    a = b"tenant-A-invoice"
    b = b"tenant-B-invoice"
    assert len(a) == len(b)
    name = "tenant-a/invoice.pdf"
    expected = {name: {"size": len(a), "sha256": hashlib.sha256(a).hexdigest()}}
    substituted = archive(tmp_path, [(name, b, "file")])
    with pytest.raises(ValueError, match="hash/size mismatch"):
        compare({"files": expected}, inspect_tar(substituted))


def test_pair_audit_rejects_tenant_path_reassignment(tmp_path):
    """Same document bytes must not silently migrate to a different tenant path."""
    payload = b"same-file"
    path = archive(tmp_path, [("tenant-b/invoice.pdf", payload, "file")])
    expected = {
        "tenant-a/invoice.pdf": {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    }
    with pytest.raises(ValueError, match="inventory mismatch"):
        compare({"files": expected}, inspect_tar(path))


def test_pair_manifest_rejects_second_tenant_even_with_same_payload(tmp_path):
    """Manifest cannot silently omit an extra tenant's archived document."""
    payload = b"shared-payload"
    path = archive(tmp_path, [
        ("tenant-a/doc.pdf", payload, "file"),
        ("tenant-b/doc.pdf", payload, "file"),
    ])
    expected = {"tenant-a/doc.pdf": {
        "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)
    }}
    with pytest.raises(ValueError, match="inventory mismatch"):
        compare({"files": expected}, inspect_tar(path))


def test_same_document_name_allowed_when_tenant_paths_are_distinct(tmp_path):
    """Two tenants may use an identical filename without collapsing identities."""
    payload = b"shared-payload"
    path = archive(tmp_path, [
        ("tenant-a/invoice.pdf", payload, "file"),
        ("tenant-b/invoice.pdf", payload, "file"),
    ])
    entries = inspect_tar(path)
    assert set(entries) == {"tenant-a/invoice.pdf", "tenant-b/invoice.pdf"}
    compare({"files": entries}, entries)


def test_repeated_audit_is_idempotent_and_does_not_modify_archive(tmp_path):
    """An audit replay must be read-only and yield identical inventory."""
    payload = b"tenant-synthetic"
    tar_path = archive(tmp_path, [("tenant-a/doc.pdf", payload, "file")])
    before = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    first = inspect_tar(tar_path)
    second = inspect_tar(tar_path)
    compare({"files": first}, second)
    assert first == second
    assert hashlib.sha256(tar_path.read_bytes()).hexdigest() == before


def test_manifest_fails_when_file_inventory_is_empty_but_archive_is_not(tmp_path):
    path = archive(tmp_path, [("tenant-a/doc.pdf", b"data", "file")])
    with pytest.raises(ValueError, match="inventory mismatch"):
        compare({"files": {}}, inspect_tar(path))
