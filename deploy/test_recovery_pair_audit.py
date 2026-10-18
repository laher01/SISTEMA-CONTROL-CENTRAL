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
