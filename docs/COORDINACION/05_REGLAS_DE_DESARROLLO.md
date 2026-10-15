# Reglas de desarrollo concurrente

1. Consultar rama `main`, archivos existentes, Issues y PR antes de empezar.
2. Comprobar responsable del módulo y posibles duplicaciones.
3. Registrar tarea y archivos previstos; comunicar previamente cambios transversales (auth, modelos, migraciones, configuración, seguridad, navegación, rutas).
4. Rama aislada creada desde `main` actualizado; PR pequeño con riesgos, pruebas y dependencias.
5. No sobrescribir trabajo concurrente ni eliminar funciones ajenas para resolver conflictos.
6. Migraciones: cadena única verificada; probar actualización y restauración en entorno desechable.
7. Seguridad: tenant aislado en backend, control de permisos y auditoría.
8. Secretos, tokens y claves fuera del repositorio, incluso si es privado.
9. Integración y despliegue solo con aprobación expresa, backups y plan de reversión.
10. Cierre de sesión: commit/PR, pruebas efectivas, pendientes, dependencias y despliegue.

Fuente de verdad para ejecución y estados: GitHub y evidencias verificables. No marcar como VERIFICADO un mero resultado CI.
