# Banco · sep-melkim-8s · gl · con letra

- Fecha: 2026-10-29T16:37:49+01:00
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

Mel-Band RoFormer vocals model (Kimberley Jensen, 8 s chunks) + Whisper large-v3-turbo + default CTC aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | — | — | 0.000 | 0.032 | 98.7 % | 98.7 % | 0.017 | -0.023 | 100.0 % | 0.001 | 0 | 61 | 5.8 % | 44.1 % |
| total | 5 | 0 | — | — | 0.000 | 0.032 | 98.7 % | 98.7 % | 0.017 | -0.023 | 100.0 % | 0.001 | 0 | 61 | 5.8 % | 44.1 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| aligner | — | 1553 | 2750 | 0.015 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | — | 0.000 | 98.2 % | 98.2 % | 100.0 % | validada (75.7 %) | 8.4 % | 27.5 % | — | 72.2 |  |
| cibran-o-mundo-do-motor | gl | 195 | — | — | — | — | — | sin validar | 7.9 % | 31.5 % | — | 42.4 |  |
| cloplas-laverca | gl | 313 | — | 0.000 | 99.3 % | 99.3 % | 100.0 % | validada (75.1 %) | 0.0 % | 25.4 % | — | 70.0 |  |
| fanny-alexander-lene | gl | 244 | — | — | — | — | — | sin validar | 12.7 % | 61.4 % | — | 53.4 |  |
| mortos-en-vida-chapapote | gl | 162 | — | — | — | — | — | sin validar | 0.2 % | 74.7 % | — | 35.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- pantis-un-aire: 0.000 s
- cloplas-laverca: 0.000 s

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
