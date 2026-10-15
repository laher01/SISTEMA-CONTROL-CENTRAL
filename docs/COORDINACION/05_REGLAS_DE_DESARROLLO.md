# Política de implementación coordinada

1. Revisar `main`, PR, ramas e Issues pertinentes; contrastar documental contra código.
2. Identificar ID de tarea y responsable principal antes de modificar archivos.
3. No duplicar trabajo ya asignado; coordinar y actualizar registro.
4. Crear rama desde `main` vigente; un PR por cambio coherente con descripción, archivos, riesgos, pruebas y dependencias.
5. Avisar **antes** de editar archivos compartidos: `models.py`, migraciones, seguridad, rutas comunes, `App.tsx`, configuración y despliegue.
6. No fusionar ni desplegar sin aprobación expresa del usuario; PR aprobado no equivale a despliegue.
7. Mantener migraciones lineales y verificadas, datos existentes y compatibilidad multi-tenant.
8. No introducir secretos reales en código, markdown, variables de ejemplo, logs o PR.
9. Estado oficial: PROPUESTO → ASIGNADO → EN DESARROLLO → EN PRUEBAS → PR ABIERTO → INTEGRADO → DESPLEGADO → VERIFICADO; también BLOQUEADO y CANCELADO.
10. Actualizar evidencia verificable de resultado y siguiente responsable al cerrar la sesión.

Para evitar conflictos en registros escritos por muchos chats, preferir Issues/PR por tarea y cambios documentales independientes en sus propias ramas; evitar ediciones simultáneas directas del mismo archivo.
