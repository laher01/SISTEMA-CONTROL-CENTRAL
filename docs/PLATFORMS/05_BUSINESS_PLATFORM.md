# 05_BUSINESS_PLATFORM

## Objetivo

Gestionar toda la estructura empresarial de FACT CENTRAL bajo un modelo
SaaS multiempresa.

## Entidades Principales

-   Empresas
-   Clientes
-   Proveedores
-   Emisores
-   Receptores
-   Gestores
-   Usuarios
-   Sucursales

## Funcionalidades

-   Alta y baja de empresas
-   Gestión de relaciones comerciales
-   Asignación de gestores
-   Control de estados
-   Historial empresarial
-   Validaciones SUNAT

## Arquitectura

Business Platform ├─ Company Engine ├─ Customer Engine ├─ Supplier
Engine ├─ Relationship Engine └─ Business Intelligence Connector

## Reglas

-   Un RUC es único.
-   Toda empresa pertenece a un Tenant.
-   Toda modificación queda auditada.

## APIs

POST /companies GET /companies PUT /companies/{id} GET /business/search

## Integraciones

-   Accounting Platform
-   Expedient Platform
-   Dashboard Platform
-   AI Platform

## Estado

Versión 1.0 Estado: En Auditoría
