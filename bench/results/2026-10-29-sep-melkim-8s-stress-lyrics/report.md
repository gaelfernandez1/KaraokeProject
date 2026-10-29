# Banco · sep-melkim-8s · stress · con letra

- Fecha: 2026-10-29T14:40:01+01:00
- Commit: a41e44c-dirty
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

Mel-Band RoFormer vocals model (Kimberley Jensen, 8 s chunks) + Whisper large-v3-turbo + default CTC aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib | 4 | 0 | — | — | 0.029 | 0.171 | 96.6 % | 97.0 % | 0.066 | -0.038 | 91.5 % | 0.029 | 0 | 64 | 6.9 % | 30.6 % |
| echo | 4 | 0 | — | — | 0.044 | 0.069 | 98.1 % | 98.6 % | 0.099 | 0.033 | 97.6 % | 0.043 | 0 | 63 | 13.9 % | 22.7 % |
| extra-lines | 4 | 0 | — | — | 0.028 | 0.125 | 97.6 % | 98.4 % | 0.079 | 0.068 | 97.2 % | — | 0 | 63 | 12.0 % | 27.2 % |
| gap | 4 | 0 | — | — | 0.021 | 0.098 | 99.4 % | 99.7 % | 0.068 | 0.071 | 96.6 % | 0.025 | 0 | 63 | 13.6 % | 19.1 % |
| missing-line | 4 | 0 | — | — | 0.026 | 0.219 | 97.1 % | 97.7 % | 0.081 | -0.166 | 94.2 % | — | 0 | 62 | 4.7 % | 29.0 % |
| web | 4 | 0 | — | — | 0.037 | 0.078 | 98.7 % | 99.0 % | 0.043 | 0.004 | 92.8 % | 0.031 | 0 | 63 | 1.5 % | 36.8 % |
| total | 24 | 0 | — | — | 0.030 | 0.124 | 98.0 % | 98.4 % | 0.069 | 0.001 | 94.7 % | 0.028 | 0 | 63 | 8.8 % | 27.6 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.5 | 2867 | 2346 | 0.206 |
| aligner | — | 1559 | 4517 | 0.022 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib-der-musiker | de | 271 | — | 0.021 | 99.4 % | 99.7 % | 98.0 % | manual | 0.0 % | 14.7 % | — | 71.3 |  |
| adlib-pas-que-tes-pas | fr | 202 | — | 0.037 | 99.6 % | 99.6 % | 88.1 % | manual | 15.4 % | 41.7 % | — | 46.1 |  |
| adlib-ridgway | en | 284 | — | 0.044 | 91.9 % | 92.7 % | 77.0 % | manual | 11.4 % | 44.3 % | — | 61.5 |  |
| adlib-te-recuerdo | es | 194 | — | 0.030 | 95.3 % | 95.8 % | 98.3 % | manual | 0.9 % | 21.8 % | — | 45.7 |  |
| echo-cafe-jenseitz | de | 248 | — | 0.049 | 98.9 % | 100.0 % | 94.6 % | manual | 54.5 % | 17.4 % | — | 55.0 |  |
| echo-cortez | en | 241 | — | 0.058 | 96.9 % | 97.7 % | 98.9 % | manual | 0.0 % | 18.6 % | — | 52.5 |  |
| echo-hablame | es | 214 | — | 0.031 | 97.1 % | 97.1 % | 99.1 % | manual | 0.0 % | 34.0 % | — | 48.4 |  |
| echo-mere-nature | fr | 225 | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 1.0 % | 20.6 % | — | 51.7 |  |
| extra-lines-der-musiker | de | 271 | — | 0.022 | 96.5 % | 97.1 % | 98.0 % | manual | 0.0 % | 19.5 % | — | 62.0 |  |
| extra-lines-esencia | es | 262 | — | 0.023 | 98.8 % | 99.1 % | 98.2 % | manual | 9.4 % | 24.9 % | — | 60.0 |  |
| extra-lines-kinematic | en | 183 | — | 0.052 | 93.5 % | 97.1 % | 93.9 % | manual | 37.6 % | 41.8 % | — | 39.6 |  |
| extra-lines-mere-nature | fr | 225 | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 1.2 % | 22.4 % | — | 51.3 |  |
| gap-capotes | fr | 218 | — | 0.025 | 100.0 % | 100.0 % | 97.6 % | manual | 7.7 % | 8.6 % | — | 48.8 |  |
| gap-esencia | es | 292 | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 9.3 % | 18.3 % | — | 67.0 |  |
| gap-keine-lust | de | 259 | — | 0.016 | 99.8 % | 99.8 % | 95.8 % | manual | 0.0 % | 9.9 % | — | 60.6 |  |
| gap-kinematic | en | 213 | — | 0.050 | 95.7 % | 97.8 % | 93.9 % | manual | 37.4 % | 39.9 % | — | 45.9 |  |
| missing-line-baila | es | 210 | — | 0.019 | 99.6 % | 99.6 % | 96.1 % | manual | 0.2 % | 31.3 % | — | 47.4 |  |
| missing-line-le-musee | fr | 184 | — | 0.022 | 99.6 % | 100.0 % | 91.4 % | manual | 0.0 % | 14.7 % | — | 42.4 |  |
| missing-line-sehnsucht | de | 233 | — | 0.032 | 99.3 % | 99.3 % | 93.4 % | manual | 0.0 % | 15.8 % | — | 52.5 |  |
| missing-line-the-rinn | en | 231 | — | 0.049 | 89.2 % | 91.2 % | 95.6 % | manual | 18.7 % | 54.3 % | — | 49.5 |  |
| web-1-freak | de | 188 | — | 0.044 | 98.9 % | 98.9 % | 95.6 % | manual | 4.0 % | 34.1 % | — | 43.2 |  |
| web-10-disparan | es | 160 | — | 0.025 | 98.4 % | 98.4 % | 95.4 % | manual | 0.0 % | 25.0 % | — | 36.0 |  |
| web-confession | fr | 148 | — | 0.031 | 96.8 % | 97.7 % | 91.7 % | manual | 2.1 % | 46.5 % | — | 33.6 |  |
| web-wordsmith | en | 171 | — | 0.043 | 99.8 % | 100.0 % | 90.7 % | manual | 0.0 % | 41.7 % | — | 37.1 |  |

## Peores casos

Mayor mediana de error de inicio:
- echo-cortez: 0.058 s
- extra-lines-kinematic: 0.052 s
- gap-kinematic: 0.050 s
- echo-cafe-jenseitz: 0.049 s
- missing-line-the-rinn: 0.049 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
