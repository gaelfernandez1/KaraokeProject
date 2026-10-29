# 003 · Banco de pruebas, línea base y metas de v3

- **Fecha**: 29/10/2026
- **Estado**: propuesta (área C2); se aprueba con su PR
- **Afecta a**: C3, C4 (eligen modelos con estas metas), C5, C7, C8 (velocidad y memoria)

## Contexto

`00-vision.md` §1 tenía metas provisionales para que C2 las fijara tras medir. El banco
(`docs/banco.md`) mide dos líneas base hechas con librerías actuales:

- **`base-legacy`**: lo que hacía el sistema v2. Demucs, Whisper `small` adivinando el idioma y
  alineación CTC con los modelos por defecto.
- **`base-turbo`**: lo mismo con Whisper `large-v3-turbo` y el idioma dado.

Las mediciones son de la RTX 3050 de 4 GB (commit `2244468`) e incluyen:

- las 79 canciones de JamendoLyrics (en, es, fr, de), con tiempos por palabra hechos a mano;
- las 5 gallegas del banco, todavía sin validar de oído.

Informes en `bench/results/2026-10-29-*`.

## Cifras

| | `base-turbo` | `base-legacy` |
|---|---|---|
| Con letra: error de inicio, mediana / media | 0,034 / 0,142 s | igual (mismos pasos) |
| Con letra: palabras a ≤ 0,3 s (en / es / fr / de) | 97,0 % (93,8 / 98,3 / 97,0 / 99,1) | igual |
| Sin letra: WER jamendo | 33,7 % | 38,2 % y 10 canciones fallidas |
| Sin letra: WER gallego (2 canciones con letra publicada, 690 palabras) | 35,9 % | 84,1 % |
| Cambios de idioma (jamendo / gallego) | 0 / 0 | 13 de 79 / 5 de 5 |
| Canción de 4 min, sin contar cargas (con letra / sin letra) | 22 / 40 s | — / 36 s |
| VRAM pico por paso (separar / transcribir / alinear) | 0,8 / 1,3 / 1,6 GB | — / 0,8 / 1,6 GB |
| RAM pico del alineador | 4,6 GB | 5,9 GB |

`base-legacy` confunde el gallego con noruego, coreano, latín y castellano, y en jamendo con
noruego, galés, latín y sueco. Cuando no hay alineador para el idioma inventado, la canción
falla. Es el cambio silencioso de idioma que v3 quiere eliminar.

La cobertura con letra (93,6 %) coincide con el techo de emparejamiento entre el texto de Jam-ALT y
las palabras de JamendoLyrics, así que la sincronía no pierde palabras.

## Ruido

Para medirlo, se repitió `base-turbo` en el conjunto `quick` (20 canciones) recalculándolo todo:

- **Con letra:** sale idéntico. Demucs lleva semilla fija y el alineador CTC es determinista.
- **Sin letra**, Whisper varía entre ejecuciones:
  - WER total: ±1,1 puntos;
  - WER por idioma: hasta ±5,6 puntos;
  - WER por canción: hasta ±22 puntos;
  - % ≤ 0,3 s: ±0,7 puntos en total y hasta ±6 por idioma.
- **Tiempo estimado** de una canción de 4 min: ±2 s.

Una diferencia menor que esto no es una mejora. En modo sin letra se comparan los totales, no las
canciones sueltas.

## Decisión: metas de v3

Las provisionales se cumplen de sobra, así que se endurecen. Como la línea base ya va bien, las
metas obligan a no empeorar con modelos más pesados y a mejorar donde flojea: el inglés, la
media (las líneas que se van lejos) y el gallego sin letra.

| Qué | Meta |
|---|---|
| Sincronía con letra (JamendoLyrics, 79) | mediana ≤ 0,03 s, media ≤ 0,10 s y ≥ 98 % de palabras a ≤ 0,3 s; ningún idioma por debajo del 96 % |
| Sincronía con letra (gallego validado de oído) | ≥ 95 % a ≤ 0,3 s y nunca por debajo de `base-turbo` (la referencia es fiable a ±0,1 s, así que manda el %) |
| Transcripción sin letra (gallego validado) | WER ≤ 0,7 × el de `base-turbo` en el mismo conjunto (hoy, 35,9 % → ≤ 25 %) |
| Transcripción sin letra (JamendoLyrics) | WER ≤ 30 % (hoy 33,7 %) |
| Idioma | 0 cambios silenciosos en todo el banco; si el usuario no da idioma, se detecta y se dice |
| Velocidad | canción de 4 min lista en ≤ 2 min con letra o sin ella, contando la carga de modelos (sin la primera descarga) |
| Memoria | cada paso ≤ 3 GB de VRAM (Windows usa ~1 GB) y ≤ 4 GB de RAM |

Lo demás de `00-vision.md` §1 sigue igual: reproductor, corrección y MP4 de 4 min en ≤ 1 min.

## Consecuencias

- `00-vision.md` §1 pasa a estas metas.
- C3 y C4 prueban cada cambio con `karaoke-bench` y `compare` contra `base-turbo`.
- La sincronía y el WER gallegos quedan provisionales hasta que el usuario valide las 5 referencias. Entonces se repite `run --set gl --mode both`, que solo cuesta unos minutos porque todo está en caché, y se apuntan aquí las cifras.
- El alineador de la línea base pasa de 4 GB de RAM (5,9 GB con `base-legacy`). Es un riesgo con los 7,6 GB que ve WSL: C4 debe bajarlo.
- Para que comparar sin letra sea más fiable, conviene fijar la semilla del transcriptor (`ctranslate2.set_random_seed`) en la versión de C4.
