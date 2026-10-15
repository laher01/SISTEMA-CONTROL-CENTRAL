# Arquitectura SaaS acordada

FACT CENTRAL → SUPERADMIN → tenants aislados → ADMINISTRADOR propietario → Gerencia / Secretaría / Responsables → Usuarios → Gestores. Tenant autenticado en backend; identidades y documentos aislados. Códigos como ADMIN01 pueden repetirse entre tenants. SUPERADMIN separado, operaciones de tenants en solo lectura. VPS MASTER, STORAGE y BACKUP son visión objetivo; su despliegue NO está confirmado. No guardar secretos en GitHub.
