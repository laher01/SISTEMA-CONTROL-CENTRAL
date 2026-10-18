"""Offline negative tests for safe extraction of synthetic backup archives."""
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recovery_safe_extract import extract  # noqa: E402


def make_pair(tmp_path, name="tenant-a/invoice.txt", payload=b"synthetic", link=False):
    tar = tmp_path / "docs.tar.gz"
    with tarfile.open(tar, "w:gz") as f:
        t = tarfile.TarInfo(name)
        if link:
            t.type = tarfile.SYMTYPE
            t.linkname = "../../secret"
            f.addfile(t)
        else:
            t.size = len(payload)
            f.addfile(t, io.BytesIO(payload))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "archive_sha256": hashlib.sha256(tar.read_bytes()).hexdigest(),
        "files": {name: {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}},
    }))
    output = tmp_path / "destination"
    output.mkdir()
    return tar, manifest, output


def test_extract_valid(tmp_path):
    archive, manifest, target = make_pair(tmp_path)
    extract(archive, manifest, target)
    assert (target / "tenant-a/invoice.txt").read_bytes() == b"synthetic"


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute", "tenant-a/../escape"])
def test_extract_denies_unsafe_path(tmp_path, unsafe):
    archive, manifest, target = make_pair(tmp_path, name=unsafe)
    with pytest.raises(ValueError):
        extract(archive, manifest, target)


def test_extract_denies_symlink(tmp_path):
    archive, manifest, target = make_pair(tmp_path, link=True)
    with pytest.raises(ValueError):
        extract(archive, manifest, target)


def test_extract_denies_changed_archive(tmp_path):
    archive, manifest, target = make_pair(tmp_path)
    archive.write_bytes(archive.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        extract(archive, manifest, target)


def test_extract_denies_nonempty_destination(tmp_path):
    archive, manifest, target = make_pair(tmp_path)
    (target / "existing").write_text("keep")
    with pytest.raises(ValueError):
        extract(archive, manifest, target)
    assert (target / "existing").read_text() == "keep"


def test_extract_denies_symlink_destination(tmp_path):
    archive, manifest, target = make_pair(tmp_path)
    target.rmdir()
    target.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        extract(archive, manifest, target)


def test_partial_output_removed_on_late_hash_failure(tmp_path):
    archive, manifest, target = make_pair(tmp_path)
    data = json.loads(manifest.read_text())
    data["files"]["tenant-a/invoice.txt"]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        extract(archive, manifest, target)
    assert list(target.rglob("*")) == []
