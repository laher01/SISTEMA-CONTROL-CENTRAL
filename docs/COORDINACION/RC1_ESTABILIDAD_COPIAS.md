# RC-1: control offline de estabilidad de copias

El módulo `deploy/check_quiescence_offline.py` calcula SHA-256 y listado completo de archivos en dos lecturas y comprueba que el dump no varíe. Detecta alteraciones evidentes en una **copia aislada**, pero no implementa una barrera transaccional de escritura: un escritor puede modificar y restaurar bytes entre ambas observaciones.

Uso para pruebas de copias desconectadas:
```python
from pathlib import Path
from deploy.check_quiescence_offline import verificar_estabilidad
assert verificar_estabilidad(Path("/aislado/documentos"), Path("/aislado/postgres.dump"), 2)
```

**No utilizar este control para afirmar que PostgreSQL y documentos son un snapshot consistente.** Primero se necesita detener o cercar todos los procesos con acceso de escritura, registrar la aceptación operativa, generar copia coordinada y restaurarla en entorno aislado. El control no se instala en la VPS ni modifica la estrategia de despliegue. Quedan pendientes cifrado y custodia fuera del servidor, además de demostrar barrera efectiva para API, trabajadores y otros escritores.
