# FACT CENTRAL — Frontend MVP

Interfaz web mínima (Vite + React + TypeScript) para operar el backend del MVP sin usar la API a mano.

## Pantallas

- **Dashboard**: expedientes por estado, pendientes de aprobación, alertas abiertas, montos y documentos sin expediente.
- **Subir documentos**: arrastra o elige varios XML, PDF o imágenes a la vez. Muestra el resultado de cada archivo (subido, duplicado o error).
- **Expedientes**: listado con filtros por estado, aprobación y RUC receptor. El detalle muestra documentos, faltantes, alertas y fecha límite, y permite agregar documentos (voucher, retención, etc.).
- **Pendientes**: documentos que no se asociaron solos. Se elige su tipo y su expediente.
- **Alertas**: alertas abiertas o resueltas, con enlace al expediente.
- **Empresas**: marcar empresas como autorizadas o agentes de retención.

## Uso

Requiere Node 22 y el backend corriendo en `http://localhost:8000` (ver `backend/README.md`).

```bash
npm ci
npm run dev        # http://localhost:5173, con proxy de /api y /health al backend
```

- `VITE_BACKEND_PROXY`: destino del proxy en desarrollo (por defecto `http://localhost:8000`).
- `VITE_API_URL`: URL base del backend si el frontend se sirve desde otro origen (por ejemplo, tras `npm run build`). En ese caso, configura `FC_CORS_ORIGINS` en el backend.

## Calidad

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```
