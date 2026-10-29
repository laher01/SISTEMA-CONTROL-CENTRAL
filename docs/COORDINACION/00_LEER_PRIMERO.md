# LEER PRIMERO — Coordinación multichat S.P.T.

## Secuencia obligatoria
1. Consultar `main` actualizado, `AGENTS.md` y esta carpeta.
2. Consultar PR abiertos, Issues, ramas y código pertinente. El registro documental puede quedar desactualizado: contrastar GitHub.
3. Comprobar si la tarea está implementada, en progreso, reservada o libre.
4. Registrar identificador, responsable, módulo, rama, archivos previstos y dependencias antes de desarrollar.
5. Trabajar en rama independiente con pruebas y PR; no fusionar ni desplegar sin autorización.
6. Actualizar el registro al finalizar indicando evidencias y pendientes, sin pisar cambios paralelos.

## Identidad del proyecto
S.P.T. (Sistema Pesquero de Trazabilidad) es la **plataforma SaaS multi-tenant**: SUPERADMIN S.P.T. → tenants aislados → roles operativos propios de cada tenant. SNIDERFISH es el tenant piloto y plantilla; la plataforma no gira en torno a SNIDERFISH. La logística pesquera, documentos y evidencias pertenecen a S.P.T. y se aíslan por tenant.

## Principios no negociables
- Backend debe aislar todas las operaciones por Tenant, incluso ante UUID conocidos; pruebas automáticas.
- SUPERADMIN puede crear y gestionar la plataforma; **inspección interna de Tenants solo lectura y auditada**.
- No compartir documentos, credenciales ni sesiones entre Tenants.
- No incluir secretos reales en Git, documentos, Issues o logs.
- No atribuir a producción lo que solo se ha fusionado o probado.
- No invadir Etapa 7, asignada a otra conversación.

Los responsables se documentan en [02](02_RESPONSABLES_ETAPAS.md); el estado de trabajos, en [03](03_TRABAJOS_EN_CURSO.md).
