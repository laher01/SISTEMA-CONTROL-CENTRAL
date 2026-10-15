# Despliegues y pendientes

## Registro de estado
- PR #207: **no desplegado**. Se trabaja solo en rama aislada; CI del último commit examinado aprobado.
- Centro de coordinación: propuesta documental pendiente de revisión/merge; **no desplegado**.
- PR #183: consta fusionado y desplegado en el trabajo histórico; exigir evidencia actual del commit operativo antes de afirmar vigencia en VPS.

## Antes de desplegar
1. Autorización expresa del usuario.
2. Verificar el `main` y commit objetivo.
3. CI y pruebas de regresión.
4. Integridad de migraciones y aislamiento tenant.
5. Salud de infraestructura y respaldo recuperable.
6. Procedimiento de reversión/restore.
7. Verificación posterior del commit ejecutado, servicios y flujo funcional.

No almacenar contraseñas, tokens, SSH keys o secretos en documentación.
