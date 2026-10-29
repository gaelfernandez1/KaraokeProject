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

## Consecuencias

- `schemas/karaoke.schema.json` y los tipos TS se regeneran (`make contracts`); en TS, `role` es
  obligatorio porque el motor siempre lo escribe. Quien lea paquetes 1.0.0 en el navegador debe
  tratar un `role` ausente como `"lead"`.
- C5: pintar las líneas `backing` de otra forma y permitir que convivan con la línea principal.
