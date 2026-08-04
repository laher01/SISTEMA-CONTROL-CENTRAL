# 01_AUTH_PLATFORM

## Objetivo

Definir la plataforma de autenticación y autorización de FACT CENTRAL.

## Alcance

-   Registro de usuarios
-   Inicio de sesión
-   Recuperación de contraseña
-   MFA
-   Gestión de sesiones
-   Roles y permisos
-   Multiempresa (Tenant)

## Componentes

-   Authentication Service
-   Authorization Service
-   Session Manager
-   Token Manager
-   MFA Engine
-   Audit Engine

## Flujo General

1.  Registro
2.  Validación de correo
3.  Activación por Administrador
4.  Inicio de sesión
5.  Emisión de JWT
6.  Validación de permisos
7.  Registro de auditoría

## Roles

-   Super Administrador
-   Administrador
-   Supervisor
-   Gestor
-   Secretaria
-   Consulta

## Seguridad

-   JWT
-   Refresh Token
-   BCrypt
-   MFA
-   Bloqueo por intentos
-   Auditoría completa

## Integraciones

-   SaaS
-   AI
-   Notification Engine
-   Permission Engine

## APIs

-   POST /auth/login
-   POST /auth/register
-   POST /auth/logout
-   POST /auth/refresh
-   POST /auth/reset-password

## Roadmap

-   OAuth2
-   SSO
-   Passkeys

## Estado

Versión: 1.0 Estado: En Auditoría
