# Banco · base-legacy · gl · sin letra

- Fecha: 2026-10-29T09:53:17+01:00
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

Demucs + Whisper small (language detected) + default CTC aligner, like v2

- **separator**: `karaoke_bench.baseline.separation:DemucsSeparator` v2
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'small', 'detect_language': True}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 3 | 82.5 % | 50.4 % | — | — | — | — | — | — | — | 5 | 62 |
| total | 5 | 3 | 82.5 % | 50.4 % | — | — | — | — | — | — | — | 5 | 62 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 3.7 | 797 | 2950 | 0.060 |
| transcriber | 2.6 | 791 | 1320 | 0.113 |
| segmenter | — | 0 | 75 | 0.000 |
| aligner | — | 1549 | 2695 | 0.058 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 75.5 % | — | — | — | nn | 51.9 | aligner: ValueError: no default alignment model for language 'nn' |
| cibran-o-mundo-do-motor | gl | 195 | 100.0 % | — | — | — | ko | 28.1 |  |
| cloplas-laverca | gl | 313 | 65.4 % | — | — | — | nn | 54.1 | aligner: ValueError: no default alignment model for language 'nn' |
| fanny-alexander-lene | gl | 244 | 98.9 % | — | — | — | la | 36.8 | aligner: ValueError: no default alignment model for language 'la' |
| mortos-en-vida-chapapote | gl | 162 | 90.6 % | — | — | — | es | 39.4 |  |

## Peores casos


Mayor WER:
- cibran-o-mundo-do-motor: 100.0 %
- fanny-alexander-lene: 98.9 %
- mortos-en-vida-chapapote: 90.6 %
- pantis-un-aire: 75.5 %
- cloplas-laverca: 65.4 %

## Notas

- Falló pantis-un-aire: aligner: ValueError: no default alignment model for language 'nn'
- Falló cloplas-laverca: aligner: ValueError: no default alignment model for language 'nn'
- Falló fanny-alexander-lene: aligner: ValueError: no default alignment model for language 'la'
- Referencia semiautomática validada de oído en gl: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
