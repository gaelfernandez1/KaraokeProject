# Banco · c4-default · stress · con letra

- Fecha: 2026-10-29T20:02:28+01:00
- Commit: 6a96d21-dirty
- Banco 0.1.0, normalización v1
- Referencias: de manual, en manual, es manual, fr manual

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
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v2
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v1
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v11

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib | 4 | 0 | — | — | 0.030 | 0.164 | 97.5 % | 97.7 % | 0.064 | -0.076 | 90.4 % | — | 0 | 64 | 0.0 % | 24.2 % |
| echo | 4 | 0 | — | — | 0.048 | 0.068 | 98.9 % | 99.1 % | 0.096 | 0.035 | 97.6 % | — | 0 | 61 | 0.0 % | 21.4 % |
| extra-lines | 4 | 0 | — | — | 0.027 | 0.039 | 99.4 % | 99.6 % | 0.077 | 0.003 | 97.2 % | — | 0 | 61 | 0.2 % | 20.0 % |
| gap | 4 | 0 | — | — | 0.021 | 0.033 | 99.6 % | 99.7 % | 0.067 | 0.007 | 96.6 % | — | 0 | 62 | 0.2 % | 16.5 % |
| missing-line | 4 | 0 | — | — | 0.026 | 0.039 | 99.8 % | 100.0 % | 0.076 | 0.016 | 93.3 % | — | 0 | 61 | 0.0 % | 26.6 % |
| web | 4 | 0 | — | — | 0.042 | 0.049 | 99.9 % | 99.9 % | 0.041 | 0.032 | 92.5 % | — | 0 | 61 | 0.0 % | 32.3 % |
| total | 24 | 0 | — | — | 0.031 | 0.068 | 99.2 % | 99.3 % | 0.065 | 0.000 | 94.2 % | — | 0 | 61 | 0.1 % | 23.5 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.5 | 2867 | 2346 | 0.206 |
| aligner | 0.1 | 1559 | 3776 | 0.015 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib-der-musiker | de | 271 | — | 0.021 | 99.4 % | 99.7 % | 98.0 % | manual | 0.0 % | 13.8 % | — | 68.9 |  |
| adlib-pas-que-tes-pas | fr | 202 | — | 0.037 | 98.3 % | 98.3 % | 88.1 % | manual | 0.1 % | 36.7 % | — | 46.1 |  |
| adlib-ridgway | en | 284 | — | 0.049 | 92.7 % | 92.7 % | 77.0 % | manual | 0.1 % | 29.9 % | — | 64.1 |  |
| adlib-te-recuerdo | es | 194 | — | 0.029 | 98.2 % | 98.4 % | 94.8 % | manual | 0.0 % | 16.5 % | — | 44.9 |  |
| echo-cafe-jenseitz | de | 248 | — | 0.049 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 18.3 % | — | 53.4 |  |
| echo-cortez | en | 241 | — | 0.069 | 99.1 % | 99.4 % | 98.9 % | manual | 0.0 % | 13.3 % | — | 53.0 |  |
| echo-hablame | es | 214 | — | 0.031 | 95.2 % | 95.2 % | 99.1 % | manual | 0.0 % | 34.0 % | — | 46.5 |  |
| echo-mere-nature | fr | 225 | — | 0.038 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 20.2 % | — | 49.5 |  |
| extra-lines-der-musiker | de | 271 | — | 0.021 | 99.4 % | 99.7 % | 98.0 % | manual | 0.0 % | 14.1 % | — | 59.6 |  |
| extra-lines-esencia | es | 262 | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 18.9 % | — | 57.9 |  |
| extra-lines-kinematic | en | 183 | — | 0.052 | 97.1 % | 97.8 % | 93.9 % | manual | 0.7 % | 28.7 % | — | 40.0 |  |
| extra-lines-mere-nature | fr | 225 | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 18.3 % | — | 49.6 |  |
| gap-capotes | fr | 218 | — | 0.025 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 9.3 % | — | 48.5 |  |
| gap-esencia | es | 292 | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 18.9 % | — | 64.8 |  |
| gap-keine-lust | de | 259 | — | 0.016 | 99.8 % | 99.8 % | 95.8 % | manual | 0.0 % | 8.6 % | — | 57.9 |  |
| gap-kinematic | en | 213 | — | 0.053 | 97.1 % | 97.8 % | 93.9 % | manual | 0.7 % | 29.4 % | — | 46.8 |  |
| missing-line-baila | es | 210 | — | 0.019 | 100.0 % | 100.0 % | 96.1 % | manual | 0.0 % | 30.1 % | — | 46.4 |  |
| missing-line-le-musee | fr | 184 | — | 0.022 | 100.0 % | 100.0 % | 91.4 % | manual | 0.0 % | 14.3 % | — | 40.6 |  |
| missing-line-sehnsucht | de | 233 | — | 0.033 | 100.0 % | 100.0 % | 93.4 % | manual | 0.0 % | 15.1 % | — | 51.1 |  |
| missing-line-the-rinn | en | 231 | — | 0.052 | 98.9 % | 100.0 % | 91.6 % | manual | 0.0 % | 47.1 % | — | 50.4 |  |
| web-1-freak | de | 188 | — | 0.044 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 32.2 % | — | 41.7 |  |
| web-10-disparan | es | 160 | — | 0.023 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.7 % | — | 34.5 |  |
| web-confession | fr | 148 | — | 0.029 | 99.7 % | 99.7 % | 86.9 % | manual | 0.2 % | 42.9 % | — | 32.0 |  |
| web-wordsmith | en | 171 | — | 0.054 | 100.0 % | 100.0 % | 89.8 % | manual | 0.0 % | 31.3 % | — | 37.6 |  |

## Peores casos

Mayor mediana de error de inicio:
- echo-cortez: 0.069 s
- web-wordsmith: 0.054 s
- gap-kinematic: 0.053 s
- extra-lines-kinematic: 0.052 s
- missing-line-the-rinn: 0.052 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
