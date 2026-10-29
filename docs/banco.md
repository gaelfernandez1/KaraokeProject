# Banco de pruebas (`karaoke-bench`)

El banco dice con números si un cambio del motor mejora la transcripción, la sincronía o la
velocidad. Mide cualquier combinación de pasos (separar la voz, transcribir, segmentar en líneas y
alinear) sobre canciones con tiempos de referencia y deja un informe comparable en
`bench/results/`.

## En dos minutos

```bash
uv sync --extra ml                                   # modelos base (solo en el equipo con GPU)
uv run karaoke-bench fetch --set jamendo             # 79 canciones públicas (~400 MB, una vez)
uv run karaoke-bench run --pipeline bench/pipelines/base-turbo.toml --set quick --mode lyrics
uv run karaoke-bench compare bench/results/<antes> bench/results/<después>
```

El audio nunca entra en git: todo lo descargado o calculado va a `bench/data/` (ignorado).

## Conjuntos

| Conjunto | Qué es | Para qué |
|---|---|---|
| `jamendo` | 79 canciones de [JamendoLyrics MultiLang](https://huggingface.co/datasets/jamendolyrics/jamendolyrics) (en, es, fr, de) con el inicio y el fin de cada palabra anotados a mano; la letra bien escrita y los tiempos por línea salen de [Jam-ALT](https://huggingface.co/datasets/jamendolyrics/jam-alt) | medidas completas |
| `jamendo-<idioma>` | las de un idioma | medir un idioma |
| `quick` | 20 fijas (5 por idioma, géneros variados), en `bench/sets/quick.txt` | prueba rápida diaria |
| `gl` | canciones en gallego con licencia libre y tiempos validados de oído (`bench/sets/gl/`) | la meta principal |
| `private` | tus canciones, en `bench/data/private/` | solo en local |
| `<conjunto>/<id>` | una canción suelta | depurar |

Las dos fuentes públicas están fijadas a una revisión concreta en `bench/sets/jamendo.toml`.
Cambiarla cambia todos los números, así que solo se hace a propósito.

## Modos

- **`lyrics` (con letra)**: separador (si lo hay) y alineador con la letra que pegaría un usuario
  (la de Jam-ALT o `lyrics.txt`). Mide la sincronía.
- **`asr` (sin letra)**: separador, transcriptor, segmentador y alineador con las líneas
  transcritas y el idioma que devuelve el transcriptor (así se ve el cambio silencioso de idioma).
  Mide WER, CER, idioma y la sincronía de las palabras que casan con la referencia.
- **`both`**: los dos, en dos informes.

## Pipelines

Un pipeline es un TOML en `bench/pipelines/` que dice qué clase hace cada paso:

```toml
name = "mi-prueba"                     # minúsculas, números y guiones
description = "Qué cambia respecto a la línea base"

[steps.separator]                      # opcional: sin él se usa la mezcla
target = "karaoke_bench.baseline.separation:DemucsSeparator"

[steps.aligner]
target = "karaoke_bench.baseline.ctc:CtcAligner"
params = { model = "proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl", revision = "05a9b49…" }
```

Pasos: `separator`, `transcriber`, `segmenter` y `aligner`. Sirve cualquier clase que cumpla los
protocolos de `karaoke_engine.steps`. Para que el banco la use bien:

- Atributo de clase `version` (texto): súbelo cuando cambie lo que produce, porque forma parte de la
  clave de la caché.
- Nada pesado a nivel de módulo: `torch`, `transformers` y similares se importan dentro de los
  métodos, porque el banco importa la clase para leer `version`.
- Opcional: un método `load()` sin argumentos. El banco lo cronometra aparte como «carga».
- Fija la revisión de los modelos de Hugging Face.

Pipelines incluidos:

| Pipeline | Qué es |
|---|---|
| `smoke` | pasos falsos, sin modelos; el alineador reparte las palabras por igual (el «tonto» que hay que batir) |
| `base-legacy` | el sistema v2 con librerías actuales: Demucs, Whisper `small` adivinando el idioma y el alineador CTC por defecto |
| `base-turbo` | Demucs, Whisper `large-v3-turbo` con el idioma elegido y el alineador CTC por defecto |
| `draft-gl` | Demucs y el alineador con el modelo de Proxecto Nós; hace los borradores de las referencias gallegas |

## Cómo funciona una ejecución

Cada paso corre para todas las canciones en **su propio proceso**: carga el modelo una vez, deja la
GPU limpia al acabar y su memoria se mide sola. El resultado de cada paso se guarda en caché
(`bench/data/cache/`) con clave por clase, parámetros, versión y entrada, así que probar otro
alineador no repite la separación. `--no-cache` lo recalcula todo.

Si un paso falla en una canción (excepción, falta de memoria o proceso muerto), esa canción sale con
su error y las demás siguen: si el proceso muere, se relanza para las que faltan (hasta 3 veces).
También se marca como error un alineador que devuelve otro número de líneas o tiempos fuera de la
canción. Cada canción terminada entra en la caché en el momento, así que una ejecución cortada
(`Ctrl`+`C`, un apagón) sigue donde iba al relanzarla.

Cada ejecución deja:

- `bench/results/<fecha>-<pipeline>-<conjunto>-<modo>/report.md`: el informe (se versiona);
- `.../results.json`: todos los números, el entorno, el commit y la versión de la normalización (se
  versiona);
- `bench/data/runs/<mismo nombre>/<canción>.json`: las salidas completas (no se versiona).

## Métricas

- **WER y CER** (solo en `asr`): sobre la letra normalizada, ponderadas por palabras o caracteres en
  cada grupo. La normalización (versión en `textnorm.NORMALIZATION_VERSION`) pasa a minúsculas,
  unifica apóstrofos, quita etiquetas como `[Estribillo]`, marcas de repetición (`x2`, `bis`) y la
  puntuación, y separa por guiones (`vou-te` → `vou te`). **Las tildes cuentan**: en gallego `é` y
  `e` son palabras distintas. Lo que va entre paréntesis (coros) se queda, porque se canta. Los
  números no se pasan a letra: las referencias se escriben en letra.
- **Sincronía de palabra**: las palabras de la salida se emparejan con las de la referencia
  (alineación de Levenshtein ignorando tildes) y solo cuentan las que casan:
  - error absoluto del inicio (mediana, media y % ≤ 0,3 s);
  - error absoluto del fin (mediana);
  - **sesgo**: media con signo (positivo = la letra llega tarde);
  - **cobertura**: % de palabras de la referencia emparejadas.
  
  Equivalen al AAE y al PCO de los artículos de JamendoLyrics.
- **Sincronía de línea** (solo en `lyrics`): mediana del error de inicio de las líneas, frente a
  Jam-ALT o la referencia gallega.
- **Idioma**: idioma pedido frente al que devuelve el transcriptor. Cualquier diferencia cuenta como
  cambio de idioma.
- **Velocidad**: segundos por paso y canción, factor de tiempo real (segundos ÷ duración) y una
  estimación para una canción de 4 minutos (suma de las medianas × 240 s más las cargas).
- **Memoria**: VRAM pico de cada paso con NVML, restando lo que ya estaba ocupado al empezar
  (Windows usa ~1 GB). Si el paso usa torch, también su pico propio. RAM pico del proceso.

## Comparar

```bash
uv run karaoke-bench compare bench/results/A bench/results/B [--out comparacion.md]
```

Tabla por idioma con A, B y la diferencia, y la lista de canciones que empeoran (+0,05 s de
mediana de inicio o +5 puntos de WER). Avisa si cambió la normalización, el conjunto o el modo.

## Referencias gallegas

No hay tiempos publicados para canciones en gallego, así que se crean así:

1. **Borrador**: `uv run karaoke-bench draft gl/<id> --pipeline bench/pipelines/draft-gl.toml`.
   Usa un modelo que ninguna pipeline base usa, para no puntuar a la línea base contra sí misma.
2. **Revisión de oído**: `uv run karaoke-bench review gl/<id> --pipeline bench/pipelines/draft-gl.toml`
   y abrir <http://localhost:8765> en el navegador (también desde Windows). La página reproduce la
   canción iluminando cada palabra, con la forma de onda de la voz debajo. Teclas:

   | Tecla | Qué hace |
   |---|---|
   | `Espazo` | reproducir o parar |
   | clic en una línea | escucharla desde 1 s antes |
   | `1` / `2` / `3` | la línea está bien / mal (pide una nota) / dudosa |
   | `A` | «la línea empieza aquí» (marca un ancla en el punto que suena) |
   | clic en una palabra, `←`/`→` | mover su inicio ±0,05 s (con `Mayús`, el fin) |
   | doble clic en el texto | corregir la letra de la línea |
   | `V` | velocidad 0,75× |
   | `M` | escuchar la mezcla o solo la voz |
   | `Ctrl`+`S` | guardar |

3. **Realineado**: `uv run karaoke-bench realign gl/<id> --pipeline bench/pipelines/draft-gl.toml`
   vuelve a alinear solo las líneas marcadas mal, dentro del hueco que dejan sus vecinas buenas o
   las anclas. Esas líneas quedan como «revisar» para volver a escucharlas.
4. Cuando no queda nada sin revisar ni mal, el botón **Canción validada** la da por buena.

Solo cuentan para la sincronía las líneas marcadas «bien», y solo cuando la canción está validada:
hasta entonces el informe la marca «sin validar» y no entra en la sincronía. El texto corregido en la
página es el que vale para el WER y el que recibe el alineador. Una referencia validada de oído es
fiable a unos ±0,1 s, así que en `gl` manda el % ≤ 0,3 s más que la mediana. `draft` no sobrescribe una
referencia con líneas ya revisadas salvo con `--force`.

## Añadir canciones

**Públicas en gallego** (o en otro idioma, en un conjunto con manifiesto):

1. Busca una canción con licencia CC (mejor BY o BY-SA) y una URL de descarga directa estable
   (Internet Archive va bien).
2. Añádela a `bench/sets/gl/manifest.toml` con `id`, `title`, `artist`, `language`, `style`,
   `license`, `license_url`, `source`, `audio_url` y `sha256` (de `sha256sum`).
   Si la canción va dentro de una grabación más larga (un concierto entero), añade
   `clip = [inicio, fin]` en segundos: se descarga la grabación, se comprueba y se guarda solo ese
   trozo, sin pérdidas.
3. Crea `bench/sets/gl/<id>/lyrics.txt` con la letra tal como se muestra y un `LICENSE` con autor,
   obra, licencia y fuente.
4. `uv run karaoke-bench fetch --set gl`, luego `draft`, `review` y `realign` como arriba.

**Privadas** (nunca salen de tu equipo): crea `bench/data/private/<id>/` con:

- `audio.<ext>` (cualquier formato que lea ffmpeg);
- `meta.toml` con `title = "…"`, `artist = "…"` y `language = "gl"`;
- `lyrics.txt` si tienes la letra;
- `reference.json` si tienes los tiempos. Un `karaoke.json` corregido a mano también sirve: se
  convierte con `karaoke_bench.reference.reference_from_doc`.

Si tienes los tiempos en un subtítulo `.srt` hecho a mano palabra a palabra (una entrada por
palabra; vale que alguna lleve dos palabras o que una palabra vaya partida en sílabas), crea antes
el `lyrics.txt` con las líneas de la canción y conviértelo:

```bash
uv run karaoke-bench import-srt private/<id> mis-tiempos.srt
```

La referencia queda como **aproximada**: un subtítulo hecho a mano es fiable a unas décimas de
segundo, así que en esas canciones el informe da también el % de palabras a ≤ 0,5 s.

Sin referencia, el banco solo mide velocidad, memoria e idioma. Con `draft` y `review` puedes
crearla igual que para el conjunto gallego.

## Formato de referencia (`reference.json`)

```json
{
  "song_id": "…", "language": "gl", "duration": 215.3,
  "timing": "manual | semiautomatic | approximate", "approved": true,
  "lines": [
    { "text": "Vou-te ver, d'aquí", "start": 12.3, "end": 15.8,
      "status": "draft | ok | wrong | unsure", "anchor": null, "note": null, "revised": false,
      "words": [ { "text": "Vou-te", "start": 12.3, "end": 12.7 } ] }
  ]
}
```

`text` es la línea tal como se ve. Las palabras pueden estar escritas de otra forma (en
JamendoLyrics van en minúscula y sin tildes): se emparejan sin tildes.

## Paquetes de ejemplo con canciones reales

`uv run karaoke-bench package jamendo/<id> --pipeline bench/pipelines/base-turbo.toml --out fixtures/packages/<slug>`
crea un paquete de karaoke con la letra de Jam-ALT y los tiempos manuales de JamendoLyrics. Solo
se versionan `karaoke.json` y `LICENSE`; el audio se genera en local con ese mismo comando.

## Ruido del banco

Repetir una ejecución sin caché da números casi iguales, pero no idénticos (la GPU no es del todo
determinista). La variación medida está en la sección «Ruido» de la decisión
`docs/plan-v3/decisiones/003-banco-y-metas.md`: una diferencia menor que ese ruido no es una mejora.
