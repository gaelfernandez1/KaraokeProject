# 002 · Contratos v0: dónde viven y cómo cambian

- **Fecha**: 28/10/2026
- **Estado**: aceptada (C1)
- **Afecta a**: C3, C4, C5, C6, C7, C8 (todo el que lea o escriba `karaoke.json` o temas)

## Decisión

- **Fuente de verdad**: los modelos pydantic de `packages/contracts/src/karaoke_contracts/`
  (`doc.py` para `karaoke.json`, `theme.py` para el tema). De ahí salen:
  - `schemas/karaoke.schema.json` y `schemas/theme.schema.json` (JSON Schema 2020-12, modo
    serialización: los campos con valor por defecto salen como obligatorios, porque siempre se
    escriben);
  - `web/src/lib/contracts/generated/*.ts` (json-schema-to-typescript, sin alias por campo y sin
    tuplas de mínimo de elementos).

  `make contracts` regenera los dos; un test de Python y la CI fallan si lo versionado no coincide.
- **Reglas que el schema no expresa**, en `validate_doc` / `validate_package`:
  - todo tramo con `end ≥ start`;
  - palabras dentro de su línea y partes dentro de su palabra, en orden;
  - las partes, juntas, escriben la palabra exacta;
  - las líneas pueden solaparse (dúos), pero empiezan en orden;
  - todo dentro de `duration`;
  - ids únicos y cantantes que existen;
  - medios con ruta relativa dentro del paquete y que existen.

  Tolerancia de 1 ms (`TIME_EPS`).
- **Versionado**: `schema_version` semver con major 1. Los campos desconocidos se **conservan**
  (`extra="allow"`): una versión menor nueva carga en un consumidor viejo y, si este la guarda, no
  pierde nada. Un major 2 se rechaza. `Infinity` y `NaN` se rechazan. mypy (plugin de pydantic con
  `init_forbid_extra`) sigue cazando erratas en los argumentos al construir modelos.
- **Rutas de medios**: `resolve_media(paquete, ref)` es la única comprobación de rutas (resuelve
  enlaces simbólicos); la usan el validador y quien escriba medios en un paquete.
- **Texto**: `text` lleva la ortografía original (también reintegracionista o dialectal) con la
  puntuación pegada; si hay `parts`, la puntuación va en la última parte. JSON en UTF-8 sin escapes
  (`dump_doc`).
- **Reloj web**: `PlaybackClock { now(): number }` en `web/src/lib/contracts/clock.ts`: segundos
  del audio con la latencia ya compensada.
- **Pasos del motor**: protocolos `Separator`, `Transcriber`, `Segmenter` y `Aligner` en
  `karaoke_engine.steps`; los alineadores devuelven `Line` del contrato.
- **Ejemplos**: `fixtures/packages/demo-sintetico/` (canción gallega inventada, 32 s, sílabas, dos
  cantantes, hueco instrumental de 7,5 s) y `fixtures/themes/basico.json`. `uv run karaoke demo`
  genera su audio: la voz pita exactamente en cada sílaba.

## Consecuencias

- Cambiar un contrato = editar el modelo + `make contracts` + tests + una decisión si afecta a
  otros, en el mismo PR.
- Los consumidores TS confían en que el servidor valida; si la web necesita validar en el
  navegador, puede usar el JSON Schema (p. ej. con ajv).
