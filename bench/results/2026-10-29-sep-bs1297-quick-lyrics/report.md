# Banco · sep-bs1297 · quick · con letra

- Fecha: 2026-10-29T10:49:47+01:00
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

BS-RoFormer vocals model (viperx, SDR 12.97) + Whisper large-v3-turbo + default CTC aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'model_bs_roformer_ep_317_sdr_12.9755.ckpt'}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | — | — | 0.025 | 0.182 | 99.4 % | 0.055 | -0.128 | 96.8 % | 0.024 | 0 | 122 |
| en | 5 | 0 | — | — | 0.046 | 0.210 | 96.5 % | 0.052 | 0.035 | 91.1 % | 0.039 | 0 | 118 |
| es | 5 | 0 | — | — | 0.025 | 0.108 | 98.1 % | 0.081 | 0.067 | 98.5 % | 0.025 | 0 | 121 |
| fr | 5 | 0 | — | — | 0.030 | 0.053 | 99.1 % | 0.080 | -0.022 | 93.4 % | 0.032 | 0 | 121 |
| total | 20 | 0 | — | — | 0.030 | 0.142 | 98.3 % | 0.065 | -0.013 | 94.8 % | 0.028 | 0 | 121 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.3 | 2449 | 2252 | 0.461 |
| aligner | — | 1559 | 4206 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.051 | 94.2 % | 93.9 % | — | 93.4 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.043 | 100.0 % | 90.7 % | — | 80.3 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.046 | 91.4 % | 97.5 % | — | 107.7 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.045 | 92.3 % | 77.0 % | — | 131.9 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.056 | 98.0 % | 98.9 % | — | 113.2 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.024 | 99.0 % | 100.0 % | — | 77.0 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.020 | 98.9 % | 98.2 % | — | 100.7 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.023 | 100.0 % | 98.2 % | — | 125.8 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.030 | 95.3 % | 98.3 % | — | 93.5 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.027 | 100.0 % | 99.1 % | — | 101.6 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.045 | 100.0 % | 97.8 % | — | 94.1 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.021 | 99.7 % | 98.0 % | — | 130.6 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 96.6 % | 94.6 % | — | 117.3 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 99.8 % | 95.8 % | — | 110.9 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.034 | 97.2 % | 96.0 % | — | 110.9 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.024 | 100.0 % | 97.6 % | — | 90.9 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.032 | 97.1 % | 91.7 % | — | 69.9 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 96.5 % | — | 107.9 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.036 | 99.2 % | 88.1 % | — | 96.6 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.022 | 100.0 % | 94.1 % | — | 89.1 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.056 s
- Kinematic_-_Peyote: 0.051 s
- The_Rinn_-_Voices__2017_Version_: 0.046 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.046 s
- Ridgway_-_Fire_Inside: 0.045 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
