# Referencia arquitectónica — FACT CENTRAL SaaS

FACT CENTRAL es una plataforma SaaS multi-tenant. Esta hoja define acuerdos mínimos y **no sustituye la revisión del código** ni documentos de arquitectura aún en borrador.

```text
FACT CENTRAL / SUPERADMIN (plataforma)
  ├─ Tenant A → ADMIN01 → Gerencia/Secretaría/Responsables → Usuarios/Gestores
  └─ Tenant B → ADMIN01 → Gerencia/Secretaría/Responsables → Usuarios/Gestores
```

- Cada Tenant tiene exactamente un administrador propietario activo según el objetivo funcional; implementar/verificar restricción transaccional y pruebas.
- `ADMIN01` puede repetirse en Tenants diferentes, sin identidad ni datos compartidos.
- Ninguna operación cruza Tenants, aunque existan comprobantes numéricamente iguales o UUID conocidos.
- SUPERADMIN crea/gestiona Tenants desde la plataforma. La **vista de información operativa** de un Tenant será solo lectura, auditada, sin suplantación de identidad.
- Los datos y documentos necesitan aislamiento en servicios, DB, storage, índices, cachés y backups.
- Master aloja aplicación y servicios; storage y backup son nodos distintos. Réplica no equivale a backup. Recovery exige DB + documentos + configuración sin secretos + gestor seguro de claves.
- Registro de VPS y métricas mediante agentes autenticados; jamás comandos arbitrarios o secretos en documentos.
- Versionar infraestructura y procedimientos en Git; credenciales en vault externo cifrado.
- Requisitos de recuperación: pruebas de restauración periódicas y objetivos RTO/RPO definidos.

**No afirmar alta disponibilidad, aislamiento exhaustivo o recuperación garantizada sin pruebas y verificación operativa.**
