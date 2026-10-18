#!/usr/bin/env python3
"""Verify actual restored PostgreSQL tenant/document/expediente joins.

Runs only against explicitly selected local synthetic database. Read-only.
"""
import os
import sys
from sqlalchemy import create_engine, text

def validate(url):
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("FC_RECOVERY_SYNTHETIC_ONLY") != "YES":
        raise ValueError("CI synthetic guard required")
    if not url.startswith("postgresql+psycopg://fact:fact@localhost:5432/fact_restore_synthetic_"):
        raise ValueError("Only local ephemeral restore DB allowed")
    engine = create_engine(url)
    with engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT d.tenant_id, d.expediente_id, e.tenant_id AS expediente_tenant
            FROM documentos d INNER JOIN expedientes e ON d.expediente_id = e.id
            WHERE d.expediente_id IS NOT NULL
        """)).mappings().all()
        if not rows:
            raise ValueError("No restored document-expediente rows")
        if any(r["tenant_id"] != r["expediente_tenant"] for r in rows):
            raise ValueError("Cross-tenant document-expediente relation")
        broken = connection.execute(text("""
            SELECT COUNT(*) FROM documentos d LEFT JOIN expedientes e ON e.id = d.expediente_id
            WHERE d.expediente_id IS NOT NULL AND e.id IS NULL
        """)).scalar_one()
        if broken:
            raise ValueError("Orphan document relationship")
        print(f"RESTORED_DOCUMENT_TENANT_RELATIONS_OK: {len(rows)}")

if __name__ == "__main__":
    try:
        validate(os.environ["FC_DATABASE_URL"])
    except (ValueError, KeyError) as exc:
        print(f"RECOVERY_RELATIONS_FAILED: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
