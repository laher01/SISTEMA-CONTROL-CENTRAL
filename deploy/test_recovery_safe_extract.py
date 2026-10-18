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


def test_rollback_directory_lookup_never_recreates_deleted_directory(tmp_path):
    import os

    from recovery_safe_extract import _open_directory

    target = tmp_path / "root"
    target.mkdir()
    root_fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(FileNotFoundError):
            _open_directory(root_fd, ("missing",), [], create=False)
        assert not (target / "missing").exists()
    finally:
        os.close(root_fd)


def test_descriptor_directory_lookup_rejects_symlink(tmp_path):
    import os

    from recovery_safe_extract import _open_directory

    target = tmp_path / "root"
    target.mkdir()
    (target / "linked").symlink_to(tmp_path, target_is_directory=True)
    root_fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(OSError):
            _open_directory(root_fd, ("linked",), [], create=False)
    finally:
        os.close(root_fd)


def test_rollback_directory_cleanup_does_not_recreate_parents(tmp_path):
    import os

    from recovery_safe_extract import _rollback

    target = tmp_path / "root"
    target.mkdir()
    fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(FileNotFoundError):
            _rollback(fd, [], [("gone", "child")])
        assert not (target / "gone").exists()
    finally:
        os.close(fd)


def test_extract_denies_conflicting_parent_file(tmp_path):
    archive, manifest, target = make_pair(tmp_path)
    (target / "tenant-a").write_text("existing")
    with pytest.raises(ValueError, match="Destination not empty"):
        extract(archive, manifest, target)
    assert (target / "tenant-a").read_text() == "existing"


def test_rollback_failure_is_explicit_quarantine_signal(tmp_path, monkeypatch):
    import recovery_safe_extract as subject

    archive, manifest, target = make_pair(tmp_path)
    original = subject._open_directory

    def injected(root_fd, parts, created_dirs, *, create=True):
        if create and parts:
            raise PermissionError("injected race")
        return original(root_fd, parts, created_dirs, create=create)

    def failed_rollback(*args):
        raise PermissionError("injected rollback conflict")

    monkeypatch.setattr(subject, "_open_directory", injected)
    monkeypatch.setattr(subject, "_rollback", failed_rollback)
    with pytest.raises(RuntimeError, match="quarantine target"):
        extract(archive, manifest, target)


def test_compressed_archive_quota_fails_before_extraction(tmp_path, monkeypatch):
    import recovery_safe_extract as subject

    archive, manifest, target = make_pair(tmp_path)
    monkeypatch.setattr(subject, "MAX_COMPRESSED", 4)
    with pytest.raises(ValueError, match="Compressed archive too large"):
        extract(archive, manifest, target)
    assert list(target.iterdir()) == []

def test_rollback_preserves_replaced_inode(tmp_path):
    import os

    from recovery_safe_extract import _rollback

    target = tmp_path / "root"
    target.mkdir()
    original = target / "invoice.txt"
    original.write_text("owned")
    info = original.stat()
    replacement = target / "replacement.txt"
    replacement.write_text("foreign")
    os.replace(replacement, original)
    fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ValueError, match="inode changed"):
            _rollback(fd, [(("invoice.txt",), (info.st_dev, info.st_ino))], [])
        assert original.read_text() == "foreign"
    finally:
        os.close(fd)


def test_rollback_removes_unchanged_owned_inode(tmp_path):
    import os

    from recovery_safe_extract import _rollback

    target = tmp_path / "root"
    target.mkdir()
    own = target / "owned.txt"
    own.write_text("owned")
    info = own.stat()
    fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY)
    try:
        _rollback(fd, [(("owned.txt",), (info.st_dev, info.st_ino))], [])
        assert not own.exists()
    finally:
        os.close(fd)
