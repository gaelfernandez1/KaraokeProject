# Banco · c4-default · gl · sin letra

- Fecha: 2026-10-29T20:53:29+01:00
- Commit: acd55fa-dirty
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

Mel-Band RoFormer (Kim, 8 s) + Whisper (HiTZ large-v3 for Galician, large-v3-turbo otherwise) + lyrics aligner (each language's default CTC model)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v11

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | 33.5 % | 17.1 % | 0.020 | 0.061 | 97.7 % | 97.7 % | 0.020 | 0.014 | 83.3 % | — | 0 | 80 | 0.0 % | 18.2 % |
| total | 5 | 0 | 33.5 % | 17.1 % | 0.020 | 0.061 | 97.7 % | 97.7 % | 0.020 | 0.014 | 83.3 % | — | 0 | 80 | 0.0 % | 18.2 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| transcriber | 0.1 | 3319 | 2543 | 0.078 |
| segmenter | — | 0 | 76 | 0.000 |
| aligner | 0.1 | 1555 | 2735 | 0.015 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 31.0 % | 0.020 | 97.0 % | 97.0 % | 77.4 % | validada (75.7 %) | 0.0 % | 12.0 % | gl | 147.1 |  |
| cibran-o-mundo-do-motor | gl | 195 | 18.3 % | — | — | — | — | sin validar | 0.0 % | 8.6 % | gl | 57.5 |  |
| cloplas-laverca | gl | 313 | 15.6 % | 0.020 | 98.4 % | 98.4 % | 90.5 % | validada (75.1 %) | 0.0 % | 5.6 % | gl | 88.3 |  |
| fanny-alexander-lene | gl | 244 | 69.1 % | — | — | — | — | sin validar | 0.0 % | 28.5 % | gl | 63.2 |  |
| mortos-en-vida-chapapote | gl | 162 | 50.8 % | — | — | — | — | sin validar | 0.0 % | 36.5 % | gl | 50.6 |  |

## Peores casos

Mayor mediana de error de inicio:
- cloplas-laverca: 0.020 s
- pantis-un-aire: 0.020 s

Mayor WER:
- fanny-alexander-lene: 69.1 %
- mortos-en-vida-chapapote: 50.8 %
- pantis-un-aire: 31.0 %
- cibran-o-mundo-do-motor: 18.3 %
- cloplas-laverca: 15.6 %

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
