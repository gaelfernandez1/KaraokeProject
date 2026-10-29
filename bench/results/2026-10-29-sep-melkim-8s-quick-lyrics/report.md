# Banco · sep-melkim-8s · quick · con letra

- Fecha: 2026-10-29T12:12:58+01:00
- Commit: ecb1e20
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
| de | 5 | 0 | — | — | 0.024 | 0.036 | 99.7 % | 0.055 | 0.020 | 96.8 % | 0.024 | 0 | 60 |
| en | 5 | 0 | — | — | 0.047 | 0.241 | 96.7 % | 0.056 | 0.007 | 91.1 % | 0.039 | 0 | 57 |
| es | 5 | 0 | — | — | 0.024 | 0.079 | 98.4 % | 0.082 | 0.042 | 98.5 % | 0.024 | 0 | 59 |
| fr | 5 | 0 | — | — | 0.030 | 0.052 | 99.3 % | 0.080 | -0.022 | 93.4 % | 0.033 | 0 | 59 |
| total | 20 | 0 | — | — | 0.030 | 0.104 | 98.5 % | 0.066 | 0.012 | 94.8 % | 0.028 | 0 | 59 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.2 | 2867 | 2309 | 0.204 |
| aligner | — | 1559 | 3903 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.050 | 95.7 % | 93.9 % | — | 46.8 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.043 | 99.8 % | 90.7 % | — | 36.4 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.048 | 91.4 % | 97.5 % | — | 48.1 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.044 | 92.3 % | 77.0 % | — | 59.2 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.057 | 98.3 % | 98.9 % | — | 51.0 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.024 | 100.0 % | 100.0 % | — | 36.3 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.019 | 100.0 % | 98.2 % | — | 46.2 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.023 | 100.0 % | 98.2 % | — | 58.0 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.030 | 95.3 % | 98.3 % | — | 43.3 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.026 | 100.0 % | 99.1 % | — | 46.0 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.045 | 100.0 % | 97.8 % | — | 43.7 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.021 | 99.4 % | 98.0 % | — | 60.5 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 97.7 % | 94.6 % | — | 53.7 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 99.8 % | 95.8 % | — | 51.7 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.031 | 100.0 % | 96.0 % | — | 51.0 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.025 | 100.0 % | 97.6 % | — | 43.0 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.031 | 97.1 % | 91.7 % | — | 32.5 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 96.5 % | — | 49.8 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.037 | 100.0 % | 88.1 % | — | 44.7 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.022 | 100.0 % | 94.1 % | — | 40.9 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.057 s
- Kinematic_-_Peyote: 0.050 s
- The_Rinn_-_Voices__2017_Version_: 0.048 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.046 s
- 1_Freak_-_Automatisch_Gekommen: 0.045 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
