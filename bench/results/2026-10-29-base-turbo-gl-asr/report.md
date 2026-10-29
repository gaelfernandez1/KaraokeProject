# Banco · base-turbo · gl · sin letra

- Fecha: 2026-10-29T09:50:53+01:00
- Commit: 2244468
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

Demucs + Whisper large-v3-turbo (language given) + default CTC aligner

- **separator**: `karaoke_bench.baseline.separation:DemucsSeparator` v2
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | 44.7 % | 21.1 % | — | — | — | — | — | — | — | 0 | 43 |
| total | 5 | 0 | 44.7 % | 21.1 % | — | — | — | — | — | — | — | 0 | 43 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 3.7 | 797 | 2950 | 0.060 |
| transcriber | 5.4 | 1335 | 2070 | 0.067 |
| segmenter | — | 0 | 75 | 0.000 |
| aligner | — | 1553 | 2694 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 37.9 % | — | — | — | gl | 48.6 |  |
| cibran-o-mundo-do-motor | gl | 195 | 32.4 % | — | — | — | gl | 24.4 |  |
| cloplas-laverca | gl | 313 | 23.5 % | — | — | — | gl | 45.0 |  |
| fanny-alexander-lene | gl | 244 | 89.0 % | — | — | — | gl | 35.6 |  |
| mortos-en-vida-chapapote | gl | 162 | 65.0 % | — | — | — | gl | 27.1 |  |

## Peores casos


Mayor WER:
- fanny-alexander-lene: 89.0 %
- mortos-en-vida-chapapote: 65.0 %
- pantis-un-aire: 37.9 %
- cibran-o-mundo-do-motor: 32.4 %
- cloplas-laverca: 23.5 %

## Notas

- Referencia semiautomática validada de oído en gl: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
