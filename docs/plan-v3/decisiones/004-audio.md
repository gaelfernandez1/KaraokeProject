# 004 · Audio: separación, volumen, formatos y motor web

- **Fecha**: 29/10/2026
- **Estado**: propuesta (área C3); se aprueba con su PR. La elección del separador queda
  provisional hasta que el usuario escuche las finalistas y C4 la revalide con su alineador.
- **Afecta a**: C4 (recibe la voz separada), C5 y C7 (reloj y motor de audio), C6 (audio del
  vídeo), C8 (tiempo y memoria del servidor)

## Separador

### Qué se midió

Con el banco (`docs/banco.md`) se cambió solo el separador de `base-turbo` (Demucs `htdemucs`).
El resto de la cadena se dejó igual: Whisper `large-v3-turbo` y el alineador CTC provisional.
Los modelos RoFormer van por [audio-separator](https://github.com/nomadkaraoke/python-audio-separator)
0.47.1 (MIT), con 2 pasadas solapadas por trozo y autocast fp16. Con 8 pasadas, las que trae por
defecto, una canción de 4 min tardaba más de 3 min.

Conjunto `quick` (20 canciones de JamendoLyrics), con la letra dada. Este modo es determinista, así
que las diferencias no son ruido, aunque 20 canciones son pocas:

| Separador | ≤ 0,3 s | Error medio | Separar 4 min | VRAM pico | RAM pico |
|---|---|---|---|---|---|
| Demucs `htdemucs` (`base-turbo`) | 98,1 % | 0,114 s | 14 s | 0,8 GB | 3,1 GB |
| Mel-Band RoFormer de voz (Kim) | 98,5 % | 0,096 s | 49 s | 3,2 GB | 2,3 GB |
| BS-RoFormer viperx 1297 | 98,3 % | 0,142 s | 111 s | 2,4 GB | 2,3 GB |
| Mel-Band karaoke (aufr33 y viperx) | 85,5 % | 0,881 s | 49 s | 2,9 GB | 2,3 GB |
| Mel-Band karaoke (becruily) | 90,9 % | 0,739 s | 101 s | 4,0 GB | 2,6 GB |

Los modelos karaoke separan la voz principal y dejan los coros en el instrumental. Se midieron
sobre la mezcla, con su voz principal como voz para alinear, y para eso son malos. Cuando toman la
voz principal por un coro, la línea entera desaparece de la voz y el alineador la coloca lejos.
Dos canciones alemanas empeoran más de 1 s de mediana.

Mel-Band de Kim gana, pero audio-separator le calcula los trozos a partir de `dim_t` (11 s) y no
del `chunk_size` de inferencia que trae su configuración (8 s). Eso da 3,2 GB de VRAM, más de los
3 GB de la meta. Medido en una canción de 4 min:

| Trozo | VRAM pico | Tiempo | Diferencia con 11 s |
|---|---|---|---|
| 11 s (por defecto en audio-separator) | 3,2 GB | 49 s | — |
| 8 s (`segment_size = 801`, el de su configuración) | 2,9 GB | 49 s | −29,6 dB |
| 5,5 s | 2,6 GB | 49 s | −26,5 dB |
| 4 s | 2,4 GB | 50 s | −24,1 dB |

Con trozos de 8 s (`sep-melkim-8s`) frente a `base-turbo`. Los informes están en
`bench/results/2026-10-29-sep-melkim-8s-*`:

| | Demucs (`base-turbo`) | Kim, 8 s |
|---|---|---|
| Con letra, jamendo (79): ≤ 0,3 s | 97,0 % | 97,5 % |
| Con letra, jamendo: por idioma (en / es / fr / de) | 93,8 / 98,3 / 97,0 / 99,1 % | 94,4 / 98,9 / 97,2 / 99,5 % |
| Con letra, jamendo: error de inicio, mediana / media | 0,034 / 0,142 s | 0,033 / 0,136 s |
| Con letra, quick (20): ≤ 0,3 s y error medio | 98,1 % · 0,114 s | 98,5 % · 0,104 s |
| Sin letra, quick: WER (dos ejecuciones de Demucs) | 36,8 y 37,9 % | 29,5 % |
| Sin letra, gallego (2 canciones con letra publicada, 690 palabras): WER | 35,9 % | 40,6 % |
| Canción de 4 min sin cargas (con letra / sin letra) | 22 / 40 s | 60 / 77 s |
| Separador: VRAM / RAM pico | 0,8 / 3,1 GB | 2,9 / 2,4 GB |

- **Sincronía:** con letra, Kim mejora un poco en los cuatro idiomas y ninguna canción empeora.
- **Transcripción sin letra:** el WER baja 7–8 puntos, mucho más que el ruido entre ejecuciones
  (±1,1).
- **Gallego:** el WER sube 4,7 puntos. Está dentro del ruido por idioma (±5,6), pero va en contra,
  y son solo dos canciones. Hay que repetirlo cuando el usuario valide las 5 referencias:
  `run --set gl --mode both` con `sep-melkim-8s` y con `base-turbo`.

### Decisión

- **Separador por defecto: Mel-Band RoFormer de voz (Kim) en trozos de 8 s**
  (`bench/pipelines/sep-melkim-8s.toml`). `karaoke_engine.separation.RoformerSeparator` cumple
  `karaoke_engine.steps.Separator`. Los modelos se descargan una vez a
  `~/.cache/karaoke/models/audio-separator` (fuera del repo).
- Demucs queda como alternativa rápida: separa en 14 s en vez de 50, y transcribe y sincroniza
  algo peor.
- **Sin modelo karaoke por ahora.** En un karaoke los coros suelen seguir sonando. La variante que
  no perjudica la sincronía no se ha medido:
  - el alineador recibe la voz completa de Kim;
  - una segunda pasada karaoke sobre esa voz devuelve los coros al instrumental solo para
    escuchar.

  Costaría unos 50 s más por canción y un stem más en `Stems` (otra decisión). Se decide cuando el
  usuario escuche si echa de menos los coros.
- Quitar la reverberación de la voz no se probó. Si los peores casos de C4 vienen de voz con mucha
  reverberación, se mide entonces.

## Volumen y formatos del paquete

- **Entrada**: cualquier cosa que lea ffmpeg, vídeo incluido. Se decodifica a WAV estéreo de 44,1 kHz.
- **Volumen**: se mide la sonoridad integrada de la mezcla original (EBU R128, `loudnorm` de
  ffmpeg). Se aplica la misma ganancia a instrumental y voz para dejar la mezcla en **−14 LUFS**,
  sin que la mezcla ni ningún stem pasen de **−1 dBTP** de pico real. La mezcla cuenta porque, con
  la voz guía al 100 %, el reproductor suma los dos stems y eso es la mezcla. Así la voz guía al 100 % suena como el
  original y todas las canciones suenan igual de fuerte.
  - Si el pico no deja subir hasta −14, la canción queda por debajo, como hacen YouTube y Apple:
    el volumen solo se baja. `audio.loudness_lufs` guarda el valor real; la del ejemplo de Cortez
    queda en −16,6 LUFS.
- **Formato**: `instrumental.m4a` (160 kb/s) y `vocals.m4a` (128 kb/s).
  - Los dos en AAC-LC estéreo a 44,1 kHz, con el índice al principio (`+faststart`) para saltar
    sin descargar todo.
  - Los dos se codifican igual, así que el retardo del códec es el mismo en ambos.
  - AAC lo abren todos los navegadores, Safari incluido.
- `karaoke audio <paquete> [--mix original]` pasa un paquete existente a este formato.
- El contrato no cambia.

## Motor de audio web (`web/src/lib/audio/`)

- **Reproducción**: dos `AudioBufferSourceNode` (instrumental y voz) programados en el mismo instante del
  `AudioContext`, 50 ms después de pedirlo, así que van juntos a la muestra. La voz se guarda en
  mono para gastar la mitad de memoria y pasa por un `GainNode`: es la voz guía, de 0 a 1.
- **Tono**: ±12 semitonos con [signalsmith-stretch](https://github.com/Signalsmith-Audio/signalsmith-stretch)
  1.3.2 (MIT). Se inserta solo cuando el tono no es 0, y su latencia se descuenta en el reloj.
- **Reloj** (`SongClock`, cumple `PlaybackClock`):
  - `position()` es el transporte: donde sigue la reproducción tras una pausa.
  - `now()` es lo que se oye: el transporte menos la latencia que informa el navegador, la del
    tono y el ajuste manual del dispositivo. La letra sigue `now()`.
  - Entre los saltos del reloj de audio se interpola con `performance.now()`, como mucho 50 ms, y
    nunca va hacia atrás.
- **Calibración**: el usuario toca al ritmo de 10 clics, uno por segundo. Cada toque responde al
  último clic anterior a él, así que se miden retardos de −0,15 a 0,85 s, y el Bluetooth cabe. El
  retardo es la mediana, sin contar los toques raros, y solo cuenta si al menos 4 toques y el 60 %
  coinciden. El ajuste manual es lo que
  falta sobre lo que informa el navegador, porque Safari no informa de nada. La interfaz la pone C7.
- `/proba-audio` (solo con `pnpm dev`) es la página para probar el motor en móviles, portátiles y
  la tele.

## Consecuencias

- C4 recibe la voz de Kim y debe revalidar la elección con su alineador.
- Con Kim aún no se cumplen las metas de sincronía de la decisión 003: 97,5 % frente al 98 % en
  jamendo, y el inglés en 94,4 % frente al 96 %. Eso le toca a C4 (alineador y segmentación).
- El alineador provisional llega a 4,8 GB de RAM, por encima de los 4 GB de la meta (C4).
- El separador pasa a ser el paso más lento: unos 50 s por canción de 4 min en la RTX 3050.
  Contando las cargas de modelos (unos 6 s cada uno), una canción de 4 min sale en unos 75 s con
  letra y unos 90 s sin ella, dentro de la meta de 2 min. C8 puede ofrecer Demucs como opción
  rápida.
- C5 y C7 usan `AudioEngine.now()` para la letra y ponen la interfaz de calibración, voz guía y
  tono.
- Queda por comprobar en dispositivos reales (usuario):
  - que el retardo inicial del AAC no desplaza la letra;
  - el tono en móviles;
  - la latencia por HDMI y Bluetooth.
