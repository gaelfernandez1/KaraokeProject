# Banco · c4-asr-turbo · quick · sin letra

- Fecha: 2026-10-29T19:39:01+01:00
- Commit: 3cdccd5
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

Mel-Band RoFormer (Kim, 8 s) + Whisper large-v3-turbo (VAD, voice check, fixed seed) + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v1
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v11

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | 19.7 % | 14.2 % | 0.026 | 0.226 | 95.9 % | 96.2 % | 0.057 | 0.106 | 80.2 % | — | 0 | 70 | 0.0 % | 14.5 % |
| en | 5 | 0 | 28.7 % | 23.7 % | 0.059 | 1.071 | 96.1 % | 96.4 % | 0.048 | 0.931 | 68.2 % | — | 0 | 68 | 0.0 % | 25.3 % |
| es | 5 | 0 | 11.3 % | 7.0 % | 0.024 | 0.067 | 98.9 % | 99.0 % | 0.080 | 0.017 | 90.0 % | — | 0 | 70 | 0.0 % | 22.6 % |
| fr | 5 | 0 | 19.4 % | 12.9 % | 0.030 | 0.041 | 99.8 % | 99.8 % | 0.081 | -0.008 | 82.3 % | — | 0 | 71 | 0.0 % | 23.6 % |
| total | 20 | 0 | 20.1 % | 14.7 % | 0.032 | 0.337 | 97.7 % | 97.9 % | 0.066 | 0.248 | 79.7 % | — | 0 | 70 | 0.0 % | 21.5 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.2 | 2867 | 2309 | 0.204 |
| transcriber | 4.7 | 1335 | 2071 | 0.029 |
| segmenter | — | 0 | 80 | 0.000 |
| aligner | 0.1 | 1559 | 3730 | 0.015 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | 25.2 % | 0.055 | 96.7 % | 97.5 % | 81.6 % | manual | 0.0 % | 29.5 % | en | 45.5 |  |
| Wordsmith_-_The_Statement | en | 171 | 30.5 % | 0.056 | 98.5 % | 98.5 % | 66.8 % | manual | 0.0 % | 30.2 % | en | 58.8 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 58.4 % | 0.078 | 78.8 % | 81.2 % | 41.9 % | manual | 0.0 % | 30.5 % | en | 53.1 |  |
| Ridgway_-_Fire_Inside | en | 284 | 29.7 % | 0.047 | 97.7 % | 97.7 % | 56.9 % | manual | 0.0 % | 25.1 % | en | 67.0 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 9.6 % | 0.072 | 96.9 % | 96.9 % | 89.9 % | manual | 0.0 % | 11.2 % | en | 61.6 |  |
| 10._Disparan_-_criatura | es | 160 | 11.3 % | 0.024 | 99.4 % | 99.4 % | 89.2 % | manual | 0.0 % | 22.7 % | es | 40.6 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 9.2 % | 0.019 | 100.0 % | 100.0 % | 91.1 % | manual | 0.0 % | 27.9 % | es | 52.3 |  |
| Esencia_-_NandoMalo_ | es | 262 | 15.6 % | 0.023 | 99.7 % | 99.7 % | 88.0 % | manual | 0.0 % | 12.7 % | es | 64.6 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 8.5 % | 0.028 | 97.9 % | 98.1 % | 92.6 % | manual | 0.0 % | 15.4 % | es | 50.8 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 16.0 % | 0.030 | 97.8 % | 97.8 % | 84.0 % | manual | 0.0 % | 34.4 % | es | 49.9 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 9.0 % | 0.045 | 97.6 % | 97.6 % | 90.5 % | manual | 0.0 % | 32.0 % | de | 55.8 |  |
| Der_Musiker_-_d-music | de | 271 | 19.1 % | 0.020 | 100.0 % | 100.0 % | 83.9 % | manual | 0.0 % | 9.1 % | de | 66.4 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 15.1 % | 0.051 | 97.4 % | 98.7 % | 82.6 % | manual | 0.0 % | 11.0 % | de | 56.9 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 26.7 % | 0.018 | 89.9 % | 90.7 % | 71.2 % | manual | 0.0 % | 7.4 % | de | 65.8 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 25.2 % | 0.033 | 99.1 % | 99.1 % | 76.2 % | manual | 0.1 % | 13.1 % | de | 55.0 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 10.2 % | 0.025 | 99.5 % | 99.5 % | 89.4 % | manual | 0.0 % | 7.3 % | fr | 48.5 |  |
| Confession_-_Quesabe | fr | 148 | 40.0 % | 0.030 | 100.0 % | 100.0 % | 59.8 % | manual | 0.0 % | 35.9 % | fr | 37.0 |  |
| Mère_nature_-_Law' | fr | 225 | 15.4 % | 0.037 | 100.0 % | 100.0 % | 89.0 % | manual | 0.0 % | 20.5 % | fr | 55.9 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 14.7 % | 0.037 | 100.0 % | 100.0 % | 85.8 % | manual | 0.0 % | 41.5 % | fr | 51.3 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 10.3 % | 0.022 | 99.6 % | 99.6 % | 94.9 % | manual | 0.0 % | 13.0 % | fr | 46.6 |  |

## Peores casos

Mayor mediana de error de inicio:
- The_Rinn_-_Voices__2017_Version_: 0.078 s
- Cortez_-_Feel__Stripped_: 0.072 s
- Wordsmith_-_The_Statement: 0.056 s
- Kinematic_-_Peyote: 0.055 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.051 s

Mayor WER:
- The_Rinn_-_Voices__2017_Version_: 58.4 %
- Confession_-_Quesabe: 40.0 %
- Wordsmith_-_The_Statement: 30.5 %
- Ridgway_-_Fire_Inside: 29.7 %
- Keine_Lust_-_Jonny_M: 26.7 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
