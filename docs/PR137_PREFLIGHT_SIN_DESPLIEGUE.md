# Preparación de integración documental — PR #137

Estado: listo para revisión de integración; **NO fusionar ni desplegar sin nueva orden del propietario**.

## Validación confirmada
- Commit validado: `ddfd17d378cbefc361b2404d50af3edf10545722`.
- GitHub Actions completó correctamente cinco workflows: backend, frontend, recepción-documental-ci, roles-browser-isolated, roles-real-integration.
- Se corrigió el reprocesamiento forzado para que no reutilice una extracción OCR obsoleta. La prueba regresiva `test_reprocesamiento_forzado_omite_cache` forma parte del conjunto aprobado.
- Captura de cámara y selección múltiple añadidas a la interfaz. **No incluye todavía** detector de bordes, corrección de perspectiva ni generación de PDF multipágina.

## Protección de trabajos paralelos
En la revisión del 11/10/2026, `main` estaba 1 commit por delante y esta rama 16 commits por delante del ancestro común. El cambio paralelo en `main` modifica también `backend/app/api/routes/documentos.py` (jerarquía documental), entre otros archivos.

**No resolver conflictos reemplazando el archivo completo.** Antes de integrar:
1. Volver a comparar `main` y esta rama para identificar el SHA actual y cambios de otros PR.
2. Realizar una integración de prueba en rama nueva o staging, conservando tanto la llamada `procesar_con_cache(...)` y el reprocesamiento `forzar_cache`, como el import/uso de `nombres_jerarquia` que existe en `main`.
3. Ejecutar nuevamente CI completo sobre el resultado combinado. Probar el acceso por tenant y jerarquía, cargas repetidas, procesamiento forzado, eliminación, paquetes PDF y fechas.
4. Verificar los scripts existentes de actualización, backup PostgreSQL y healthcheck `127.0.0.1:18080/health`, y que haya capacidad/credenciales de VPS. No asumir que un deploy automático está instalado ni activo.
5. Solicitar orden explícita antes de fusionar a `main`, ejecutar acciones de producción o desplegar en VPS.

## Alcance pendiente
- Escáner inteligente: bordes, perspectiva y PDF multipágina con pruebas reales.
- Ingesta por correo: integración separada, no incluida en este PR.
- WhatsApp/Telegram: futuros adaptadores, sin configurar ni activar.
- Caché: monitorización de ocupación y política de expiración/limpieza por tenant antes de despliegue a gran escala.

La aprobación de CI demuestra compatibilidad con la base de esta rama, **no garantiza** una integración limpia con el `main` divergente ni que la VPS haya sido actualizada.
