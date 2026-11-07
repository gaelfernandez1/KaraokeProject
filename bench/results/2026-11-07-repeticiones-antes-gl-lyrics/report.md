# Banco · repeticiones-antes · gl · con letra

- Fecha: 2026-11-07T18:24:26+01:00
- Commit: 016d5af-dirty
- Banco 3.0.0, normalización v1
- Referencias: gl semiautomática

## Entorno

| Clave | Valor |
|---|---|
| ctranslate2 | 4.8.5 |
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
| transformers | 5.22.1 |

## Pipeline

c4-default before stanza repeats and reading repeat marks by the audio (the baseline of decision 016)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v13

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | — | — | 0.020 | 0.016 | 99.8 % | 100.0 % | 0.020 | 0.011 | 100.0 % | — | 0 | 61 | 0.0 % | 23.9 % |
| total | 5 | 0 | — | — | 0.020 | 0.016 | 99.8 % | 100.0 % | 0.020 | 0.011 | 100.0 % | — | 0 | 61 | 0.0 % | 23.9 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| aligner | 0.1 | 1555 | 2739 | 0.015 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | — | 0.020 | 99.7 % | 100.0 % | 100.0 % | validada (75.7 %) | 0.0 % | 14.0 % | — | 72.4 |  |
| cibran-o-mundo-do-motor | gl | 195 | — | — | — | — | — | sin validar | 0.0 % | 9.1 % | — | 42.3 |  |
| cloplas-laverca | gl | 313 | — | 0.020 | 100.0 % | 100.0 % | 100.0 % | validada (75.1 %) | 0.1 % | 7.7 % | — | 69.6 |  |
| fanny-alexander-lene | gl | 244 | — | — | — | — | — | sin validar | 0.0 % | 45.6 % | — | 53.4 |  |
| mortos-en-vida-chapapote | gl | 162 | — | — | — | — | — | sin validar | 0.0 % | 42.9 % | — | 35.4 |  |

## Peores casos

Mayor mediana de error de inicio:
- cloplas-laverca: 0.020 s
- pantis-un-aire: 0.020 s

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
