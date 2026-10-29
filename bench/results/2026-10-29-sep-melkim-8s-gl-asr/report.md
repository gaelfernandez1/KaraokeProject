# Banco · sep-melkim-8s · gl · sin letra

- Fecha: 2026-10-29T13:13:15+01:00
- Commit: cf278e0
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

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | 46.0 % | 25.3 % | — | — | — | — | — | — | — | 0 | 83 |
| total | 5 | 0 | 46.0 % | 25.3 % | — | — | — | — | — | — | — | 0 | 83 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| transcriber | 5.3 | 1335 | 2070 | 0.068 |
| segmenter | — | 0 | 74 | 0.000 |
| aligner | — | 1553 | 2746 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Referencia | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 41.4 % | — | — | — | sin validar | gl | 95.2 (caché) |  |
| cibran-o-mundo-do-motor | gl | 195 | 39.0 % | — | — | — | sin validar | gl | 55.7 (caché) |  |
| cloplas-laverca | gl | 313 | 24.3 % | — | — | — | sin validar | gl | 89.3 (caché) |  |
| fanny-alexander-lene | gl | 244 | 81.2 % | — | — | — | sin validar | gl | 76.8 (caché) |  |
| mortos-en-vida-chapapote | gl | 162 | 64.6 % | — | — | — | sin validar | gl | 50.5 (caché) |  |

## Peores casos


Mayor WER:
- fanny-alexander-lene: 81.2 %
- mortos-en-vida-chapapote: 64.6 %
- pantis-un-aire: 41.4 %
- cibran-o-mundo-do-motor: 39.0 %
- cloplas-laverca: 24.3 %

## Notas

- Referencia sin validar de oído en pantis-un-aire, cibran-o-mundo-do-motor, cloplas-laverca, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
