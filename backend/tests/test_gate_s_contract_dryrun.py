"""Synthetic, offline tests for the Gate S read-only contract analyzer."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "gate_s_contract_dryrun",
    Path(__file__).resolve().parents[2] / "scripts" / "gate_s_contract_dryrun.py",
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_detects_old_batch_signature_and_locking():
    delete_src = (
        "def eliminar_documento(session, settings, hoy, tenant_id, auth, almacen, documento_id):\n"
        "    pass\n"
    )
    trash_src = (
        "def capacidades_documentales():\n    return {}\n"
        "def restaurar_documento():\n    pass\n"
        "def retirar_documentos_lote():\n"
        "    eliminar_documento(session, settings, hoy, tenant_id, auth, documento_id)\n"
    )
    result = module.analyze_sources(
        delete_src, trash_src, "def registrar_items_ubl():\n    pass\n",
        "def registrar_items_ubl():\n    Tenant.id\n    with_for_update()\n",
    )
    assert result["signature_mismatch"] is True
    assert result["status"] == "RECONCILIATION_REQUIRED"
    assert result["capabilities_endpoint"] is True
    assert result["items_locking"] is True


def test_compatible_signature_does_not_certify_runtime():
    src = "def eliminar_documento(session, documento_id):\n    pass\n"
    trash = "def retirar_documentos_lote():\n    eliminar_documento(session, documento_id)\n"
    result = module.analyze_sources(src, trash, "", "")
    assert result["signature_mismatch"] is False
    assert result["status"] == "STATIC_SIGNATURE_CHECK_ONLY"
    assert "runtime" in result["limitations"]


def test_missing_expected_function_is_explicit_blocker():
    with pytest.raises(ValueError):
        module.analyze_sources("pass", "pass", "", "")
