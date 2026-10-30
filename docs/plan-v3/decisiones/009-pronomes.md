# 009 · Pronombres gallegos pegados a su verbo

- **Fecha**: 30/10/2026
- **Estado**: propuesta; se aprueba con su PR
- **Afecta a**: C4 (texto de la letra), C5 y C7 (lo que se pinta), C2 (no cambia el banco)

## Contexto

El usuario, al ver sus canciones, señaló que pronombres escritos aparte como «dixo lle» o «collín
che» van en gallego pegados al verbo («díxolle», «collinche»). Las webs de letras los escriben
aparte, como en castellano. La regla de `005` era no cambiar nunca el texto mostrado.

## Decisión

- Excepción en gallego: un pronombre enclítico escrito aparte se junta a su verbo, con la
  acentuación que pide la norma, y lo demás (gheada, seseo, puntuación, mayúsculas) se queda como
  está. Se hace después de alinear (`align.clitics.join_clitics`), así que los tiempos no cambian
  y el banco, que mide el alineador, tampoco.
- Prudencia antes que cobertura: solo pronombres inequívocos, detrás de formas verbales conocidas y
  nunca tras las palabras que piden próclise. Lo que no se reconoce se queda aparte, como estaba.
- `karaoke join-clitics <paquete>` lo aplica a paquetes ya hechos.

## Consecuencias

- El reconocimiento de verbos es un léxico de verbos frecuentes con sus conjugaciones: un verbo
  raro con «che» detrás se queda sin juntar. Se puede ampliar la lista en `clitics.py`.
- La norma reintegracionista escribe el pronombre con guion («dixo-lle»): eso ya llega junto y no
  se toca.
