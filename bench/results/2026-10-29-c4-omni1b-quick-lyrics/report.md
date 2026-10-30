# Banco · c4-omni1b · quick · con letra

- Fecha: 2026-10-29T15:52:48+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper large-v3-turbo + lyrics aligner (Omnilingual CTC 1B for every language)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v3 {'model': 'omni-ctc-1b'}

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | — | — | 0.025 | 0.052 | 99.6 % | 99.7 % | 0.067 | 0.038 | 92.6 % | 0.034 | 0 | 70 | 0.0 % | 9.9 % |
| en | 5 | 0 | — | — | 0.043 | 0.298 | 94.7 % | 95.0 % | 0.066 | -0.117 | 76.9 % | 3.484 | 0 | 68 | 0.0 % | 29.0 % |
| es | 5 | 0 | — | — | 0.029 | 0.248 | 95.4 % | 95.5 % | 0.094 | 0.126 | 87.1 % | 0.025 | 0 | 69 | 0.0 % | 9.9 % |
| fr | 5 | 0 | — | — | 0.035 | 0.099 | 98.7 % | 98.7 % | 0.088 | -0.003 | 77.9 % | 0.029 | 0 | 69 | 0.1 % | 18.1 % |
| total | 20 | 0 | — | — | 0.032 | 0.172 | 97.1 % | 97.3 % | 0.078 | 0.012 | 83.6 % | 0.049 | 0 | 69 | 0.0 % | 16.7 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.2 | 2867 | 2309 | 0.204 |
| aligner | 8.5 | 2973 | 5164 | 0.023 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.043 | 100.0 % | 100.0 % | 56.5 % | manual | 0.0 % | 14.3 % | — | 41.2 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.043 | 90.5 % | 90.7 % | 75.7 % | manual | 0.0 % | 57.7 % | — | 38.4 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.035 | 97.3 % | 98.9 % | 90.6 % | manual | 0.0 % | 32.6 % | — | 51.6 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.039 | 92.7 % | 92.7 % | 58.9 % | manual | 0.0 % | 30.5 % | — | 63.5 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.049 | 98.5 % | 98.5 % | 94.9 % | manual | 0.0 % | 9.7 % | — | 54.6 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.030 | 98.4 % | 98.4 % | 94.3 % | manual | 0.0 % | 6.6 % | — | 35.6 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.022 | 96.9 % | 96.9 % | 80.5 % | manual | 0.1 % | 14.1 % | — | 47.4 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.032 | 96.2 % | 96.2 % | 94.6 % | manual | 0.0 % | 6.2 % | — | 59.4 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.029 | 91.0 % | 91.3 % | 79.9 % | manual | 0.0 % | 10.2 % | — | 44.1 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.041 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 12.3 % | — | 47.8 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.051 | 99.0 % | 99.0 % | 85.8 % | manual | 0.0 % | 15.6 % | — | 43.6 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.020 | 99.7 % | 99.7 % | 92.9 % | manual | 0.0 % | 10.1 % | — | 62.2 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.042 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 15.1 % | — | 55.7 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 100.0 % | 100.0 % | 95.8 % | manual | 0.0 % | 4.6 % | — | 52.8 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.035 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 4.0 % | — | 52.9 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.028 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 4.4 % | — | 42.4 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.034 | 91.7 % | 91.7 % | 42.9 % | manual | 0.2 % | 67.5 % | — | 33.3 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.044 | 100.0 % | 100.0 % | 96.5 % | manual | 0.1 % | 7.5 % | — | 51.2 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.043 | 98.9 % | 98.9 % | 70.5 % | manual | 0.1 % | 8.3 % | — | 45.9 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.025 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 2.8 % | — | 42.1 |  |

## Peores casos

Mayor mediana de error de inicio:
- 1_Freak_-_Automatisch_Gekommen: 0.051 s
- Cortez_-_Feel__Stripped_: 0.049 s
- Mère_nature_-_Law': 0.044 s
- Kinematic_-_Peyote: 0.043 s
- Pas_que_tes_pas_-_AZUL: 0.043 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
