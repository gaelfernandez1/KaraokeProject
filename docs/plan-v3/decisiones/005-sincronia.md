# 005 · Sincronía con letra: alineador nuevo, modelos y cómo se mide

- **Fecha**: 29/10/2026
- **Estado**: propuesta (área C4); se aprueba con su PR
- **Afecta a**: C5 y C7 (líneas de coro y confianza por palabra), C8 (memoria y tiempo del
  servidor), C2 (cambios en el banco)

## Contexto

Las canciones que más se cantarán son gallegas actuales sacadas de YouTube: rap y trap, voces
superpuestas, coros, adlibs, pausas instrumentales, habla con gheada y seseo. La letra viene de webs
de letras, que la escriben para leerla: cabeceras (`[Estribillo]`, `[Verso 1: Ana]`), `x2`,
estribillos que solo se nombran, coros entre paréntesis, líneas que faltan o sobran.

La línea base (`base-turbo`, `sep-melkim-8s`) usa una alineación CTC clásica: debe explicar cada
tramo del audio con la letra o con un blanco. Por eso pega lo que no está en la letra a la palabra
más cercana, mete a la fuerza las líneas que no se cantan y estira palabras sobre los
instrumentales.

## Cómo se comprobó sin medir a mano

| Conjunto | Qué es | Para qué |
|---|---|---|
| `jamendo` (79) y `quick` (20) | tiempos por palabra hechos a mano (JamendoLyrics) | la meta de `decisiones/003` |
| `stress` (24, nuevo) | canciones de `quick` con instrumentales de 30 s insertados, adlibs, ecos, letra «de web» y líneas que faltan o sobran; los tiempos exactos se desplazan con cada cambio | robustez, por tipo de problema |
| `private` (local) | 2 canciones gallegas de rap con tiempos aproximados hechos a mano en un subtítulo (`import-srt`), una de ellas también con la letra completa de LRCLIB sobre un recorte de 27 s | el caso real; sus informes no se versionan |
| `gl` (5) | canciones gallegas con licencia libre; referencias validadas solas donde coinciden tres alineadores independientes (`triangulate`) | gallego sin escuchar cada línea |
| sin referencia | parte del tiempo de palabra en la que la voz separada calla y parte de palabras con confianza < 0,3 | cualquier canción |

## Decisión

**Alineador**: `karaoke_engine.align.aligner:LyricsAligner` (`docs/sincronia.md`), en
`bench/pipelines/c4-default.toml`, después del separador de `decisiones/004`. Hace esto:

- lee la letra como se pega: cabeceras, cantantes, repeticiones, estribillos nombrados y coros
  entre paréntesis como líneas aparte, marcadas `role: "backing"`;
- pasa números y símbolos a palabras en gallego, castellano, portugués e inglés;
- busca el camino CTC con un **relleno entre líneas** que explica lo que no está en la letra (3
  por tramo);
- puede **saltarse una línea** pagando 6 por letra (un coro, 4);
- **cobra 4 por cada letra**, y por cada blanco dentro de una palabra, donde la voz calla;
- termina cada palabra en la primera pausa de más de 0,3 s.

Lo que se probó y no entra por defecto:

| Prueba | Por qué no entra |
|---|---|
| Coste fijo por línea saltada | premiaba meter muchas líneas cortas en el rap en vez de las largas que se cantan: con la letra completa sobre el recorte, 33 % a ≤ 0,3 s y 38 % de cobertura, frente a 73 % y 94 % con coste por letra |
| Saltos baratos al principio o al final de la letra | ayudan con recortes (78 % frente a 73 %), pero en canciones enteras llegaron a tirar media canción |
| Mover el inicio de cada palabra al arranque de la voz | empeora JamendoLyrics, cuyos inicios siguen la vocal |

**Barrido** sobre `quick` y `stress` (≤ 0,3 s · error medio · cobertura). Los informes del barrido
quedan en local; esta tabla los resume:

| Variante | quick | stress |
|---|---|---|
| `sep-melkim-8s` (línea base) | 98,5 % · 0,104 s · 94,8 % | 98,0 % · 0,124 s · 94,7 % |
| primera versión (salto 40 por línea, coro 5, inicios a la voz) | 97,7 % · 0,088 s · 91,4 % | 97,6 % · 0,125 s · 91,3 % |
| salto 200 por línea, coro 60, sin mover inicios | 98,9 % · 0,066 s · 94,2 % | 98,7 % · 0,071 s · 94,1 % |
| salto 6 por letra, coro 4, bordes a 3 | 99,0 % · 0,072 s · 94,0 % | 98,8 % · 0,076 s · 94,2 % |
| **elegida** (la anterior sin bordes y con el modelo inglés grande) | **99,3 % · 0,064 s · 94,1 %** | **99,2 % · 0,068 s · 94,2 %** |

Un error de la primera versión que destapó el aviso «fuera de voz»: el blanco entre las dos e de
«Meer» esperó gratis 57 s de instrumental. Desde entonces, los blancos dentro de una palabra pagan
el silencio. Fuera de voz pasó del 6–7 % al 0,1 %.

**Modelos** (todos Apache-2.0 y con revisión fijada; tabla completa en `docs/sincronia.md`):

