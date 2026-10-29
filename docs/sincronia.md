# Sincronía de la letra (`karaoke_engine.align`)

Cómo el motor coloca cada palabra de la letra en el momento en que se canta. Las decisiones y las
cifras están en `docs/plan-v3/decisiones/005-sincronia.md`, y la forma de medir, en `docs/banco.md`.

## Qué hace

1. **Lee la letra como se pega** (`lyrics.parse_lyrics`). Las webs de letras escriben las canciones
   para leerlas, no como se cantan:
   - cabeceras como `[Estribillo]` o `[Verso 1: Ana]`: dan la sección y quién canta;
   - repeticiones (`x2`, `×3`, `(x2)`, `(bis)`, o `x2` solo en una línea para repetir la estrofa);
   - un estribillo que solo se nombra (`[Estribillo]` sin nada debajo): se repite el último que
     tenía ese nombre;
   - coros entre paréntesis: salen como líneas aparte, marcadas como coro.

   El texto que se muestra no cambia nunca, ni la gheada, ni el seseo, ni la puntuación.
2. **Pasa cada palabra a lo que se dice** (`spoken.spoken`), solo para alinear: minúsculas, sin
   puntuación, y números y símbolos en palabras en gallego, castellano, portugués e inglés
   (`2024` → «dous mil vinte e catro»; `&` → «e»).
3. **Calcula las emisiones CTC** de la voz separada con el modelo del idioma
   (`emissions.EmissionModel`). Lo hace en ventanas de 30 s con 2 s de contexto, y de la GPU solo
   salen las columnas que usa la letra.
4. **Mira dónde suena la voz** (`activity.vocal_activity`): la energía de la voz separada comparada
   con el propio canto de la canción.
5. **Busca el mejor camino** (`ctc.align_segments`), con tres libertades que la alineación CTC
   clásica no tiene:
   - un **relleno** entre líneas que explica cualquier sonido por un coste: adlibs, coros que no
     están en la letra, restos del instrumental;
   - **saltarse una línea** entera por un coste: líneas que trae la web y nadie canta;
   - **coste extra por cada letra** donde la voz calla, para que la letra no se meta en los
     instrumentales.
6. **Ajusta los finales**: una palabra acaba donde su voz se para (en la primera pausa de más de
   0,3 s), con 0,1 s de margen. Mover también los inicios al arranque de la voz
   (`refine_onsets`) está disponible, pero empeora JamendoLyrics y no va activado.

7. **Sílabas** (`syllables.syllables`, gallego, castellano y portugués): cada palabra de dos o más
   sílabas cuyas letras tienen cada una su token recibe `parts`. Cada parte empieza cuando el CTC
   pone su primera letra y acaba donde empieza la siguiente. Una palabra con números o con letras
   que el modelo no conoce se queda sin partes; el reproductor la ilumina entera.

La **confianza** de cada palabra es la media geométrica de la probabilidad CTC de sus letras. Una
palabra sin ninguna letra que el modelo conozca (un número en un idioma sin reglas, un emoji) se
queda pegada a su vecina con confianza 0. Las líneas saltadas no salen. Las de coro salen con
`role: "backing"` (campo extra hasta que el contrato lo formalice).

## Modelos

Los modelos se descargan una vez de Hugging Face a la caché local y van fijados a una revisión. El
valor por defecto de cada idioma sale del banco (decisión 005).

| Nombre | Modelo | Licencia | Uso |
|---|---|---|---|
| `nos-xlsr-300m-gl` | [proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl](https://huggingface.co/proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl) | Apache-2.0 | gallego |
| `nos-w2vbert-gl` | [proxectonos/w2v-bert-2.0-gl](https://huggingface.co/proxectonos/w2v-bert-2.0-gl) | Apache-2.0 | gallego |
| `omni-ctc-300m`, `omni-ctc-1b` | Omnilingual ASR CTC de Meta ([original](https://github.com/facebookresearch/omnilingual-asr), Apache-2.0), en la conversión a `Wav2Vec2ForCTC` de [aadel4](https://huggingface.co/aadel4/omniASR-CTC-1B-v2) | Apache-2.0 | cualquier idioma (unos 1600) |
| `w2v2-large-en` | [facebook/wav2vec2-large-960h-lv60-self](https://huggingface.co/facebook/wav2vec2-large-960h-lv60-self) | Apache-2.0 | inglés |
| `w2v2-en`, `xlsr-en` | [facebook/wav2vec2-base-960h](https://huggingface.co/facebook/wav2vec2-base-960h), [jonatasgrosman/wav2vec2-large-xlsr-53-english](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-english) | Apache-2.0 | inglés (comparación) |
| `xlsr-es`, `xlsr-fr`, `xlsr-de`, `xlsr-pt` | [jonatasgrosman/wav2vec2-large-xlsr-53-*](https://huggingface.co/jonatasgrosman) | Apache-2.0 | castellano, francés, alemán, portugués |
| `ifrz-gl` | [ifrz/wav2vec2-large-xlsr-galician](https://huggingface.co/ifrz/wav2vec2-large-xlsr-galician) | sin licencia publicada | solo para comparar en el banco |

## Parámetros (`LyricsAligner`)

Los valores por defecto salen de los barridos de la decisión 005: relleno 3 por tramo, saltar una
línea 6 por letra (un coro, 4), silencio 4, sin saltos baratos en los bordes y sin mover los
inicios. Los saltos cuestan por letra: con un coste fijo por línea, el camino más barato metía
muchas líneas cortas en el audio en vez de las largas que de verdad se cantan.

| Parámetro | Qué hace |
|---|---|
| `model` | nombre de la tabla; sin él, el del idioma (y Omnilingual si el idioma no tiene uno) |
| `filler_penalty` | coste por tramo de explicar un sonido con el relleno; más alto obliga a la letra a cubrir más |
| `skip_penalty` | coste por letra de saltarse una línea principal |
| `backing_skip_penalty` | coste por letra de saltarse una línea de coro (más bajo: los coros a menudo se pisan con la voz o no se oyen) |
| `edge_skip_penalty` | coste por letra de dejar fuera líneas al principio o al final de la letra (para recortes o versiones cortas); desactivado, porque en canciones enteras puede tirar una estrofa cantada |
| `silence_penalty` | coste extra por letra en un tramo sin voz |
| `refine_onsets` | mover los inicios al arranque de la voz |
| `parts` | dar sílabas con tiempo a las palabras (gl, es, pt) |
| `char_map` | letras que se escriben de otra forma para alinear, por ejemplo `{ j = "x" }` para la gheada |

## Hacer un karaoke

```bash
uv run karaoke make cancion.m4a --lyrics letra.txt --lang gl --out mi-karaoke
```

Acepta cualquier audio o vídeo que lea ffmpeg. Separa la voz, alinea la letra, deja el audio
nivelado en m4a y escribe `karaoke.json` el último: si algo falla a medias, no queda un paquete
que parezca bueno. Para escucharlo, copia la carpeta a `bench/data/paquetes/` y ábrela en
`/proba-audio`.

## Medir

```bash
uv run karaoke-bench run --pipeline bench/pipelines/<pipeline>.toml --set quick --mode lyrics
uv run karaoke-bench run --pipeline bench/pipelines/<pipeline>.toml --set stress --mode lyrics
uv run karaoke-bench compare bench/results/<antes> bench/results/<después>
```
