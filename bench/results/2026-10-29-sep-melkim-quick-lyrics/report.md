# Banco · sep-melkim · quick · con letra

- Fecha: 2026-10-29T10:15:32+01:00
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

Mel-Band RoFormer vocals model (Kimberley Jensen) + Whisper large-v3-turbo + default CTC aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt'}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | — | — | 0.024 | 0.035 | 99.7 % | 0.055 | 0.020 | 96.8 % | 0.024 | 0 | 60 |
| en | 5 | 0 | — | — | 0.046 | 0.211 | 96.8 % | 0.055 | 0.037 | 91.1 % | 0.039 | 0 | 57 |
| es | 5 | 0 | — | — | 0.024 | 0.079 | 98.3 % | 0.081 | 0.039 | 98.5 % | 0.024 | 0 | 59 |
| fr | 5 | 0 | — | — | 0.030 | 0.053 | 99.2 % | 0.080 | -0.022 | 93.4 % | 0.033 | 0 | 58 |
| total | 20 | 0 | — | — | 0.030 | 0.096 | 98.5 % | 0.066 | 0.019 | 94.8 % | 0.028 | 0 | 59 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 5.9 | 3195 | 2303 | 0.205 |
| aligner | — | 1559 | 4052 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.051 | 94.9 % | 93.9 % | — | 46.4 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.043 | 100.0 % | 90.7 % | — | 37.6 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.046 | 92.4 % | 97.5 % | — | 49.2 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.043 | 92.3 % | 77.0 % | — | 60.0 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.057 | 98.3 % | 98.9 % | — | 50.8 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.024 | 100.0 % | 100.0 % | — | 37.1 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.019 | 99.3 % | 98.2 % | — | 46.7 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.023 | 100.0 % | 98.2 % | — | 58.0 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.030 | 95.3 % | 98.3 % | — | 43.6 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.027 | 100.0 % | 99.1 % | — | 45.9 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.044 | 100.0 % | 97.8 % | — | 44.0 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.020 | 99.7 % | 98.0 % | — | 60.6 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 97.7 % | 94.6 % | — | 54.4 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 99.8 % | 95.8 % | — | 51.4 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.032 | 100.0 % | 96.0 % | — | 51.0 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.025 | 100.0 % | 97.6 % | — | 43.4 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.031 | 96.8 % | 91.7 % | — | 32.3 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 96.5 % | — | 49.0 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.037 | 100.0 % | 88.1 % | — | 44.3 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.022 | 100.0 % | 94.1 % | — | 40.4 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.057 s
- Kinematic_-_Peyote: 0.051 s
- The_Rinn_-_Voices__2017_Version_: 0.046 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.046 s
- 1_Freak_-_Automatisch_Gekommen: 0.044 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
