# FACT CENTRAL Android — versión de pruebas 0.2.1
Cliente nativo Java, conexión HTTPS a app.nexomarnegocioseirl.online y sesión temporal en memoria. No incluye credenciales, acceso SQL, ni almacenamiento persistente de comprobantes. Roles y permisos de Secretaría se consultan en servidor; SUPERADMIN únicamente muestra información de cuenta. La API sigue siendo la autoridad final.

La API del dominio configurado devolvió HTTP 401 sin sesión en `/api/v1/auth/me` y HTTP 200 en `/api/v1/auth/administracion-publica` según comprobación de la VPS. Falta una prueba autenticada desde Android. No cambiar la URL sin verificar tenant, autenticación y certificados.\n\nAlcance inicial: revisión agregada SUNAT de solo lectura, consulta de alertas, inicio de sesión, cierre de sesión, resumen, listas de documentos y expedientes según rol, navegación móvil. Incluye carga de archivos solo para Gestor, detalle y previsualización de retirada para roles autorizados, panel de control y portal web integrado para visualizar cambios publicados sin reinstalar APK. Pendientes: escáner/cámara, descarga nativa, notificaciones push, paginación avanzada, solicitudes MISD desde móvil y prueba autenticada de carga/retirada en dispositivo. No es una versión de producción.

Compilar: JDK 17, Android SDK 35, Gradle 8.9; `gradle -p android testDebugUnitTest lintDebug assembleDebug`. El workflow del PR no despliega ni utiliza secretos. El APK de depuración está destinado a pruebas; la firma de producción requiere configuración independiente.

## Resultado de auditoría Android

- Dashboard: `DashboardResumen.montos` expone `bancarizable` y `no_bancarizable` por moneda; no existe el campo `total`. Se muestran ambos valores por separado para no alterar fórmulas.
- Portal web: utiliza sesión WebView independiente de la sesión nativa. Puede pedir iniciar sesión nuevamente. La opción cerrar sesión limpia cookies y almacenamiento web de la app.
- VersionCode: 2. Las APK debug del CI fueron firmadas con certificados distintos. No se pueden actualizar entre sí sin desinstalar. La firma estable de producción requiere un keystore privado fuera del repositorio y manejo protegido de secretos; no se incorporó una clave de producción.
- Sin credenciales de prueba no se ha validado una carga autenticada ni retirada real. No probar borrados sobre documentos fiscales reales.
