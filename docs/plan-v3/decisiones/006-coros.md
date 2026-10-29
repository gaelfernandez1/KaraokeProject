# 006 · Coros en el documento de karaoke (contrato 1.1.0)

- **Fecha**: 30/10/2026
- **Estado**: propuesta (área C4); se aprueba con su PR
- **Afecta a**: C5 y C7 (pintan la letra), C6 (el MP4), C8 (guarda paquetes)

## Contexto

Las letras de las webs escriben los coros entre paréntesis, y el usuario los quiere ver aparte (entre
corchetes) de la letra principal, aunque suenen a la vez. El contrato 1.0.0 solo podía guardarlos
como líneas normales.

## Decisión

- `Line.role`: `"lead"` (por defecto) o `"backing"`. Una línea de coro puede solaparse en el tiempo
  con la principal; las líneas siguen ordenadas por inicio, como ya admitía el validador (dúos).
- `SCHEMA_VERSION` pasa a **1.1.0**. Un documento 1.0.0 sin `role` se lee con todas sus líneas como
  principales. Los paquetes de ejemplo de `fixtures/packages/` pasan a 1.1.0.
- El texto de una línea de coro va sin los paréntesis; cómo se marca en pantalla (corchetes, otro
  color, más pequeño) lo decide C5.

## Coros que se pisan con la voz principal

En una sola pasada, un coro solo puede ir antes o después de su línea principal. Se probó una
segunda pasada que alinea cada coro solo, en el tramo de su línea principal, y le deja solaparse:

| | ≤ 0,3 s (jamendo · stress · quick) | Cobertura (jamendo) |
|---|---|---|
| Una pasada (coros en su sitio escrito) | 98,8 · 99,2 · 99,3 % | 92,3 % |
| Todos los coros solos, solapables | 97,6 % en jamendo | 92,3 % |
| Solo los que no caben en su sitio, solapables | 98,5 · 98,9 · 99,0 % | 92,6 % |

En estas canciones los paréntesis son sobre todo ecos y respuestas justo después de la voz
principal, y alineados solos se pegan a las mismas palabras de la voz principal. La segunda pasada
queda como opción (`overlap_backing`), desactivada; para activarla por defecto hace falta escucharla
en canciones con coros simultáneos.

## Consecuencias

- `schemas/karaoke.schema.json` y los tipos TS se regeneran (`make contracts`); en TS, `role` es
  obligatorio porque el motor siempre lo escribe. Quien lea paquetes 1.0.0 en el navegador debe
  tratar un `role` ausente como `"lead"`.
- C5: pintar las líneas `backing` de otra forma y permitir que convivan con la línea principal.
