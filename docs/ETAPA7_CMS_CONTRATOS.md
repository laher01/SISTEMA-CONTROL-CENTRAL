# ETAPA 7 — Contrato de implementación (sin despliegue)
Fecha: 2026-10-15
Estado: PROPUESTO / rama independiente
Responsable lógico: chat Etapa 7
Fuente de verdad operativa: main + PRs + CI + versión VPS, no este documento.

## Invariantes
- `https://app.nexomarnegocioseirl.online/` muestra login sin sesión; `/ingresar` login alternativo; `/bienvenida` landing.
- `nexomarnegocioseirl.online` sirve portal comercial en VPS antigua; fragmentos #inicio, #precios y #registro son secciones client-side.
- `factcentral.online` está RESERVADO: no modificar DNS, Nginx, OAuth, routing ni redirecciones referentes a este dominio en Etapa 7.
- `/privacidad` y `/terminos` permanecen accesibles públicamente; no afirmar que #privacidad/#terminos están implementados en website/index.html.
- No tocar ni invalidar OAuth de Gmail/Outlook, credenciales, tokens, sesiones, datos operativos de tenants.
- No fusionar ni desplegar sin pruebas, respaldo adecuado, autorización y comprobación de SHA en VPS.

## Inventario verificado (main 104509d8)
- React/TypeScript/Vite: frontend/src/App.tsx, frontend/src/paginas/Presentacion.tsx.
- Páginas legales: frontend/src/paginas/PaginasPublicas.tsx.
- NEXUS: frontend/src/componentes/NexusFlotante.tsx; backend/app/api/routes/nexus.py; backend/app/services/nexus.py.
- Autorización operativa de SUPERADMIN: backend/app/api/deps.py. No reutilizar OperativeAuthDep sin revisión: restringe el alcance de SUPERADMIN.
- Frontend del portal estático: website/index.html; nginx: deploy/nginx.conf.
- Despliegue manual: .github/workflows/deploy-staging.yml (no push automático); CI antes de deploy.
- PR #213 propone Centro de Coordinación: respetar ese trabajo y no replicar AGENTS.md/docs/COORDINACION.

## Diseño incremental (PR separados)
1. **Fase B — Landing**: definir contrato de secciones y renderer compatible con Presentacion; pruebas de /, /ingresar, /bienvenida y páginas legales. Preservar rutas.
2. **Fase C — CMS**: esquema mínimo PostgreSQL de contenido de sitio, secciones, revisiones, estado borrador/publicado y auditoría; migración Alembic encadenada al head vigente, no a revision asumida.
3. **Fase D — Precios/medios**: planes como catálogo informativo sin cobro; carga de archivos validada (tipo real, tamaño, permisos, antivirus si aplica, sin rutas arbitrarias), consentimiento de testimonios.
4. **Fase E — NEXUS**: endpoint administrativo de propuestas textuales estructuradas; entradas autorizadas; no acceso a datos operativos ni publicación por IA.
5. **Fase F — Aprobación**: editor -> vista previa no pública -> revisor autorizado -> publicación versionada transaccional -> rollback auditado.
6. **Fase G — Pruebas**: matrices de acceso (anónimo, SUPERADMIN, ADMINISTRADOR, roles operativos), aislamiento tenant, sanitización, rechazo de acceso público a borradores, regresión OAuth y login.
7. **Fase H — Entrega**: CI verde + PR aprobado; respaldo y verificación staging; despliegue manual main con confirmación de commit y salud; prueba de rutas reales.

## Seguridad multi-tenant y rol global
El CMS de marca FACT CENTRAL debe ser global por defecto y aislado de expedientes de tenants. Una dependencia administrativa dedicada evaluará permisos reales, sin ampliar lectura cross-tenant. La publicación pública expone SOLO una versión aprobada del contenido; borradores y archivos no aprobados son privados.

## Gestión de dominios (dependencia)
Panel SUPERADMIN “Infraestructura → Dominios y Cloudflare”, a coordinar con propietario de arquitectura SaaS. Separar DNS administrado por Cloudflare de rutas HTTP/Nginx/SPA; consultas read-only primero, mutaciones auditadas y con permisos restringidos después. Evitar almacenar tokens Cloudflare en PostgreSQL sin protección o en Git. No tocar dominio reservado `factcentral.online`.

## Pruebas exigidas antes de cada merge
`backend: uv sync --locked; uv run ruff check .; uv run ruff format --check .; uv run mypy app; uv run pytest`
`frontend: npm ci; npm run lint; npm run typecheck; npm test; npm run build`
Las pruebas deben ejecutarse en CI, no inferirse por documentos.

## Estado y dependencias
- ET7-001: contratos y alcance (este PR): EN PR / sin despliegue.
- ET7-002: renderer y navegación comercial: PROPUESTO.
- ET7-003: CMS persistente + auditoría: PROPUESTO.
- ET7-004: medios y planes: PROPUESTO.
- ET7-005: propuestas NEXUS: PROPUESTO.
- ET7-006: preview, aprobación, publicación: PROPUESTO.
- ET7-007: regresión, seguridad, despliegue: PROPUESTO.
- Centro de Coordinación: PR #213 / verificar estado antes de añadir registros.
