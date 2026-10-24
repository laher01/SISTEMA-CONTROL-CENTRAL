# Diagnóstico F — HTTP 502 público en rutas de backend (2026-10-24)

## Evidencia reproducida (sin credenciales ni escrituras)

- GitHub Actions #40063854157 (SHA d78bb1): DNS OK; TLS válido al menos 7 días; GET / -> HTTP 200; GET /health -> HTTP 502.
- GitHub Actions #40063925494 (SHA 2acc45): GET / -> HTTP 200; GET /health -> HTTP 502; GET /api/v1/documentos -> HTTP 502; GET /api/v1/expedientes -> HTTP 502.
- Ambas ejecuciones del diagnóstico público fallaron como corresponde.
- Despliegue histórico #40055303532: healthy DB/backend/frontend y comprobación local http://127.0.0.1:18080/health correcta al finalizar. Esto no certifica estado actual.
- CI PR #389 aprobó pruebas aisladas, **no** acceso público.

## Trazado técnico a partir del código

- `deploy/nginx.conf`: la portada `/` se entrega como archivo estático; `/health` se proxifica a `http://backend:8000/health` y `/api/` a `http://backend:8000`.
- `deploy/docker-compose.production.yml`: frontend y backend comparten la red `fact_central_internal`; `cloudflared` depende del frontend saludable; el frontend se publica localmente en 127.0.0.1:18080.
- `backend/app/main.py`: GET `/health` devuelve `{"status":"ok"}` cuando llega al backend.

**Inferencia (no certeza):** el patrón 200 estático / 502 en TODAS las rutas de backend sugiere fallo de origen, resolución, conexión o enrutamiento del tramo proxy→backend (incluyendo ruta de túnel/reverse proxy público). Un 502 no demuestra fallo de autenticación; no certificar los permisos hasta recibir una respuesta backend coherente.

## Diagnóstico necesario antes de cualquier reparación

1. Comprobar, en modo solo lectura por ejecutor remoto autorizado, SHA efectivo y `docker compose ps` para `backend`, `frontend`, `tunnel` y `db`; no ejecutar `up`, `restart`, `pull` ni comandos mutantes.
2. Comprobar `curl -fsS http://127.0.0.1:18080/health` desde VPS para diferenciar salud local de acceso externo.
3. Desde el contenedor frontend, comprobar resolución `backend` y GET a `http://backend:8000/health`; desde backend comprobar GET a `http://127.0.0.1:8000/health`.
4. Consultar únicamente logs operativos acotados de `frontend`, `backend` y `tunnel` (redactar tokens, cookies, usuarios y contenidos fiscales).
5. Contrastar configuración real del túnel Cloudflare, dominios, rutas y origen, sin divulgar tokens. Evitar inferir configuración real a partir de código versionado.
6. Solo tras evidencias distinguir: resolución DNS interna de Docker, backend no saludable, Nginx a upstream incorrecto, ruta Cloudflare distinta, o estado transitorio.

## Criterios de aceptación para corrección futura

- HTTP 200 en / y /health públicos, TLS válido.
- /api/v1/documentos y /api/v1/expedientes responden 401/403 sin credenciales, **tras confirmar que alcanzan el backend**.
- CI, backend y frontend saludables; sin exposición de datos.
- No cambiar fórmulas económicas, migraciones, base fiscal ni despliegue por una hipótesis.
- Cualquier corrección de infraestructura debe pasar por autorización independiente (C/F para preparar, I para integrar, D para desplegar).

## Restricciones de esta investigación

No se ha accedido por SSH, reiniciado, modificado configuración de Cloudflare, fusionado ni desplegado. No existen credenciales de pruebas en este diagnóstico.
