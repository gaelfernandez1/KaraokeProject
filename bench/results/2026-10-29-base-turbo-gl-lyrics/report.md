# Banco · base-turbo · gl · con letra

- Fecha: 2026-10-29T16:37:17+01:00
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

Demucs + Whisper large-v3-turbo (language given) + default CTC aligner

- **separator**: `karaoke_bench.baseline.separation:DemucsSeparator` v2
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | — | — | 0.000 | 0.031 | 98.7 % | 98.7 % | 0.000 | -0.022 | 100.0 % | 0.000 | 0 | 29 | 3.7 % | 52.1 % |
| total | 5 | 0 | — | — | 0.000 | 0.031 | 98.7 % | 98.7 % | 0.000 | -0.022 | 100.0 % | 0.000 | 0 | 29 | 3.7 % | 52.1 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 3.7 | 797 | 2950 | 0.060 |
| aligner | — | 1553 | 2750 | 0.047 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | — | 0.000 | 98.2 % | 98.2 % | 100.0 % | validada (75.7 %) | 7.7 % | 35.6 % | — | 31.1 (caché) |  |
| cibran-o-mundo-do-motor | gl | 195 | — | — | — | — | — | sin validar | 9.3 % | 42.3 % | — | 22.0 (caché) |  |
| cloplas-laverca | gl | 313 | — | 0.000 | 99.3 % | 99.3 % | 100.0 % | validada (75.1 %) | 1.0 % | 29.4 % | — | 31.4 (caché) |  |
| fanny-alexander-lene | gl | 244 | — | — | — | — | — | sin validar | 0.0 % | 72.5 % | — | 25.1 (caché) |  |
| mortos-en-vida-chapapote | gl | 162 | — | — | — | — | — | sin validar | 0.3 % | 80.8 % | — | 19.6 (caché) |  |

## Peores casos

Mayor mediana de error de inicio:
- cloplas-laverca: 0.000 s
- pantis-un-aire: 0.000 s

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
