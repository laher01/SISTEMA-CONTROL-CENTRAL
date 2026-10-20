# RC-1 — Protocolo de exclusión cooperativa (solo entorno aislado)

`deploy/rc1_cooperative_write_fence.py` utiliza `flock` de Linux. Escritores que participan toman lock compartido durante escrituras; captura toma lock exclusivo. Los ensayos verifican que ambos no se solapen.

**No es todavía una barrera productiva:** `flock` es cooperativo; el backend FastAPI, los trabajadores, los accesos PostgreSQL, procesos externos y scripts existentes no participan aún. Tampoco congela transacciones PostgreSQL ni garantiza una instantánea DB/documentos.

Para implementar barrera real, identificar todos los escritores y puntos de entrada, adoptar el candado en cada vía de escritura, drenar tareas/tx en curso, bloquear nuevos escritores, capturar dump y volumen bajo el mismo lock y probar con concurrencia de procesos y restauración integral. Mantener esta implementación solo en fixtures aislados hasta disponer de pruebas de todos los caminos y autorización operacional.
