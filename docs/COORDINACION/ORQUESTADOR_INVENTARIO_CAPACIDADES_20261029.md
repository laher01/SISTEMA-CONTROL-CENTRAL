# Orquestador — inventario inicial de capacidades

**Fecha de corte:** 2026-10-29  
**Fuente de código:** `main` SHA `6795a0dec7b870c04efa3abe2df1c10fda2e2962`.  
**Estado:** documento de auditoría para Issue #412; no es una función instalada ni un registro consultable dentro del SaaS.  
**Producción:** no se comprobó el SHA ni los datos de `132.145.233.172`; una ruta presente en `main` no demuestra que esté desplegada.

## Reglas del inventario

- **Implementado en main** significa que existe código en el SHA de corte.
- **Abierto** significa que hay PR/Issue activo; no se incorpora al inventario de producción por ese hecho.
- **Pendiente de confirmar** significa que el código disponible no acredita la regla completa o falta verificación funcional.
- Cada capacidad deberá tener un solo propietario lógico. Otras capacidades pueden consumirla a través de un contrato documentado.
- Coincidencia de nombres o rutas solo genera una revisión; el Orquestador no cambia ni elimina código por su cuenta.
- La versión futura del catálogo deberá registrar propósito, responsable, entrada/salida, rutas, tablas leídas/escritas, permisos, eventos, dependencias, evidencia y SHA.

## Capacidades visibles en el código

| ID | Capacidad y límite | Evidencia en main | Estado frente a requisitos | Propietario lógico inicial |
|---|---|---|---|---|
| FC-AUTH-01 | Inicio de sesión, sesión y contexto de acceso | `backend/app/api/routes/auth.py`, `backend/app/api/deps.py` | Implementado en main; auditar RBAC y aislamiento con cobertura real de roles | Seguridad / autenticación |
| FC-TENANT-01 | Alta y administración de tenants desde plataforma | `routes/administraciones.py`, `routes/pagina_web.py` | Implementado en main; comprobar flujo exacto de creación y provisión de administrador | SUPERADMIN / SaaS |
| FC-UPLOAD-01 | Recepción de archivos documentales | `routes/documentos.py`, `frontend/src/paginas/Subir.tsx` | **Brecha confirmada en main:** las rutas y pantalla admitían USUARIO; PR #413 propone restringir carga a GESTOR | Ingesta documental |
| FC-OCR-01 | Extracción/clasificación inicial de factura, RHE, guías y PDF/imagen | `routes/documentos.py`, servicios de procesamiento documental | Implementación parcial; exactitud de importes, caché, itemización y formatos requiere pruebas de cada proveedor | OCR / procesamiento documental |
| FC-EXP-01 | Crear expediente y asociar documentos relacionados | `routes/documentos.py`, `routes/expedientes.py`, `routes/registros.py` | Factura y RHE sirven de ancla; guías pueden iniciar referencia provisional. No se demuestra una regla general para cualquier documento relacionado que llegue antes de la factura/RHE | Expedientes |
| FC-RECEPTOR-01 | Autorizar empresas receptoras para su contabilización | `routes/empresas.py`, `models.py` | Estados de autorización existen; **PR #414 propone excluir receptores no autorizados de montos/desgloses y mostrar contador** | Empresas / control documental |
| FC-DASH-01 | Resumen y desglose financiero | `routes/dashboard.py`, `frontend/src/paginas/Dashboard.tsx` | Implementado en main; el filtro financiero de receptores no autorizados está en PR #414, aún no integrado | Dashboard |
| FC-ITEM-01 | Contabilidad estadística de ítems/productos | `routes/contabilidad_items.py`, `app/item_models.py` | Capacidad separada de los importes fiscales de facturas; el reescaneo/idempotencia debe coordinarse con PR de ítems abiertos | Contabilidad de ítems |
| FC-MISD-01 | Solicitud, autorización y retirada documental | `routes/solicitudes_retiro_misd.py`, `routes/documentos.py`, `routes/expedientes.py` | Contratos y ramas MISD siguen abiertos. La retirada lógica, purga física, recarga y retención requieren cierre conjunto; no asumir borrado completo por el estado de la UI | MISD / documentos |
| FC-ORDEN-01 | Pedidos, asignaciones, producción y comisiones | `routes/asignaciones_emisores.py`, `gerencias.py`, `produccion.py`, `comisiones.py` | Código presente; fórmulas, periodo, actor y relación muchos-a-muchos requieren validar con escenarios de negocio | Operaciones comerciales |
| FC-PAGO-01 | Pagos a usuarios, gestores y responsables | `routes/pagos.py`, `pagos_gestores.py`, `pagos_responsables.py`, `responsable.py` | Rutas distintas por nivel; contratos MISD/pagos y concurrencia siguen sujetos a PR #292 y pruebas integradas | Pagos / liquidaciones |
| FC-NEXUS-01 | Asistente contextual del tenant | `routes/nexus.py`, `routes/chat.py` | Función propia; no sustituye OCR, contabilidad de ítems, autorización ni ejecución de cambios | NEXUS |
| FC-ALERTA-01 | Alertas de documentos y atención pendiente | `routes/alertas.py`, `routes/mensajes_alerta.py` | Código presente; validar que los estados pendientes de receptor sean visibles en todos los menús previstos | Control documental |
| FC-INFRA-01 | Inventario y operación global de infraestructura | No aparece registrado en el ciclo de routers de `backend/app/main.py` de main SHA de corte | PR #61 está abierto/borrador y muy desfasado; no está instalado según main | Infraestructura / Etapa 7 |

