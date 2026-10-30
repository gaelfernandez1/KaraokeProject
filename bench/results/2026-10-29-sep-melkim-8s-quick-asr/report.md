# Banco · sep-melkim-8s · quick · sin letra

- Fecha: 2026-10-29T12:18:19+01:00
- Commit: ad4521b-dirty
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

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | 32.1 % | 26.7 % | 0.029 | 0.855 | 91.3 % | 0.058 | 0.060 | 71.8 % | — | 0 | 76 |
| en | 5 | 0 | 43.6 % | 36.5 % | 0.050 | 0.711 | 96.0 % | 0.052 | -0.293 | 56.4 % | — | 0 | 73 |
| es | 5 | 0 | 19.7 % | 14.2 % | 0.026 | 0.850 | 93.4 % | 0.083 | -0.679 | 90.0 % | — | 0 | 77 |
| fr | 5 | 0 | 20.1 % | 12.3 % | 0.029 | 0.366 | 98.1 % | 0.080 | -0.330 | 86.8 % | — | 0 | 78 |
| total | 20 | 0 | 29.5 % | 22.8 % | 0.031 | 0.693 | 94.7 % | 0.070 | -0.325 | 75.4 % | — | 0 | 77 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.2 | 2867 | 2309 | 0.204 |
| transcriber | 5.8 | 1335 | 2070 | 0.051 |
| segmenter | — | 0 | 90 | 0.000 |
| aligner | — | 1559 | 4187 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | 33.3 % | 0.052 | 96.8 % | 84.4 % | en | 60.0 |  |
| Wordsmith_-_The_Statement | en | 171 | 19.9 % | 0.044 | 98.6 % | 76.1 % | en | 64.9 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 100.0 % | — | — | — | en | 52.1 |  |
| Ridgway_-_Fire_Inside | en | 284 | 95.4 % | 25.932 | 0.0 % | 4.3 % | en | 69.3 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 11.2 % | 0.060 | 95.9 % | 89.6 % | en | 61.9 |  |
| 10._Disparan_-_criatura | es | 160 | 6.2 % | 0.024 | 100.0 % | 96.9 % | es | 44.4 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 22.9 % | 0.020 | 93.4 % | 91.8 % | es | 61.1 |  |
| Esencia_-_NandoMalo_ | es | 262 | 24.0 % | 0.024 | 96.2 % | 93.7 % | es | 71.5 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 10.7 % | 0.030 | 94.0 % | 95.2 % | es | 59.1 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 63.2 % | 12.364 | 35.0 % | 37.7 % | es | 55.9 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 11.7 % | 0.046 | 95.9 % | 93.5 % | de | 55.5 |  |
| Der_Musiker_-_d-music | de | 271 | 77.9 % | 0.032 | 69.6 % | 26.0 % | de | 67.5 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 52.7 % | 0.043 | 98.5 % | 70.7 % | de | 63.6 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 15.4 % | 0.017 | 88.8 % | 83.1 % | de | 68.2 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 16.6 % | 0.034 | 99.2 % | 88.1 % | de | 62.6 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 13.9 % | 0.025 | 97.4 % | 94.3 % | fr | 53.5 |  |
| Confession_-_Quesabe | fr | 148 | 30.4 % | 0.028 | 96.4 % | 75.3 % | fr | 44.5 |  |
| Mère_nature_-_Law' | fr | 225 | 15.8 % | 0.038 | 98.2 % | 89.4 % | fr | 63.5 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 21.0 % | 0.037 | 99.6 % | 88.1 % | fr | 52.4 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 15.9 % | 0.022 | 98.7 % | 91.0 % | fr | 48.8 |  |

## Peores casos

Mayor mediana de error de inicio:
- Ridgway_-_Fire_Inside: 25.932 s
- Háblame_-_(Talk_to_me)_-_Brunela_Crochenci: 12.364 s
- Cortez_-_Feel__Stripped_: 0.060 s
- Kinematic_-_Peyote: 0.052 s
- 1_Freak_-_Automatisch_Gekommen: 0.046 s

Mayor WER:
- The_Rinn_-_Voices__2017_Version_: 100.0 %
- Ridgway_-_Fire_Inside: 95.4 %
- Der_Musiker_-_d-music: 77.9 %
- Háblame_-_(Talk_to_me)_-_Brunela_Crochenci: 63.2 %
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 52.7 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
