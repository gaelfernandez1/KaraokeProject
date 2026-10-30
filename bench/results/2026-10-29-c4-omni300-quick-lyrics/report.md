# Banco · c4-omni300 · quick · con letra

- Fecha: 2026-10-29T15:50:53+01:00
- Commit: a35bb1a
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

Mel-Band RoFormer (Kim, 8 s) + Whisper large-v3-turbo + lyrics aligner (Omnilingual CTC 300M for every language)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v3 {'model': 'omni-ctc-300m'}

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | — | — | 0.024 | 0.180 | 95.7 % | 96.2 % | 0.062 | 0.011 | 83.7 % | 0.041 | 0 | 66 | 0.0 % | 24.8 % |
| en | 5 | 0 | — | — | 0.055 | 1.462 | 81.4 % | 82.7 % | 0.079 | 0.811 | 61.1 % | — | 0 | 65 | 0.0 % | 43.0 % |
| es | 5 | 0 | — | — | 0.028 | 0.430 | 93.2 % | 93.4 % | 0.091 | 0.323 | 76.6 % | 0.034 | 0 | 65 | 0.0 % | 15.0 % |
| fr | 5 | 0 | — | — | 0.033 | 0.449 | 94.5 % | 94.5 % | 0.092 | -0.042 | 64.5 % | 0.021 | 0 | 65 | 0.1 % | 23.3 % |
| total | 20 | 0 | — | — | 0.033 | 0.600 | 91.4 % | 92.0 % | 0.078 | 0.266 | 71.3 % | 0.026 | 0 | 65 | 0.0 % | 26.5 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.2 | 2867 | 2309 | 0.204 |
| aligner | 6.1 | 1577 | 2797 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.069 | 76.3 % | 76.3 % | 40.1 % | manual | 0.0 % | 21.7 % | — | 40.0 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.070 | 64.3 % | 67.2 % | 53.5 % | manual | 0.0 % | 76.3 % | — | 37.4 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.040 | 93.9 % | 96.3 % | 80.3 % | manual | 0.0 % | 56.0 % | — | 50.1 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.042 | 90.5 % | 90.5 % | 58.9 % | manual | 0.0 % | 44.4 % | — | 61.7 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.061 | 88.8 % | 88.8 % | 73.0 % | manual | 0.0 % | 16.4 % | — | 53.0 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.027 | 95.9 % | 95.9 % | 88.7 % | manual | 0.0 % | 15.1 % | — | 34.7 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.022 | 96.9 % | 96.9 % | 79.4 % | manual | 0.0 % | 17.9 % | — | 46.0 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.027 | 91.2 % | 91.2 % | 88.9 % | manual | 0.1 % | 8.9 % | — | 57.7 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.034 | 87.5 % | 88.2 % | 55.7 % | manual | 0.0 % | 14.3 % | — | 42.8 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.043 | 100.0 % | 100.0 % | 99.1 % | manual | 0.1 % | 18.9 % | — | 46.5 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.065 | 76.9 % | 77.5 % | 49.6 % | manual | 0.0 % | 50.0 % | — | 42.3 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.020 | 100.0 % | 100.0 % | 92.9 % | manual | 0.0 % | 9.2 % | — | 60.3 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.043 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 18.3 % | — | 54.0 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 97.8 % | 98.8 % | 95.8 % | manual | 0.0 % | 38.0 % | — | 51.2 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.034 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 8.6 % | — | 51.2 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.026 | 97.9 % | 97.9 % | 77.6 % | manual | 0.0 % | 8.5 % | — | 41.3 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.046 | 71.4 % | 71.4 % | 16.7 % | manual | 0.0 % | 59.1 % | — | 32.4 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.044 | 97.3 % | 97.3 % | 87.4 % | manual | 0.1 % | 19.3 % | — | 49.8 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.041 | 86.8 % | 86.8 % | 62.3 % | manual | 0.1 % | 21.1 % | — | 44.7 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.021 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 8.7 % | — | 40.8 |  |

## Peores casos

Mayor mediana de error de inicio:
- Wordsmith_-_The_Statement: 0.070 s
- Kinematic_-_Peyote: 0.069 s
- 1_Freak_-_Automatisch_Gekommen: 0.065 s
- Cortez_-_Feel__Stripped_: 0.061 s
- Confession_-_Quesabe: 0.046 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
