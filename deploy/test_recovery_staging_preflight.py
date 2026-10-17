import argparse
import pytest
from recovery_staging_preflight import verify


def args(tmp_path):
    a = tmp_path / "source"
    b = tmp_path / "target"
    a.mkdir()
    b.mkdir()
    return argparse.Namespace(
        confirm="ISOLATED-STAGING-ONLY",
        source_env="staging",
        target_env="ephemeral",
        source_database="staging_data",
        target_database="test_restore",
        source_documents=str(a),
        target_documents=str(b),
        expected_host="staging-review-01",
        actual_host="staging-review-01",
    )


def test_preflight_valid(tmp_path):
    assert verify(args(tmp_path))


@pytest.mark.parametrize("field,value", [
    ("confirm", "NO"),
    ("source_env", "production"),
    ("target_env", "staging"),
    ("target_database", "staging_data"),
    ("actual_host", "another-host"),
])
def test_fail_closed(tmp_path, field, value):
    item = args(tmp_path)
    setattr(item, field, value)
    with pytest.raises(ValueError):
        verify(item)


def test_reject_nested_volume(tmp_path):
    item = args(tmp_path)
    nested = tmp_path / "source" / "nested"
    nested.mkdir()
    item.target_documents = str(nested)
    with pytest.raises(ValueError):
        verify(item)


def test_reject_nonempty_restore_target(tmp_path):
    item = args(tmp_path)
    (tmp_path / "target" / "data").write_text("in use")
    with pytest.raises(ValueError):
        verify(item)
