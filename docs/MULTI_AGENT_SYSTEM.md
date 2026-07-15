# MULTI_AGENT_SYSTEM.md

# FACT CENTRAL

## Sistema Multiagente Inteligente

---

# 1. Objetivo

Definir la arquitectura del Sistema Multiagente de FACT CENTRAL.

El ERP no utilizará un único modelo de Inteligencia Artificial.

Utilizará un conjunto de agentes especializados que colaboran entre sí para construir Expedientes inteligentes.

Cada agente tendrá una única responsabilidad.

La coordinación estará a cargo del Agente Orquestador.

---

# 2. Filosofía

Una empresa funciona porque existen especialistas.

Contabilidad.

Ventas.

Logística.

Tributación.

Administración.

FACT CENTRAL seguirá exactamente la misma filosofía.

Cada IA será especialista en una tarea.

Nunca intentará hacerlo todo.

---

# 3. Arquitectura General

```
                    USUARIO

                       │

                       ▼

               AGENTE ORQUESTADOR

                       │

 ┌─────────────┬─────────────┬─────────────┐

 ▼             ▼             ▼             ▼

OCR      DOCUMENTAL     EXPEDIENTES    AUDITOR

 │             │             │             │

 └─────────────┴──────┬──────┴─────────────┘

                      ▼

                 TRIBUTARIO

                      ▼

                   PAGOS

                      ▼

                 DASHBOARD

                      ▼

                APRENDIZAJE

                      ▼

             BASE DE CONOCIMIENTO
```

---

# 4. Agente Orquestador

## Función

Es el Director General del ERP.

No procesa documentos.

No realiza OCR.

No calcula impuestos.

Su responsabilidad consiste en decidir qué agente debe trabajar.

---

## Responsabilidades

Recibir solicitudes.

Crear tareas.

Asignar agentes.

Coordinar el flujo.

Esperar respuestas.

Resolver conflictos.

Registrar tiempos.

Administrar prioridades.

Reintentar procesos.

---

# 5. Agente OCR

Especialista en lectura documental.

Responsabilidades

Detectar orientación.

Corregir imagen.

Eliminar ruido.

OCR.

QR.

Código de barras.

Firmas.

Sellos.

---

# 6. Agente Documental

Especialista en comprender documentos.

Reconoce

Factura.

RHE.

Guía.

Voucher.

Retención.

Correo.

WhatsApp.

Cotización.

Fotografía.

---

# 7. Agente Expedientes

Es el corazón del ERP.

Responsabilidades

Crear Expedientes.

Relacionar documentos.

Completar Expedientes.

Detectar faltantes.

Actualizar estados.

Actualizar porcentajes.

Administrar el semáforo.

---

# 8. Agente Tributario

Piensa como SUNAT.

Analiza

Bancarización.

Retenciones.

Detracciones.

ITF.

Agente Retenedor.

Buen Contribuyente.

Sujeto Sin Capacidad Operativa.

Riesgos tributarios.

---

# 9. Agente Pagos

Calcula automáticamente

Producción.

Porcentajes.

Liquidaciones.

Comisiones.

Adelantos.

Pendientes.

Históricos.

---

# 10. Agente Dashboard

Especialista en indicadores.

Responde preguntas como

¿Qué sucede hoy?

¿Qué gestor produjo más?

¿Qué empresa está atrasada?

¿Qué expedientes están incompletos?

¿Qué pagos faltan?

---

# 11. Agente Auditor

Piensa como un auditor.

Detecta

Duplicados.

Fraude.

Montos anómalos.

Patrones sospechosos.

Fechas inconsistentes.

Empresas inusuales.

Documentación incompleta.

Nunca modifica información.

Solo alerta.

---

# 12. Agente Aprendizaje

Es el profesor del ERP.

Aprende de:

Correcciones.

Errores.

Nuevos formatos.

Nuevas empresas.

Nuevos productos.

Nuevas reglas.

Va construyendo una Base de Conocimiento.

---

# 13. Base de Conocimiento

Será la memoria permanente del ERP.

Almacenará

Patrones.

Empresas.

Productos.

Documentos.

Relaciones.

Correcciones.

Reglas.

Experiencias.

Mientras más años trabaje el ERP,

más inteligente será.

---

# 14. Comunicación

Los agentes nunca accederán directamente entre ellos.

Toda comunicación será realizada mediante el Agente Orquestador.

Esto evita dependencias.

---

# 15. Prioridades

Alta

OCR

Documental

Expedientes

Media

Tributario.

Pagos.

Dashboard.

Baja

Aprendizaje.

Optimización.

---

# 16. Tolerancia a Fallos

Si un agente falla,

los demás continúan trabajando.

El Orquestador registrará:

Error.

Hora.

Agente.

Documento.

Intentos.

Resultado.

---

# 17. Escalabilidad

Nuevos agentes podrán incorporarse sin modificar los existentes.

Ejemplos

Agente Inventario.

Agente Compras.

Agente Ventas.

Agente Contratos.

Agente Recursos Humanos.

Agente Producción.

---

# 18. Auditoría

Toda decisión tomada por un agente quedará registrada.

Se almacenará

Agente.

Fecha.

Hora.

Entrada.

Salida.

Nivel de confianza.

Tiempo de ejecución.

---

# 19. Seguridad

Los agentes únicamente podrán acceder a la información autorizada por el Orquestador.

Nunca accederán directamente a la Base de Datos.

Todo será mediante APIs internas.

---

# 20. Regla Suprema

FACT CENTRAL no utiliza una Inteligencia Artificial.

FACT CENTRAL utiliza un Sistema Multiagente Inteligente.

Cada agente es especialista en una única función.

Todos colaboran para construir, validar, proteger y mejorar continuamente los Expedientes Inteligentes del ERP.
