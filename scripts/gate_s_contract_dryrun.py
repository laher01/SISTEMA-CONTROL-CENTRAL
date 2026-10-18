#!/usr/bin/env python3
"""Gate S: static, read-only contract diagnostic across existing git refs.

Usage (in a local authorized repository with fetched refs):
python3 scripts/gate_s_contract_dryrun.py --delete-ref <sha286> --trash-ref <sha292> --items-ref <sha186> --rescan-ref <sha281>
Does not checkout, merge, deploy, use SSH, or connect to a database.
"""
import argparse
import ast
import json
import subprocess
from pathlib import Path

DOCUMENTOS = "backend/app/api/routes/documentos.py"
ITEMS = "backend/app/services/contabilidad_items_ubl.py"
MIGRATIONS = {
    "0024": "backend/alembic/versions/20261010_0024_tarifas_duales_usuario.py",
    "0035": "backend/alembic/versions/20261014_0035_contabilidad_items.py",
    "0041": "backend/alembic/versions/20261018_0041_casos_ocr.py",
}


def git_show(ref: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"Unavailable git object: {ref[:12]}:{path}")
    return completed.stdout


def definition(tree: ast.Module, name: str):
    return next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)


def analyze_sources(delete_src: str, trash_src: str, items_src: str, rescan_src: str) -> dict:
    delete_tree, trash_tree = ast.parse(delete_src), ast.parse(trash_src)
    definition_delete = definition(delete_tree, "eliminar_documento")
    batch = definition(trash_tree, "retirar_documentos_lote")
    cap = definition(trash_tree, "capacidades_documentales")
    if definition_delete is None or batch is None:
        raise ValueError("Expected deletion and batch endpoints not found")
    required_args = [a.arg for a in definition_delete.args.args]
    calls = [x for x in ast.walk(batch) if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == "eliminar_documento"]
    supplied_args = len(calls[0].args) if calls else None
    signature_mismatch = supplied_args is not None and supplied_args < len(required_args)
    return {
        "delete_signature": required_args,
        "batch_arguments": supplied_args,
        "batch_uses_delete": bool(calls),
        "signature_mismatch": signature_mismatch,
        "capabilities_endpoint": cap is not None,
        "restore_endpoint": definition(trash_tree, "restaurar_documento") is not None,
        "items_locking": "with_for_update()" in rescan_src and "Tenant.id" in rescan_src,
        "item_line_uniqueness_recheck_required": "registrar_items_ubl" in items_src,
        "status": "RECONCILIATION_REQUIRED" if signature_mismatch else "STATIC_SIGNATURE_CHECK_ONLY",
        "limitations": "Static AST cannot verify runtime routing, DB transactions, or file-system rollback.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete-ref", required=True)
    parser.add_argument("--trash-ref", required=True)
    parser.add_argument("--items-ref", required=True)
    parser.add_argument("--rescan-ref", required=True)
    parser.add_argument("--migration-0024-ref")
    parser.add_argument("--migration-0041-ref")
    args = parser.parse_args()
    try:
        result = analyze_sources(
            git_show(args.delete_ref, DOCUMENTOS),
            git_show(args.trash_ref, DOCUMENTOS),
            git_show(args.items_ref, ITEMS),
            git_show(args.rescan_ref, ITEMS),
        )
        migration_refs = {
            "0024": args.migration_0024_ref,
            "0035": args.items_ref,
            "0041": args.migration_0041_ref,
        }
        revisions = {}
        for revision, ref in migration_refs.items():
            if not ref:
                revisions[revision] = {"status": "REF_NOT_SUPPLIED"}
                continue
            t = ast.parse(git_show(ref, MIGRATIONS[revision]))
            assignments = {}
            for node in t.body:
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    if node.target.id in ("revision", "down_revision"):
                        assignments[node.target.id] = ast.literal_eval(node.value)
            revisions[revision] = assignments
        result["migration_metadata"] = revisions
        print(json.dumps(result, indent=2, sort_keys=True))
    except (RuntimeError, ValueError, SyntaxError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
