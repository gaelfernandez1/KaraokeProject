# Banco · base-turbo · quick · sin letra

- Fecha: 2026-10-29T09:33:51+01:00
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
| de | 5 | 0 | 36.0 % | 26.9 % | 0.027 | 0.659 | 91.3 % | 0.061 | -0.541 | 73.5 % | — | 0 | 39 |
| en | 5 | 0 | 49.5 % | 40.5 % | 0.051 | 0.634 | 93.6 % | 0.058 | 0.488 | 53.8 % | — | 0 | 36 |
| es | 5 | 0 | 27.4 % | 21.0 % | 0.026 | 0.393 | 95.0 % | 0.082 | -0.242 | 77.6 % | — | 0 | 43 |
| fr | 5 | 0 | 32.3 % | 24.1 % | 0.030 | 0.166 | 96.1 % | 0.081 | -0.134 | 74.3 % | — | 0 | 39 |
| total | 20 | 0 | 36.8 % | 28.3 % | 0.031 | 0.460 | 94.0 % | 0.070 | -0.141 | 69.3 % | — | 0 | 40 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 3.1 | 804 | 3080 | 0.059 |
| transcriber | 5.5 | 1335 | 2068 | 0.052 |
| segmenter | — | 0 | 99 | 0.000 |
| aligner | — | 1559 | 4637 | 0.020 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | 45.9 % | 0.058 | 84.3 % | 86.4 % | en | 26.1 (caché) |  |
| Wordsmith_-_The_Statement | en | 171 | 29.8 % | 0.044 | 97.5 % | 69.4 % | en | 38.4 (caché) |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 100.0 % | — | — | — | en | 19.7 (caché) |  |
| Ridgway_-_Fire_Inside | en | 284 | 98.0 % | 96.845 | 0.0 % | 1.3 % | en | 29.2 (caché) |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 13.5 % | 0.061 | 93.5 % | 90.7 % | en | 29.7 (caché) |  |
| 10._Disparan_-_criatura | es | 160 | 51.5 % | 0.024 | 100.0 % | 50.0 % | es | 42.4 (caché) |  |
| Baila_-_Alfonso_Lugo | es | 210 | 20.1 % | 0.019 | 100.0 % | 85.1 % | es | 30.9 (caché) |  |
| Esencia_-_NandoMalo_ | es | 262 | 17.7 % | 0.023 | 98.4 % | 93.1 % | es | 35.1 (caché) |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 12.8 % | 0.034 | 88.5 % | 91.3 % | es | 28.7 (caché) |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 100.0 % | — | — | — | es | 20.9 (caché) |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 40.4 % | 0.050 | 81.8 % | 88.3 % | de | 28.2 (caché) |  |
| Der_Musiker_-_d-music | de | 271 | 49.5 % | 0.023 | 95.0 % | 56.2 % | de | 34.3 (caché) |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 100.0 % | — | — | — | de | 29.0 (caché) |  |
| Keine_Lust_-_Jonny_M | de | 229 | 15.1 % | 0.018 | 94.6 % | 84.1 % | de | 43.8 (caché) |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 27.2 % | 0.031 | 98.4 % | 85.4 % | de | 24.4 (caché) |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 70.6 % | 0.025 | 100.0 % | 29.8 % | fr | 20.8 (caché) |  |
| Confession_-_Quesabe | fr | 148 | 30.7 % | 0.029 | 90.8 % | 78.0 % | fr | 25.6 (caché) |  |
| Mère_nature_-_Law' | fr | 225 | 24.1 % | 0.040 | 95.0 % | 86.2 % | fr | 31.8 (caché) |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 25.0 % | 0.038 | 99.5 % | 81.7 % | fr | 24.4 (caché) |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 14.3 % | 0.023 | 98.7 % | 92.6 % | fr | 24.1 (caché) |  |

## Peores casos

Mayor mediana de error de inicio:
- Ridgway_-_Fire_Inside: 96.845 s
- Cortez_-_Feel__Stripped_: 0.061 s
- Kinematic_-_Peyote: 0.058 s
- 1_Freak_-_Automatisch_Gekommen: 0.050 s
- Wordsmith_-_The_Statement: 0.044 s

Mayor WER:
- The_Rinn_-_Voices__2017_Version_: 100.0 %
- Háblame_-_(Talk_to_me)_-_Brunela_Crochenci: 100.0 %
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 100.0 %
- Ridgway_-_Fire_Inside: 98.0 %
- Capotes_à_un_Franc_-_elmanu: 70.6 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
