# Banco · c4-default · quick · con letra

- Fecha: 2026-10-29T20:00:45+01:00
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
| de | 5 | 0 | — | — | 0.024 | 0.035 | 99.7 % | 99.8 % | 0.056 | 0.020 | 96.8 % | — | 0 | 59 | 0.0 % | 18.0 % |
| en | 5 | 0 | — | — | 0.056 | 0.122 | 98.4 % | 98.6 % | 0.045 | 0.001 | 90.3 % | — | 0 | 58 | 0.1 % | 29.7 % |
| es | 5 | 0 | — | — | 0.024 | 0.056 | 99.4 % | 99.5 % | 0.081 | 0.022 | 97.4 % | — | 0 | 59 | 0.0 % | 24.5 % |
| fr | 5 | 0 | — | — | 0.029 | 0.038 | 99.9 % | 99.9 % | 0.079 | -0.013 | 92.2 % | — | 0 | 59 | 0.0 % | 24.2 % |
| total | 20 | 0 | — | — | 0.032 | 0.064 | 99.3 % | 99.4 % | 0.063 | 0.008 | 94.1 % | — | 0 | 59 | 0.0 % | 24.1 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.2 | 2867 | 2309 | 0.204 |
| aligner | 0.1 | 1559 | 3716 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.052 | 97.1 % | 97.8 % | 93.9 % | manual | 0.7 % | 28.7 % | — | 41.5 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.054 | 100.0 % | 100.0 % | 89.8 % | manual | 0.0 % | 30.8 % | — | 37.2 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.052 | 98.9 % | 100.0 % | 93.6 % | manual | 0.0 % | 46.1 % | — | 49.8 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.049 | 92.7 % | 92.7 % | 77.0 % | manual | 0.0 % | 30.9 % | — | 61.4 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.068 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 12.1 % | — | 52.7 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.024 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.2 % | — | 36.3 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.019 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 29.8 % | — | 45.9 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 19.5 % | — | 57.5 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.029 | 98.2 % | 98.4 % | 94.8 % | manual | 0.0 % | 16.3 % | — | 42.7 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.027 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 34.9 % | — | 46.1 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.044 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 32.5 % | — | 52.9 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.021 | 99.4 % | 99.7 % | 98.0 % | manual | 0.0 % | 13.8 % | — | 60.0 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 97.7 % | 98.9 % | 94.6 % | manual | 0.0 % | 20.4 % | — | 53.6 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 99.8 % | 99.8 % | 95.8 % | manual | 0.0 % | 8.2 % | — | 51.0 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.031 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 15.2 % | — | 51.0 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.025 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 7.7 % | — | 42.8 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.029 | 99.7 % | 99.7 % | 86.9 % | manual | 0.2 % | 42.9 % | — | 32.2 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 18.3 % | — | 49.5 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.036 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 38.1 % | — | 44.5 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.022 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 14.3 % | — | 40.7 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.068 s
- Wordsmith_-_The_Statement: 0.054 s
- Kinematic_-_Peyote: 0.052 s
- The_Rinn_-_Voices__2017_Version_: 0.052 s
- Ridgway_-_Fire_Inside: 0.049 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
