# Banco · c4-asr-bsc · gl · sin letra

- Fecha: 2026-10-29T19:30:17+01:00
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

Mel-Band RoFormer (Kim, 8 s) + BSC Whisper large-v3 LoS (VAD, voice check, fixed seed) + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v1 {'model': 'bsc-los'}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v1
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v11

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | 57.6 % | 46.3 % | 0.020 | 0.591 | 96.6 % | 96.6 % | 0.020 | 0.374 | 52.2 % | — | 0 | 222 | 0.0 % | 19.8 % |
| total | 5 | 0 | 57.6 % | 46.3 % | 0.020 | 0.591 | 96.6 % | 96.6 % | 0.020 | 0.374 | 52.2 % | — | 0 | 222 | 0.0 % | 19.8 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| transcriber | 137.7 | 3287 | 6765 | 0.100 |
| segmenter | — | 0 | 76 | 0.000 |
| aligner | 0.1 | 1555 | 2733 | 0.013 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 47.9 % | 0.020 | 98.1 % | 98.1 % | 60.6 % | validada (75.7 %) | 0.0 % | 13.9 % | gl | 122.3 |  |
| cibran-o-mundo-do-motor | gl | 195 | 51.0 % | — | — | — | — | sin validar | 0.0 % | 19.0 % | gl | 61.6 |  |
| cloplas-laverca | gl | 313 | 56.2 % | 0.020 | 94.2 % | 94.2 % | 42.3 % | validada (75.1 %) | 0.0 % | 12.7 % | gl | 118.0 |  |
| fanny-alexander-lene | gl | 244 | 76.2 % | — | — | — | — | sin validar | 0.0 % | 23.3 % | gl | 67.5 |  |
| mortos-en-vida-chapapote | gl | 162 | 68.0 % | — | — | — | — | sin validar | 0.0 % | 29.8 % | gl | 51.1 |  |

## Peores casos

Mayor mediana de error de inicio:
- pantis-un-aire: 0.020 s
- cloplas-laverca: 0.020 s

Mayor WER:
- fanny-alexander-lene: 76.2 %
- mortos-en-vida-chapapote: 68.0 %
- cloplas-laverca: 56.2 %
- cibran-o-mundo-do-motor: 51.0 %
- pantis-un-aire: 47.9 %

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
