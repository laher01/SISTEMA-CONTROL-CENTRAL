# FACT CENTRAL SaaS — Instrucciones para asistentes

**Leer antes de editar código:** [Centro de Coordinación](docs/COORDINACION/00_LEER_PRIMERO.md).

- FACT CENTRAL es una plataforma SaaS multi-tenant, no un ERP independiente.
- Antes de programar, verificar el `main` vigente, documentos de coordinación, Issues, PR abiertos y responsables.
- Un solo responsable principal por tarea. No duplicar tareas activas de otros chats.
- Desarrollar exclusivamente en ramas independientes; abrir PR con pruebas.
- **No fusionar a `main` ni desplegar sin autorización expresa del usuario.**
- Informar antes de cambiar archivos compartidos, autenticación, modelos o migraciones.
- SUPERADMIN gestiona plataforma pero su inspección de datos de cada Tenant será de solo lectura, auditada, sin suplantar sesiones.
- Un Tenant jamás accede a otro; no compartir datos ni identidades operativas.
- No guardar contraseñas, tokens o claves SSH en repositorio.
- No confundir PROYECTADO, INTEGRADO, DESPLEGADO y VERIFICADO.
- Etapa 7 (Landing, CMS, planes y NEXUS comercial) está asignada a otro chat: no modificarla aquí.