La API registra 29 routers en el SHA consultado. El panel React también expone rutas para carga, documentos, expedientes, ítems, pedidos/pagos, empresas, alertas, NEXUS y configuración. La ruta de pantalla no acredita por sí sola que el endpoint autorice el rol correcto.

## Brechas y evidencia activa

| Frente | Evidencia consultada | Lectura de coordinación |
|---|---|---|
| Cargas solo por Gestor | PR #413, rama `fix/gestor-only-document-upload-20261029`; CI 6/6 verde para SHA `1994c2d06f8731452b989b9b892bf9d3a5a47c06` | No fusionado ni desplegado; el fix protege las tres rutas de carga y la ruta directa de UI |
| Montos de receptor pendiente | PR #414, apilado sobre #413 | Segundo CI en ejecución para el último SHA; no integrar hasta confirmar todos los checks |
| Guía de autodespliegue | Workflow `.github/workflows/deploy-staging.yml` vs `deploy/README.md`; PR #415 propone alinear documentación | El workflow está opt-in por `ORACLE_AUTO_DEPLOY_ENABLED=true`, exige `ORACLE_RECOVERY_VERIFIED=true` y restringe el destino a `ubuntu@132.145.233.172`. Aún no se verificaron los Environments/secretos del repositorio |
| DNS/túnel operativo | Dominio declarado por usuario: `app.nexomarnegocioseirl.online`; la guía tenía otro hostname | Validar Cloudflare Tunnel y el SHA real de la VPS antes de cualquier despliegue |
| Orquestador | Issue #412; protocolo maestro en `AGENTE_MAESTRO_CHATGPT_NEXUS.md` | El protocolo prohíbe asumir ejecución autónoma en segundo plano. El catálogo/runtime SUPERADMIN todavía debe diseñarse e implementarse |
| Matriz de propietarios | PR #297, borrador, rama histórica | 156 commits detrás y divergente de main en la comparación consultada; reutilizar conceptos, no fusionar esa rama como si fuese vigente |
| Infraestructura Etapa 7 | PR #61, borrador | 7 commits propios y 891 commits detrás respecto del main de corte; 40 archivos y rutas SUPERADMIN/infraestructura. Reconciliar con su propietario antes de tocar panel/modelos |

## Siguiente contrato del Orquestador

1. Versionar el catálogo con un identificador único por capacidad y referencia de evidencia al SHA.
2. Comparar capacidades, rutas, entidades de lectura/escritura, permisos y eventos; clasificar coincidencia exacta o posible solapamiento.
3. Mostrar evidencia, severidad y responsable sugerido; exigir resolución humana registrada.
4. Mantener el alcance global limitado a metadatos; la API SUPERADMIN no leerá documentos ni datos operativos de un Tenant.
5. Añadir CI en modo aviso inicial para capacidades sin propietario, IDs repetidos y contratos de ruta duplicados; endurecer el gate solo tras comprobar falsos positivos.
6. Probar RBAC, aislamiento tenant, aceptación/rechazo de hallazgos, excepciones auditadas y ausencia de mutaciones.
7. Antes de abrir la implementación runtime, coordinar propietario y archivos con Etapa 7 (#61) y actualizar las referencias #297/#302 con main vigente.

## Límites de esta revisión

Este documento registra evidencia del código y PR accesibles en GitHub, no inspecciona transcripciones privadas completas. Los estados históricos de conversación ayudan a priorizar, pero no demuestran actividad actual. No hubo SSH ni lectura autenticada de PostgreSQL en la VPS antigua, ni acceso a Cloudflare para comprobar el hostname. No se realizaron merges, despliegues, migraciones o cambios de datos.
