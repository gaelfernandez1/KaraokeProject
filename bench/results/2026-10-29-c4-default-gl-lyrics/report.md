# Banco · c4-default · gl · con letra

- Fecha: 2026-10-29T16:37:51+01:00
- Commit: 9f19305-dirty
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

Mel-Band RoFormer (Kim, 8 s) + Whisper large-v3-turbo + lyrics aligner (each language's default CTC model)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v6

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | — | — | 0.020 | 0.038 | 98.6 % | 98.7 % | 0.020 | -0.011 | 100.0 % | 0.020 | 0 | 61 | 0.0 % | 23.9 % |
| total | 5 | 0 | — | — | 0.020 | 0.038 | 98.6 % | 98.7 % | 0.020 | -0.011 | 100.0 % | 0.020 | 0 | 61 | 0.0 % | 23.9 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| aligner | 0.1 | 1553 | 2735 | 0.015 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | — | 0.020 | 97.9 % | 98.2 % | 100.0 % | validada (75.7 %) | 0.0 % | 14.0 % | — | 73.8 (caché) |  |
| cibran-o-mundo-do-motor | gl | 195 | — | — | — | — | — | sin validar | 0.0 % | 9.1 % | — | 42.3 (caché) |  |
| cloplas-laverca | gl | 313 | — | 0.020 | 99.3 % | 99.3 % | 100.0 % | validada (75.1 %) | 0.1 % | 7.7 % | — | 69.7 (caché) |  |
| fanny-alexander-lene | gl | 244 | — | — | — | — | — | sin validar | 0.0 % | 45.6 % | — | 53.6 (caché) |  |
| mortos-en-vida-chapapote | gl | 162 | — | — | — | — | — | sin validar | 0.0 % | 42.9 % | — | 35.4 (caché) |  |

## Peores casos

Mayor mediana de error de inicio:
- cloplas-laverca: 0.020 s
- pantis-un-aire: 0.020 s

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
