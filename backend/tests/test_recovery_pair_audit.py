"""Recovery pair auditor: offline tests with synthetic files only."""
import hashlib
import io
import json
import tarfile

import pytest

from deploy.recovery_pair_audit import compare, digest, inspect_tar, relative_path


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
