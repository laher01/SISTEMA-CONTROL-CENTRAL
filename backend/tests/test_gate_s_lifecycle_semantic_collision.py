"""Gate S static safety checks: signature and semantic collision.

Only synthetic sources; actual PR sources are inspected by the CLI using git show.
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "gate_s_contract_dryrun",
    Path(__file__).resolve().parents[2] / "scripts" / "gate_s_contract_dryrun.py",
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


HARD = """
def eliminar_documento(session, settings, hoy, tenant_id, auth, almacen, documento_id):
    bloquear_tenant_documental(session, tenant_id)
    session.delete(documento)
"""
SOFT = """
def eliminar_documento(session, settings, hoy, tenant_id, auth, documento_id):
    documento.deleted_at = ahora()

def retirar_documentos_lote():
    eliminar_documento(session, settings, hoy, tenant_id, auth, documento_id)
"""


def test_contract_identifies_signature_and_semantic_collision():
    report = module.lifecycle_semantics(HARD, SOFT)
    assert report["positional_mismatch"]
    assert report["batch_positional_args"] == 6
    assert report["physical_required_args"] == 7
    assert report["soft_assigns_deleted_at"]
    assert report["physical_has_storage_parameter"]
    assert report["physical_calls_transaction_lock"]
    assert report["semantic_collision_risk"]
    assert report["status"] == "BLOCK_INTEGRATION"


def test_equal_signatures_do_not_override_semantic_blocker():
    changed_hard = HARD.replace("auth, almacen, documento_id", "auth, documento_id")
    report = module.lifecycle_semantics(changed_hard, SOFT)
    assert not report["positional_mismatch"]
    assert report["semantic_collision_risk"]
    assert report["status"] == "BLOCK_INTEGRATION"
