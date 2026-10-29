# Banco · sep-karaoke-aufr33 · quick · con letra

- Fecha: 2026-10-29T11:05:46+01:00
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

Mel-Band RoFormer karaoke model (aufr33 and viperx): lead vocals, backing vocals stay in the instrumental + Whisper large-v3-turbo + default CTC aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt'}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | — | — | 0.032 | 1.531 | 74.8 % | 0.082 | -0.643 | 96.8 % | 0.031 | 0 | 61 |
| en | 5 | 0 | — | — | 0.052 | 0.455 | 88.0 % | 0.064 | -0.141 | 91.1 % | 0.052 | 0 | 58 |
| es | 5 | 0 | — | — | 0.031 | 1.240 | 85.4 % | 0.094 | 0.523 | 98.5 % | 0.031 | 0 | 60 |
| fr | 5 | 0 | — | — | 0.031 | 0.243 | 95.1 % | 0.084 | -0.114 | 93.4 % | 0.034 | 0 | 60 |
| total | 20 | 0 | — | — | 0.036 | 0.881 | 85.5 % | 0.081 | -0.103 | 94.8 % | 0.035 | 0 | 60 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2309 | 0.204 |
| aligner | — | 1559 | 4162 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.051 | 94.2 % | 93.9 % | — | 47.3 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.055 | 77.0 % | 90.7 % | — | 37.4 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.051 | 88.9 % | 97.5 % | — | 48.9 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.044 | 92.7 % | 77.0 % | — | 60.0 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.055 | 98.3 % | 98.9 % | — | 51.3 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.025 | 99.5 % | 100.0 % | — | 36.7 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.047 | 58.1 % | 98.2 % | — | 46.6 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.037 | 83.2 % | 98.2 % | — | 58.4 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.030 | 94.2 % | 98.3 % | — | 43.2 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.027 | 100.0 % | 99.1 % | — | 46.3 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 1.171 | 33.4 % | 97.8 % | — | 44.2 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.023 | 90.8 % | 98.0 % | — | 60.9 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 97.7 % | 94.6 % | — | 53.7 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 100.0 % | 95.8 % | — | 51.8 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 1.392 | 37.2 % | 96.0 % | — | 50.8 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.025 | 100.0 % | 97.6 % | — | 42.5 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.029 | 96.1 % | 91.7 % | — | 32.4 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 96.5 % | — | 49.6 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.051 | 78.8 % | 88.1 % | — | 44.4 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.022 | 100.0 % | 94.1 % | — | 40.6 |  |

## Peores casos

Mayor mediana de error de inicio:
- Sehnsucht-Unplugged_-_REH-TORTE: 1.392 s
- 1_Freak_-_Automatisch_Gekommen: 1.171 s
- Wordsmith_-_The_Statement: 0.055 s
- Cortez_-_Feel__Stripped_: 0.055 s
- Pas_que_tes_pas_-_AZUL: 0.051 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
