#!/usr/bin/env python3
"""Insert synthetic relational data into CI's ephemeral source PostgreSQL."""
import os
import uuid
from sqlalchemy import create_engine, text

if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("FC_RECOVERY_SYNTHETIC_ONLY") != "YES":
    raise SystemExit("synthetic CI only")
url = os.environ["FC_DATABASE_URL"]
if not url.endswith("/fact_central") or "localhost:5432" not in url:
    raise SystemExit("refuse non-ephemeral CI source")
engine = create_engine(url)
with engine.begin() as c:
    for idx in (1, 2):
        tenant, company1, company2, expedition, document = [str(uuid.uuid4()) for _ in range(5)]
        c.execute(text("INSERT INTO tenants(id,nombre) VALUES (:id,:name)"), {"id": tenant, "name": f"synthetic-{idx}"})
        c.execute(text("INSERT INTO empresas(id,tenant_id,ruc,razon_social) VALUES (:id,:t,:r,:n)"),
            {"id": company1, "t":tenant,"r":f"2000000000{idx}","n":"Synthetic issuer"})
        c.execute(text("INSERT INTO empresas(id,tenant_id,ruc,razon_social) VALUES (:id,:t,:r,:n)"),
            {"id":company2,"t":tenant,"r":f"2000000001{idx}","n":"Synthetic recipient"})
        c.execute(text("""INSERT INTO expedientes
          (id,tenant_id,receptor_id,emisor_id,tipo_comprobante,serie,correlativo,fecha_emision,moneda,importe_total,estado)
          VALUES (:id,:t,:r,:e,'01','F001',:n,CURRENT_DATE,'PEN',100.00,'NARANJA')"""),
          {"id":expedition,"t":tenant,"r":company2,"e":company1,"n":f"000{idx}"})
        c.execute(text("""INSERT INTO documentos
          (id,tenant_id,expediente_id,estado,sha256,nombre_original,mime_type,tamano_bytes,ruta_storage)
          VALUES (:id,:t,:e,'RECIBIDO',:hash,:name,'application/pdf',10,:path)"""),
          {"id":document,"t":tenant,"e":expedition,"hash":f"{idx}"*64,
           "name":"sample.pdf","path":f"synthetic-{idx}/sample.pdf"})
print("SYNTHETIC_RELATIONAL_FIXTURES_READY")
