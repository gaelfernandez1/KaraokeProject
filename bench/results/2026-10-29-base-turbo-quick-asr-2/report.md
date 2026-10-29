# Banco · base-turbo · quick · sin letra

- Fecha: 2026-10-29T09:48:55+01:00
- Commit: 2244468
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

Demucs + Whisper large-v3-turbo (language given) + default CTC aligner

- **separator**: `karaoke_bench.baseline.separation:DemucsSeparator` v2
- **transcriber**: `karaoke_bench.baseline.whisper:FasterWhisperTranscriber` v1 {'model': 'large-v3-turbo'}
- **segmenter**: `karaoke_bench.baseline.segment:SegmentPerLine` v1
- **aligner**: `karaoke_bench.baseline.ctc:CtcAligner` v1

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | 30.5 % | 22.0 % | 0.025 | 0.162 | 97.2 % | 0.055 | -0.011 | 73.6 % | — | 0 | 36 |
| en | 5 | 0 | 52.9 % | 43.3 % | 0.052 | 0.728 | 92.8 % | 0.060 | 0.664 | 49.9 % | — | 0 | 40 |
| es | 5 | 0 | 31.7 % | 26.5 % | 0.026 | 0.463 | 93.6 % | 0.085 | -0.312 | 77.6 % | — | 0 | 43 |
| fr | 5 | 0 | 34.9 % | 27.2 % | 0.031 | 1.047 | 94.5 % | 0.082 | 0.668 | 74.4 % | — | 0 | 37 |
| total | 20 | 0 | 37.9 % | 29.7 % | 0.031 | 0.582 | 94.7 % | 0.069 | 0.216 | 68.3 % | — | 0 | 40 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 3.2 | 797 | 2850 | 0.059 |
| transcriber | 5.9 | 1335 | 2070 | 0.053 |
| segmenter | — | 0 | 92 | 0.000 |
| aligner | — | 1559 | 4116 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | 44.7 % | 0.051 | 92.1 % | 86.4 % | en | 34.1 |  |
| Wordsmith_-_The_Statement | en | 171 | 41.1 % | 0.050 | 92.0 % | 58.0 % | en | 36.3 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 100.0 % | — | — | — | en | 19.0 |  |
| Ridgway_-_Fire_Inside | en | 284 | 98.0 % | 96.845 | 0.0 % | 1.3 % | en | 28.1 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 11.0 % | 0.059 | 95.1 % | 91.8 % | en | 31.4 |  |
| 10._Disparan_-_criatura | es | 160 | 51.5 % | 0.024 | 100.0 % | 50.0 % | es | 34.6 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 41.5 % | 0.020 | 93.8 % | 85.1 % | es | 29.8 |  |
| Esencia_-_NandoMalo_ | es | 262 | 17.7 % | 0.023 | 98.4 % | 93.1 % | es | 33.6 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 12.8 % | 0.034 | 88.5 % | 91.3 % | es | 26.9 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 100.0 % | — | — | — | es | 19.5 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 18.6 % | 0.045 | 97.2 % | 88.3 % | de | 26.3 |  |
| Der_Musiker_-_d-music | de | 271 | 47.8 % | 0.021 | 99.5 % | 56.2 % | de | 29.8 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 100.0 % | — | — | — | de | 27.0 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 15.4 % | 0.017 | 95.7 % | 84.5 % | de | 33.8 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 27.2 % | 0.031 | 98.4 % | 85.4 % | de | 25.0 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 70.6 % | 0.031 | 81.1 % | 30.2 % | fr | 20.3 |  |
| Confession_-_Quesabe | fr | 148 | 39.7 % | 0.029 | 90.8 % | 78.0 % | fr | 24.7 |  |
| Mère_nature_-_Law' | fr | 225 | 26.1 % | 0.040 | 93.6 % | 86.2 % | fr | 28.9 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 25.0 % | 0.038 | 99.5 % | 81.7 % | fr | 22.9 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 14.3 % | 0.023 | 98.7 % | 92.6 % | fr | 21.1 |  |

## Peores casos

Mayor mediana de error de inicio:
- Ridgway_-_Fire_Inside: 96.845 s
- Cortez_-_Feel__Stripped_: 0.059 s
- Kinematic_-_Peyote: 0.051 s
- Wordsmith_-_The_Statement: 0.050 s
- 1_Freak_-_Automatisch_Gekommen: 0.045 s

Mayor WER:
- The_Rinn_-_Voices__2017_Version_: 100.0 %
- Háblame_-_(Talk_to_me)_-_Brunela_Crochenci: 100.0 %
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 100.0 %
- Ridgway_-_Fire_Inside: 98.0 %
- Capotes_à_un_Franc_-_elmanu: 70.6 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
