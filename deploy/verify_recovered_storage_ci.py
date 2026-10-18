#!/usr/bin/env python3
"""Read-only verification of recovered synthetic storage rows and filesystem."""
import hashlib
import os
from pathlib import Path
from sqlalchemy import create_engine, text

url=os.environ["FC_DATABASE_URL"]
root=Path(os.environ["FC_RECOVERED_DOC_ROOT"]).resolve(strict=True)
if os.getenv("GITHUB_ACTIONS")!="true" or os.getenv("FC_RECOVERY_SYNTHETIC_ONLY")!="YES":
    raise SystemExit("CI only")
if not url.startswith("postgresql+psycopg://fact:fact@localhost:5432/fact_restore_synthetic_"):
    raise SystemExit("Only disposable restore DB allowed")
count=0
with create_engine(url).connect() as c:
    rows=c.execute(text("""SELECT d.ruta_storage,d.sha256,d.tamano_bytes,d.tenant_id,
        e.tenant_id AS expediente_tenant FROM documentos d
        JOIN expedientes e ON d.expediente_id=e.id""")).mappings().all()
    if len(rows)!=2:
        raise ValueError("Expected two synthetic document records")
    for row in rows:
        rel=Path(row["ruta_storage"])
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError("Unsafe storage path")
        target=(root/rel).resolve(strict=True)
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("File escapes restore root")
        data=target.read_bytes()
        if row["tenant_id"]!=row["expediente_tenant"]:
            raise ValueError("Tenant mismatch")
        if hashlib.sha256(data).hexdigest()!=row["sha256"] or len(data)!=row["tamano_bytes"]:
            raise ValueError("Storage hash or size mismatch")
        count+=1
print(f"RESTORED_SYNTHETIC_STORAGE_REFERENCES_OK: {count}")
