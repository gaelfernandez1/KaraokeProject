# Banco · c4-asr-hitz · gl · sin letra

- Fecha: 2026-10-29T19:24:21+01:00
- Commit: 3cdccd5
- Banco 0.1.0, normalización v1
- Referencias: gl semiautomática

## Entorno

| Clave | Valor |
|---|---|
| ctranslate2 | 4.8.4 |
| demucs | 4.0.1 |
| driver | 617.42 |
| faster-whisper | 1.2.1 |
| gpu | NVIDIA GeForce RTX 3050 Laptop GPU |
| gpu_memory_mb | 4096 |
| jiwer | 4.0.0 |
| numpy | 2.5.4 |
| platform | Linux-6.6.114.1-microsoft-standard-WSL2-x86_64-with-glibc2.43 |
| python | 3.12.16 |
| torch | 2.14.1+cu130 |
| transformers | 5.21.0 |

## Pipeline

Mel-Band RoFormer (Kim, 8 s) + HiTZ Whisper large-v3 Galician (VAD, voice check, fixed seed) + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v1 {'model': 'hitz-large-v3-gl'}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v1
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v11

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | 34.7 % | 18.2 % | 0.020 | 0.061 | 97.7 % | 97.7 % | 0.020 | 0.014 | 83.8 % | — | 0 | 227 | 0.0 % | 18.6 % |
| total | 5 | 0 | 34.7 % | 18.2 % | 0.020 | 0.061 | 97.7 % | 97.7 % | 0.020 | 0.014 | 83.8 % | — | 0 | 227 | 0.0 % | 18.6 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| transcriber | 141.1 | 3319 | 6749 | 0.103 |
| segmenter | — | 0 | 75 | 0.000 |
| aligner | 0.1 | 1555 | 2733 | 0.015 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 31.2 % | 0.020 | 97.0 % | 97.0 % | 77.9 % | validada (75.7 %) | 0.0 % | 12.3 % | gl | 132.1 |  |
| cibran-o-mundo-do-motor | gl | 195 | 21.6 % | — | — | — | — | sin validar | 0.0 % | 10.3 % | gl | 57.8 |  |
| cloplas-laverca | gl | 313 | 15.3 % | 0.020 | 98.4 % | 98.4 % | 90.8 % | validada (75.1 %) | 0.0 % | 4.8 % | gl | 90.3 |  |
| fanny-alexander-lene | gl | 244 | 73.5 % | — | — | — | — | sin validar | 0.0 % | 29.8 % | gl | 94.0 |  |
| mortos-en-vida-chapapote | gl | 162 | 51.9 % | — | — | — | — | sin validar | 0.0 % | 35.7 % | gl | 52.2 |  |

## Peores casos

Mayor mediana de error de inicio:
- cloplas-laverca: 0.020 s
- pantis-un-aire: 0.020 s

Mayor WER:
- fanny-alexander-lene: 73.5 %
- mortos-en-vida-chapapote: 51.9 %
- pantis-un-aire: 31.2 %
- cibran-o-mundo-do-motor: 21.6 %
- cloplas-laverca: 15.3 %

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
