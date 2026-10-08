# Mejoras transversales: filtros, expedientes, duplicados y mensajería (08/10/2026)

## Objetivo y criterio de aceptación
En Registros, Documentos y Expedientes ofrecer búsqueda coherente por tipo A/B del proveedor emisor, RUC emisor, RUC receptor, día, rango de emisión o carga claramente rotulado, usuario y gestor según RBAC. Ningún filtro enviado manualmente por URL puede ampliar el ámbito concedido al rol. Un gestor solo consulta sus datos; un usuario, los de sí mismo y sus gestores; administración accede dentro del tenant según permisos efectivos. Los filtros y exportaciones deben reutilizar exactamente la misma consulta autorizada.

## Modelo y reglas
- «Tipo A/B» es `Empresa.clasificacion_proveedor` del emisor, no una etiqueta del comprobante. Permitir «sin clasificar». Propagar cambios de la empresa a sus expedientes sin duplicar datos.
- Mostrar RUC bajo la razón social de emisor y receptor. En Expedientes, tipo va inmediatamente antes de Comprobante.
- Resumen global filtrado calculado en servidor, previo a paginación: registros, expedientes distintos, documentos, sumas PEN y USD por separado, nunca convertir ni sumar monedas heterogéneas. Documentos sin expediente no aportan monto sin asignación fehaciente. Evitar doble sumar múltiples evidencias de una compra. Diferenciar fecha de emisión y fecha de carga en filtros.
- Descargas: usar ZIP (compatible, abierto) como formato principal; RAR solo si se incorpora un generador con licencia y pruebas, sin prometerlo por cambiar extensión. Estructurar por expediente y nombres seguros, incluir originales de todo tipo, manifiesto verificable (RUC, serie, hash, fecha, responsable), y auditar descarga. PDF compilado: orden configurable factura, guías, voucher, cotización, otros; convertir imágenes con reglas y recursos acotados, y anexar XML/archivos no renderizables mediante manifiesto o adjuntos explicitos. Nunca omitir silenciosamente un original. Si falta capacidad de conversión, indicar PDF parcial y ofrecer ZIP completo.
- Vista previa desde las tres pantallas navega al mismo detalle/visor con ámbito autorizado. Descargas de múltiples expedientes comprueban *todos* los IDs y límites, y cancelan si alguno está fuera de ámbito. Evitar listas arbitrarias o agotamiento de memoria.

## Duplicidad
Clave comercial canónica por tenant: RUC emisor + tipo comprobante + serie normalizada + correlativo numérico normalizado (y receptor cuando legislación/contratos lo requieran). Comparar también fecha, receptor, monto, moneda y hash para detectar contradicciones, no sobreescribir. Índice único parcial para expedientes activos, protegido contra carreras concurrentes. Misma factura por otro gestor no crea nuevo expediente ni se vuelve a contabilizar; la evidencia podría ser idéntica por SHA o ser representación adicional (XML y PDF) del MISMO expediente, nunca automáticamente rechazadas por ser binariamente distintas. Procesos de rectificación, anulación y notas de crédito van en flujos expresos, no se tratan como duplicados simples.

## Privacidad del aviso duplicado
La detección opera a escala de tenant completo, pero el dato mostrado depende del rol. Administración puede conocer usuario, gestor, fecha, correlativo, monto y referencia. Un usuario o gestor que no tiene permiso de consultar ese expediente recibe aviso genérico de duplicidad y referencia de coordinación con administración, **sin revelar nombres, montos, documentos ni relaciones de otros equipos**. Si ambos expedientes quedan dentro de su ámbito, puede ver datos de propiedad y copiar aviso a WhatsApp; la función Copiar nunca envía datos por sí misma. Auditar intento y decisión de duplicidad.

## Chat interno (etapa separada)
Diseñar mensajes y adjuntos con límites, permisos por canal, aislamiento tenant y jerarquía, bloqueo de archivos activos y escaneo antivirus, cuotas, retención, auditoría y enlaces temporales. No iniciar como chat irrestricto entre todos: requiere decisiones de privacidad y acceso. Preferir notificación o solicitud de coordinación para incidencias de duplicados.

## Ruta de entrega
1. Filtros + RUC + columna A/B + pruebas backend y frontend.
2. Totales filtrados globales equivalentes en las tres pantallas.
3. Exportación ZIP completa + PDF correcto, vista previa y auditoría.
4. Duplicados comerciales + mensaje de rol seguro + prueba concurrencia.
5. Mensajería interna con reglas explícitas y pruebas de autorización.

**Criterios de liberación:** CI verde, pruebas cross-tenant, prueba Usuario/Gestor, no filtración de privacidad, respaldo previo, rollback ensayado, despliegue controlado y verificación en navegador. El paso 1 solo no implica liberar todo el alcance.
