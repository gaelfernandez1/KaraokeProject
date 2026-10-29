# Banco · sep-karaoke-becruily · quick · con letra

- Fecha: 2026-10-29T11:48:16+01:00
- Commit: 03edc9a
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

Mel-Band RoFormer karaoke model (becruily): lead vocals, backing vocals stay in the instrumental + Whisper large-v3-turbo + default CTC aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'mel_band_roformer_karaoke_becruily.ckpt'}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | — | — | 0.026 | 0.809 | 92.9 % | 0.061 | -0.598 | 96.8 % | 0.027 | 0 | 115 |
| en | 5 | 0 | — | — | 0.050 | 0.450 | 90.5 % | 0.061 | -0.167 | 91.1 % | 0.050 | 0 | 113 |
| es | 5 | 0 | — | — | 0.031 | 1.378 | 85.9 % | 0.093 | 0.616 | 98.5 % | 0.030 | 0 | 115 |
| fr | 5 | 0 | — | — | 0.031 | 0.309 | 94.3 % | 0.083 | -0.176 | 93.4 % | 0.033 | 0 | 113 |
| total | 20 | 0 | — | — | 0.034 | 0.739 | 90.9 % | 0.073 | -0.089 | 94.8 % | 0.033 | 0 | 114 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 9.4 | 3955 | 2599 | 0.421 |
| aligner | — | 1559 | 4351 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.046 | 94.2 % | 93.9 % | — | 754.0 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.049 | 85.0 % | 90.7 % | — | 75.0 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.050 | 89.9 % | 97.5 % | — | 100.1 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.046 | 91.0 % | 77.0 % | — | 121.3 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.057 | 97.2 % | 98.9 % | — | 102.3 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.024 | 100.0 % | 100.0 % | — | 71.7 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.048 | 57.8 % | 98.2 % | — | 92.1 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.035 | 84.5 % | 98.2 % | — | 114.5 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.030 | 95.1 % | 98.3 % | — | 85.3 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.027 | 99.0 % | 99.1 % | — | 91.6 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.049 | 85.5 % | 97.8 % | — | 84.6 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.023 | 91.9 % | 98.0 % | — | 120.1 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 97.7 % | 94.6 % | — | 108.6 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 100.0 % | 95.8 % | — | 100.7 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.039 | 86.2 % | 96.0 % | — | 101.5 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.025 | 100.0 % | 97.6 % | — | 83.8 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.031 | 91.2 % | 91.7 % | — | 63.2 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 96.5 % | — | 97.1 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.043 | 80.9 % | 88.1 % | — | 87.4 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.022 | 100.0 % | 94.1 % | — | 79.7 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.057 s
- The_Rinn_-_Voices__2017_Version_: 0.050 s
- 1_Freak_-_Automatisch_Gekommen: 0.049 s
- Wordsmith_-_The_Statement: 0.049 s
- Baila_-_Alfonso_Lugo: 0.048 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
