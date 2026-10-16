# NEXUS Knowledge Bridge — contrato de memoria persistente (v0.1)

Estado: especificación para revisión; **no implementado**. No crea tablas, servicios, conectores ni tareas.

## Principios
- GitHub guarda documentación técnica versionada y PR; **no** es almacén de chats privados.
- PostgreSQL aloja registros de memoria con separación por tenant; la API aplica el ámbito autenticado.
- Cada recuerdo distingue fuente comprobable, interpretación propuesta y decisión aprobada.
- El contenido importado se considera **dato no confiable**, nunca instrucciones privilegiadas para el agente.
- Las conversaciones privadas solo se importan por selección/consentimiento expreso y mediante exportación o integración autorizada.

## Entidades propuestas

### nexus_knowledge_sources
- id UUID; tenant_id UUID; owner_account_id UUID; source_type enum [GITHUB_DOC, USER_UPLOAD, CHAT_EXPORT, MANUAL_NOTE, OPERATIVE_EVENT]
- external_ref string nullable (sin tokens); revision string nullable; sha256 char(64); title string
- ingestion_consent_at timestamptz nullable; consent_actor_id UUID nullable
- visibility enum [PRIVATE, ROLE, TENANT]; created_at; revoked_at nullable; retention_until nullable
- storage_reference privada; **nunca** almacenar URL firmada ni credenciales

### nexus_knowledge_items
- id UUID; tenant_id UUID; source_id UUID; version int; parent_version_id UUID nullable
- classification enum [HYPOTHESIS, PROPOSAL, VERIFIED_FACT, APPROVED_POLICY, OBSOLETE]
- state enum [DRAFT, IN_REVIEW, APPROVED, REJECTED, REVOKED]
- title; content_redacted; evidence_locator; confidence_note (texto no numérico); effective_from; effective_until
- author_account_id; approver_account_id nullable; approved_at nullable; revoked_at nullable
- created_at; updated_at
- Exclusión lógica y auditoría; nunca alteración silenciosa de una versión aprobada

### nexus_knowledge_events
- id UUID; tenant_id UUID; item_id UUID nullable; actor_account_id UUID
- action enum [IMPORT, READ, PROPOSE, APPROVE, REJECT, SUPERSEDE, REVOKE, ERASE]
- reason; created_at; correlation_id; metadata_sanitized
- Registrar identificadores de objetos, no texto íntegro ni secretos en logs

## Contrato de consulta
Entradas derivadas de sesión: tenant_id, actor, rol, ámbito organizacional y propósito.
Entradas del cliente: query, filtros de fechas, límite de resultados; no aceptar tenant_id ni rol del navegador.
Aplicar ACL en SQL **antes** de ranking semántico o búsqueda textual; devolver únicamente fuentes visibles y vigentes.
Separar respuestas: hecho respaldado, política aprobada, propuesta e incertidumbre.
No promover borradores como instrucciones oficiales.

## Contrato de importación
1. Autorización y selección explícitas del propietario o actor competente.
2. Análisis de archivo, tamaño y formato permitido; rechazo de contenido peligroso.
3. Eliminación/redacción de secretos, datos personales no necesarios y material sin autorización.
4. Hash, procedencia y conservación del original en almacenamiento privado según política de retención.
5. Crear borradores propuestos; exigir revisión antes de aprobar.
6. Versionar, indexar y auditar; permitir revocación y eliminación conforme a políticas.

## Comunicación con IA
- Un modelo externo solo recibe segmentos mínimos permitidos, tras control de acceso y saneamiento.
- No enviar conversaciones privadas completas por defecto.
- Respuestas generadas nunca autorizan comandos al servidor ni cambios de reglas.
- Un fallo del proveedor conserva el modo contextual y comunica la limitación.

## Pruebas obligatorias antes de implementar/desplegar
1. Tenant A jamás recupera fuentes/items/eventos de Tenant B, incluso por IDs adivinados.
2. GESTOR y SECRETARIA no reciben conocimiento fuera del ámbito explícitamente autorizado.
3. Un borrador, elemento revocado u obsoleto no aparece como política vigente.
4. La importación sin consentimiento verificable se rechaza.
5. Una instrucción maliciosa dentro del documento no ejecuta herramientas ni amplía permisos.
6. Reimportaciones del mismo hash/procedencia/version son idempotentes.
7. Revocación elimina el ítem de recuperación y de cachés; audita la operación.
8. Ausencia de proveedor externo no rompe la consulta local.
9. Respaldos, migraciones en DB desechable y restauración aislada superan CI/preflight.
10. Registros y GitHub no contienen credenciales ni datos personales innecesarios.

## Orden de implementación
A. Revisar contrato y permisos existentes; definir retención.
B. Modelos + migración nueva, sin alterar revisiones aplicadas.
C. Ingesta manual segura y endpoints solo lectura por ámbito.
D. Aprobación/revocación y auditoría.
E. Recuperación y canal de incidencias con GitHub/LLM opt-in.
F. Pruebas, CI, respaldo restaurable y despliegue supervisado.
