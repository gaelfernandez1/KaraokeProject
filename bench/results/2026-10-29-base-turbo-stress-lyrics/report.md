# Banco · base-turbo · stress · con letra

- Fecha: 2026-10-29T14:19:25+01:00
- Commit: b32c547
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

Demucs + Whisper large-v3-turbo (language given) + default CTC aligner

- **separator**: `karaoke_bench.baseline.separation:DemucsSeparator` v2
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib | 4 | 0 | — | — | 0.030 | 0.188 | 95.7 % | 96.2 % | 0.067 | -0.057 | 91.5 % | 0.031 | 0 | 23 |
| echo | 4 | 0 | — | — | 0.044 | 0.070 | 98.2 % | 98.7 % | 0.098 | 0.029 | 97.6 % | 0.044 | 0 | 22 |
| extra-lines | 4 | 0 | — | — | 0.028 | 0.121 | 96.8 % | 97.3 % | 0.080 | 0.037 | 97.2 % | — | 0 | 23 |
| gap | 4 | 0 | — | — | 0.021 | 0.126 | 99.2 % | 99.3 % | 0.068 | 0.003 | 96.6 % | 0.026 | 0 | 22 |
| missing-line | 4 | 0 | — | — | 0.027 | 0.177 | 96.7 % | 97.3 % | 0.080 | -0.107 | 94.2 % | — | 0 | 21 |
| web | 4 | 0 | — | — | 0.036 | 0.094 | 98.8 % | 99.0 % | 0.043 | -0.013 | 92.8 % | 0.031 | 0 | 23 |
| total | 24 | 0 | — | — | 0.030 | 0.130 | 97.6 % | 98.0 % | 0.068 | -0.017 | 94.7 % | 0.030 | 0 | 22 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 2.8 | 2057 | 2814 | 0.059 |
| aligner | — | 3943 | 4654 | 0.022 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib-der-musiker | de | 271 | — | 0.021 | 96.8 % | 96.8 % | 98.0 % | manual | — | 32.3 |  |
| adlib-pas-que-tes-pas | fr | 202 | — | 0.040 | 98.3 % | 99.2 % | 88.1 % | manual | — | 16.6 |  |
| adlib-ridgway | en | 284 | — | 0.047 | 91.5 % | 92.3 % | 77.0 % | manual | — | 19.4 |  |
| adlib-te-recuerdo | es | 194 | — | 0.030 | 95.6 % | 96.2 % | 98.3 % | manual | — | 16.6 |  |
| echo-cafe-jenseitz | de | 248 | — | 0.046 | 98.9 % | 100.0 % | 94.6 % | manual | — | 19.4 |  |
| echo-cortez | en | 241 | — | 0.058 | 96.6 % | 97.4 % | 98.9 % | manual | — | 17.0 |  |
| echo-hablame | es | 214 | — | 0.031 | 99.0 % | 99.0 % | 99.1 % | manual | — | 16.7 |  |
| echo-mere-nature | fr | 225 | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | — | 23.4 |  |
| extra-lines-der-musiker | de | 271 | — | 0.022 | 93.9 % | 94.2 % | 98.0 % | manual | — | 25.6 |  |
| extra-lines-esencia | es | 262 | — | 0.023 | 99.1 % | 99.4 % | 98.2 % | manual | — | 21.4 |  |
| extra-lines-kinematic | en | 183 | — | 0.049 | 94.2 % | 96.4 % | 93.9 % | manual | — | 12.8 |  |
| extra-lines-mere-nature | fr | 225 | — | 0.038 | 99.2 % | 99.2 % | 96.5 % | manual | — | 19.4 |  |
| gap-capotes | fr | 218 | — | 0.025 | 99.2 % | 99.2 % | 97.6 % | manual | — | 16.6 |  |
| gap-esencia | es | 292 | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | — | 23.7 |  |
| gap-keine-lust | de | 259 | — | 0.017 | 100.0 % | 100.0 % | 95.8 % | manual | — | 23.0 |  |
| gap-kinematic | en | 213 | — | 0.050 | 94.2 % | 95.7 % | 93.9 % | manual | — | 14.8 |  |
| missing-line-baila | es | 210 | — | 0.020 | 98.2 % | 98.5 % | 96.1 % | manual | — | 16.7 |  |
| missing-line-le-musee | fr | 184 | — | 0.023 | 99.6 % | 100.0 % | 91.4 % | manual | — | 15.6 |  |
| missing-line-sehnsucht | de | 233 | — | 0.031 | 97.9 % | 97.9 % | 93.4 % | manual | — | 17.6 |  |
| missing-line-the-rinn | en | 231 | — | 0.048 | 90.2 % | 91.8 % | 95.6 % | manual | — | 15.2 |  |
| web-1-freak | de | 188 | — | 0.043 | 98.3 % | 98.3 % | 95.6 % | manual | — | 15.3 |  |
| web-10-disparan | es | 160 | — | 0.022 | 98.9 % | 98.9 % | 95.4 % | manual | — | 13.4 |  |
| web-confession | fr | 148 | — | 0.029 | 97.4 % | 98.1 % | 91.7 % | manual | — | 12.9 |  |
| web-wordsmith | en | 171 | — | 0.043 | 100.0 % | 100.0 % | 90.7 % | manual | — | 13.0 |  |

## Peores casos

Mayor mediana de error de inicio:
- echo-cortez: 0.058 s
- gap-kinematic: 0.050 s
- extra-lines-kinematic: 0.049 s
- missing-line-the-rinn: 0.048 s
- adlib-ridgway: 0.047 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
