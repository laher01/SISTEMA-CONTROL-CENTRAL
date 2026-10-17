"""Offline coordinated restore planner: no subprocesses, DB or network actions.

A privileged staging runner must separately implement and authorize actual operations.
"""
from dataclasses import dataclass
from pathlib import Path

from recovery_pair_audit import compare, inspect_tar


@dataclass(frozen=True)
class DocumentReference:
    tenant: str
    expediente: str
    path: str
    sha256: str


def verify_references(entries: dict, references: list[DocumentReference]) -> dict:
    """Fail closed if any row lacks its matching archived file or crosses tenants."""
    if not references:
        raise ValueError("No document references to validate")
    seen = set()
    tenants: dict[str, int] = {}
    for ref in references:
        if not ref.tenant or not ref.expediente or not ref.path:
            raise ValueError("Incomplete document relation")
        if not ref.path.startswith(ref.tenant + "/"):
            raise ValueError("Cross-tenant document path")
        if (ref.tenant, ref.expediente, ref.path) in seen:
            raise ValueError("Duplicate document reference")
        seen.add((ref.tenant, ref.expediente, ref.path))
        item = entries.get(ref.path)
        if item is None or item["sha256"] != ref.sha256:
            raise ValueError("Missing or tampered referenced file")
        tenants[ref.tenant] = tenants.get(ref.tenant, 0) + 1
    if set(entries) != {ref.path for ref in references}:
        raise ValueError("Unreferenced files need explicit documented disposition")
    return tenants


def verify_migration_transitions(history: list[str]) -> None:
    """Verify synthetic migration state transitions, not an actual Alembic run."""
    if history != ["0038", "0039", "0038", "0039"]:
        raise ValueError("Unsafe or incomplete 0039 roundtrip")


def verify_synthetic_rbac(tenant: str, document_tenant: str, allowed: bool) -> None:
    if allowed != (tenant == document_tenant):
        raise ValueError("Synthetic tenant access rule violated")


def validate_synthetic_drill(entries: dict, references: list[DocumentReference],
                             history: list[str]) -> dict:
    totals = verify_references(entries, references)
    verify_migration_transitions(history)
    for tenant in totals:
        verify_synthetic_rbac(tenant, tenant, True)
        verify_synthetic_rbac(tenant, tenant + "-other", False)
    return totals
