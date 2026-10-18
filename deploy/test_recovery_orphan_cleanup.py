import json
import time

from recovery_orphan_cleanup import MARKER, cleanup


def fixture(tmp_path, name, age, valid=True):
    path = tmp_path / name
    path.mkdir()
    if valid:
        (path / MARKER).write_text(json.dumps({
            "kind": "factcentral-ci-ephemeral", "name": name,
            "created_at": time.time() - age,
        }))
    return path


def test_old_owned_cleanup_dry_and_apply(tmp_path):
    p = fixture(tmp_path, "stale", 7200)
    assert cleanup(tmp_path, now=time.time(), ttl=3600) == ["stale"]
    assert p.exists()
    assert cleanup(tmp_path, now=time.time(), ttl=3600, dry_run=False) == ["stale"]
    assert not p.exists()


def test_unmarked_and_recent_preserved(tmp_path):
    a = fixture(tmp_path, "unmarked", 7200, valid=False)
    b = fixture(tmp_path, "recent", 20)
    assert cleanup(tmp_path, now=time.time(), ttl=3600, dry_run=False) == []
    assert a.exists() and b.exists()


def test_symlink_target_preserved(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    marker = outside / MARKER
    marker.write_text(json.dumps({"kind": "factcentral-ci-ephemeral", "name": "linked", "created_at": 1}))
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    assert cleanup(tmp_path, now=time.time(), ttl=3600, dry_run=False) == []
    assert outside.exists()


def test_active_process_never_cleaned(tmp_path):
    import os
    p = fixture(tmp_path, "active", 7200)
    marker = p / MARKER
    data = json.loads(marker.read_text())
    data["pid"] = os.getpid()
    marker.write_text(json.dumps(data))
    assert cleanup(tmp_path, now=time.time(), ttl=3600, dry_run=False) == []
    assert p.exists()


def test_symlink_child_never_cleaned(tmp_path):
    p = fixture(tmp_path, "contains_link", 7200)
    outside = tmp_path.parent / (tmp_path.name + "-kept")
    outside.mkdir(exist_ok=True)
    (p / "link").symlink_to(outside, target_is_directory=True)
    assert cleanup(tmp_path, now=time.time(), ttl=3600, dry_run=False) == []
    assert outside.exists() and p.exists()


def test_pid_marker_without_live_process_still_preserved(tmp_path):
    p = fixture(tmp_path, "old_pid", 7200)
    marker = p / MARKER
    data = json.loads(marker.read_text())
    data["pid"] = 999999999
    marker.write_text(json.dumps(data))
    assert cleanup(tmp_path, now=time.time(), ttl=3600, dry_run=False) == []
    assert p.exists()
