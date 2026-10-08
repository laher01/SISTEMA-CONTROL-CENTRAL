# Implementación incremental: selección de espacio y control de Secretaría

Esta entrega habilita la selección del tenant por su **nombre único existente** en el inicio de sesión, manteniendo compatibilidad con el espacio predeterminado cuando se omite. Es una medida de transición: **todavía NO crea un código AL001-1 independiente**, ni provisiona 100 Administraciones. No revela nombres de tenants mediante un buscador público. En la siguiente fase se implementará código corto único con migración y alta administrada.

Secretaría, Administración y Superadministración pueden utilizar `GET /api/v1/dashboard/secretaria-clientes?desde=AAAA-MM-DD&hasta=AAAA-MM-DD` para consultar expedientes por Cliente/Receptor, moneda, periodo e importe. No constituye crédito fiscal validado: todavía requiere validación SUNAT, deduplicación y controles tributarios. Gerencia, Usuario y Gestor no pueden invocar esta ruta.

Pendientes antes del alcance completo: interfaz de tablero para Secretaría, clasificación tributaria validada, Responsable->Usuarios->Gestores y jerarquía de pedidos, identidad pública codificada por tenant, alta y administración de tenants, pruebas cruzadas de autorización y datos reales. Nunca inferir el tenant desde un RUC de cliente.