| Idioma | Modelo | Por qué |
|---|---|---|
| gallego | Nós wav2vec2 XLS-R 300M | en las 2 canciones privadas, todos los candidatos quedan a ±2 palabras de 100: Nós XLS-R 73,4 / 79,2 %, Nós w2v-BERT 75,8 / 81,2 %, Omnilingual 1B 75,8 / 84,2 % con 79 % de cobertura, ifrz 71,0 / 77,1 %; w2v-BERT pasa de 4,6 GB de RAM y Omnilingual 1B de 6 GB |
| inglés | `facebook/wav2vec2-large-960h-lv60-self` | 97,6 % en las 20 inglesas de jamendo, frente al 95,0 % del modelo base que heredó la línea base y el 94,2 % de XLS-R inglés |
| castellano, francés, alemán, portugués | XLS-R de jonatasgrosman | los de la línea base, que ya pasan del 98 % |
| cualquier otro | Omnilingual CTC 300M | cubre unos 1600 idiomas, pero alinea peor (91,4 % en `quick`, 71 % de cobertura): solo de respaldo (anotarlo en `provenance` queda para `karaoke make`) |

## Cifras finales (`c4-default`, commit de este PR)

| | Línea base (`sep-melkim-8s`) | Nuevo | Meta (003) |
|---|---|---|---|
| jamendo (79): ≤ 0,3 s | 97,5 % | **98,8 %** | ≥ 98 % ✓ |
| jamendo: por idioma (de / en / es / fr) | 99,5 / 94,4 / 98,9 / 97,2 % | 99,4 / **97,6** / 99,5 / 98,8 % | ninguno < 96 % ✓ |
| jamendo: error de inicio, mediana / media | 0,033 / 0,136 s | 0,035 / **0,093 s** | ≤ 0,03 / ≤ 0,10 s: media ✓, mediana ✗ |
| jamendo: cobertura | 93,6 % | 92,3 % | — |
| stress (24): ≤ 0,3 s · media | 98,0 % · 0,124 s | **99,2 % · 0,068 s** | — |
| Fuera de voz (stress) | 8,8 % | 0,1 % | — |
| Canción de 4 min, con letra (con cargas) | 60 s | 59 s | ≤ 2 min ✓ |
| Alinear: VRAM pico / RAM pico | 1,6 / 4,8 GB | 1,6 / 2,7 GB con un modelo; 3,7 GB si un proceso carga cuatro idiomas seguidos | ≤ 3 / ≤ 4 GB ✓ |

- **Mediana**: no baja de 0,03 s porque el modelo inglés grande pone los inicios unos 7 ms más
  tarde. La línea base tampoco la cumplía (0,033 s); la media y el % sí mejoran.
- **Cobertura**: baja 1,3 puntos porque algunos coros entre paréntesis que se pisan con la voz
  principal no caben en un camino único y se saltan. Se resuelve en el siguiente paso (coros en
  una segunda pasada).
- **Gallego (canciones privadas, referencia aproximada)**:
  - 74 y 79 % a ≤ 0,3 s y 85 y 94 % a ≤ 0,5 s;
  - la referencia va 0,1 s por delante del alineador en todas las palabras: quien marca a mano
    se adelanta;
  - con la letra completa de LRCLIB sobre el recorte: 73 % a ≤ 0,3 s y 94 % de cobertura, frente
    al 0 % de la línea base, que mete la canción entera en 27 s.
- **Gallego (5 con licencia libre)**: 98,6 % a ≤ 0,3 s en las dos validadas, empatado con la
  línea base (sección siguiente).

## Validación automática del gallego

Los borradores de las 5 canciones gallegas con licencia libre se validaron con `triangulate`, sin
escucharlos, usando tres alineadores distintos del elegido:

- Demucs con el modelo `ifrz` (`base-turbo`);
- Kim con Nós w2v-BERT (`c4-w2vbert`);
- Kim con Omnilingual 300M (`c4-omni300`).

Una línea queda validada cuando los tres ponen cada palabra a ≤ 0,15 s de la mediana:

| Canción | Palabras validadas | Canción validada |
|---|---|---|
| Pantis, «un aire» | 76 % | sí |
| Clo Plas, «laverca» | 75 % | sí |
| Cibrán, «O mundo do motor» | 62 % | no (falta poco) |
| Mortos en Vida, «Chapapote» (punk a gritos) | 31 % | no |
| Fanny + Alexander, «Lene» | 19 % | no |

Con las dos validadas (624 palabras):

| | ≤ 0,3 s | Error medio |
|---|---|---|
| `base-turbo` | 98,7 % | 0,031 s |
| `sep-melkim-8s` | 98,7 % | 0,032 s |
| `c4-default` | 98,6 % | 0,038 s |

- La meta (≥ 95 %) se cumple.
- Frente a `base-turbo` es un empate (una palabra). Esa medida favorece a las líneas base: usan
  el mismo modelo que uno de los tres validadores, que además es uno de ellos.
- Las líneas dudosas (las únicas que alguien tendría que escuchar) las lista el comando. Las
  canciones sin validar siguen fuera de la sincronía.

## Consecuencias

- Banco (C2):
  - el banco pasa la letra tal cual a los alineadores que la leen (`TextAligner`) y les deja
    devolver otro número de líneas;
  - conjunto `stress`;
  - `import-srt` para referencias aproximadas, con la columna ≤ 0,5 s;
  - `triangulate`;
  - `package --align`;
  - avisos sin referencia;
  - los informes de `private` van a `bench/data/results/` (no se versionan).
- C5/C7: las líneas de coro llevan `role: "backing"` (campo extra; el contrato lo formalizará con
  una versión menor cuando llegue la segunda pasada de coros). `confidence` por palabra sirve para
  marcar dudas en el editor.
- C8: alinear una canción cuesta unos 5 s y unos 2,7 GB de RAM con un modelo. Al cambiar de
  idioma, el modelo anterior se libera del todo (también la memoria del proceso): cuatro idiomas
  seguidos se quedan en 3,7 GB (antes, 4,4 GB). Los modelos se bajan una vez a la caché de Hugging
  Face.
- Pendiente en C4: coros solapados y repeticiones que la letra no dice, transcripción sin letra
  (gallego), `parts` (sílabas) y `karaoke make`.
