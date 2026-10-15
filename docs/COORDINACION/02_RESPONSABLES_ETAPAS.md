# Responsables de etapas

| Área | Responsable lógico | Restricción |
| --- | --- | --- |
| Landing Page, CMS, planes comerciales, NEXUS comercial (Etapa 7) | Chat responsable de Etapa 7 | Reservado; no modificar |
| Consola SUPERADMIN, inventario, consulta Tenant solo lectura | Chat de arquitectura SaaS (esta conversación) | Rama y PR independientes |
| Seguridad y aislamiento multi-tenant | Chat de arquitectura SaaS (esta conversación) | Cambios de autenticación compartidos requieren aviso |
| VPS y observabilidad de infraestructura | Chat de infraestructura SaaS (esta conversación, hasta reasignación) | No introducir accesos inseguros |
| Storage por Tenant y nodos adicionales | Chat de infraestructura SaaS | No desplegar sin autorización |
| Backups, resiliencia, restauración | Chat de infraestructura SaaS | Respaldos verificados, nunca secretos en Git |
| Otros módulos operativos/documentales | PENDIENTE DE ASIGNACIÓN | Respetar PR y trabajo de otras conversaciones |

Un responsable lógico de chat **no es** propietario de cuenta GitHub. Al asignar un Issue registrar también la persona/cuenta que ejecuta, si se conoce; no inventar identidades.
