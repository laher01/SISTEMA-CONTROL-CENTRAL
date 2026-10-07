# 24_NEXUS_FLOATING_ASSISTANT.md

# FACT CENTRAL — Asistente Flotante NEXUS

## Objetivo

NEXUS es la capa conversacional contextual de FACT CENTRAL. Debe estar disponible desde cualquier pantalla y trabajar sobre la sesión, el rol y el recurso actualmente visible.

No reemplaza PostgreSQL ni el motor de reglas. Consulta, explica y recomienda. Toda modificación crítica deberá pasar por APIs autorizadas y auditables.

## Contexto automático

El frontend envía ruta actual, expediente actual cuando corresponda y sesión autenticada. El backend deriva tenant, Usuario y Gestor exclusivamente desde la sesión.

## Capacidades internas

NEXUS puede revisar faltantes de un expediente, explicar reglas documentales, consultar RUC y razón social registrados, calcular compras del mes dentro del ámbito permitido y auditar cada consulta.

## Integraciones externas

Las integraciones no deben contener secretos en código. Se configuran mediante variables de entorno:

- FC_NEXUS_RUC_URL_TEMPLATE
- FC_NEXUS_RUC_TOKEN
- FC_NEXUS_SEARCH_URL
- FC_NEXUS_SEARCH_TOKEN
- FC_NEXUS_EXTERNAL_TIMEOUT_SECONDS

FC_NEXUS_RUC_URL_TEMPLATE deberá incluir {ruc}.

La integración de búsqueda recibe POST JSON con query, preferred_domains=[sunat.gob.pe] y language=es. Puede responder answer y sources con title/url.

## Fuente oficial y reglas

Para consultas tributarias, NEXUS prioriza sunat.gob.pe.

Una respuesta obtenida por Internet no modifica por sí sola reglas de bancarización, documentos obligatorios, datos fiscales, estados de expedientes ni configuración tributaria. Los cambios de reglas deberán ser revisados y aprobados antes de incorporarse al motor de reglas.

## Seguridad

- El asistente respeta RBAC y ownership.
- Gestor solo consulta sus expedientes.
- Usuario solo consulta su ámbito.
- La sesión determina la propiedad.
- Las consultas se auditan.
- Las integraciones externas tienen timeout.
- Ninguna credencial externa se expone al frontend.
- Si no hay proveedor externo configurado, NEXUS lo informa y no simula haber consultado Internet.

## Interfaz

El botón flotante NEXUS se mantiene visible en toda la aplicación autenticada. En un expediente ofrece acciones rápidas para revisar faltantes, verificar RUC y revisar la factura. Fuera de un expediente ofrece total de compras del mes, búsqueda de actualización SUNAT y ayuda.

## Regla principal

NEXUS debe distinguir siempre entre información local de FACT CENTRAL, información obtenida por una integración externa e inferencias o recomendaciones.