# Arquitectura SaaS — principios de coordinación

FACT CENTRAL es una plataforma SaaS multi-tenant, no un ERP independiente.

FACT CENTRAL SaaS → SUPERADMIN → TENANTS AISLADOS → ADMINISTRADOR PROPIETARIO → GERENCIA / SECRETARÍA / RESPONSABLES → USUARIOS → GESTORES.

- Cada tenant tiene datos, configuraciones, documentos y operaciones propios.
- Códigos como `ADMIN01` pueden repetirse entre tenants diferentes sin mezclar identidades.
- La identidad del tenant se valida en backend; todo acceso operativo queda limitado a su tenant.
- SUPERADMIN tiene identidad independiente y únicamente consulta autorizada de datos operativos en modo solo lectura.
- No iniciar sesión como propietario de otro tenant, transferir datos entre tenants o exponer credenciales.
- Cualquier cambio que afecte estas reglas necesita pruebas de aislamiento y autorización específica.

Esta página expresa reglas objetivo, **no certifica** que todas las funciones estén ya implementadas.
