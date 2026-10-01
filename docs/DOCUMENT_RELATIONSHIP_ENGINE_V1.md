# Document Relationship Engine v1

## Propósito

Proponer relaciones entre un documento procesado y expedientes existentes mediante evidencia
explicable. El motor reduce la búsqueda manual, pero no realiza vinculaciones silenciosas.

## Evidencias utilizadas

| Evidencia | Puntaje |
|---|---:|
| Serie y correlativo exactos | 0.65 |
| RUC del emisor | 0.20 |
| RUC del receptor | 0.10 |
| Importe exacto | 0.05 |

Las coincidencias se buscan únicamente dentro del tenant del documento. Se retornan como máximo
10 candidatos ordenados por puntaje. Cada candidato incluye las razones concretas que produjeron
el resultado.

## Contrato

```http
GET /api/v1/documentos/{documento_id}/relaciones-sugeridas
```

## Invariantes

- El motor nunca vincula automáticamente.
- El documento conserva su estado hasta que el usuario confirma.
- Ningún candidato de otro tenant puede participar.
- Un puntaje es una sugerencia explicable, no una validación tributaria.
- La vinculación confirmada continúa usando el contrato existente y queda auditada.
