# Banco · base-turbo · quick · con letra

- Fecha: 2026-10-29T09:39:29+01:00
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
| de | 5 | 0 | — | — | 0.025 | 0.107 | 98.9 % | 0.055 | -0.041 | 96.8 % | 0.026 | 0 | 23 |
| en | 5 | 0 | — | — | 0.048 | 0.171 | 96.3 % | 0.054 | 0.021 | 91.1 % | 0.043 | 0 | 20 |
| es | 5 | 0 | — | — | 0.025 | 0.077 | 98.3 % | 0.082 | 0.029 | 98.5 % | 0.025 | 0 | 22 |
| fr | 5 | 0 | — | — | 0.029 | 0.096 | 99.0 % | 0.078 | -0.065 | 93.4 % | 0.033 | 0 | 22 |
| total | 20 | 0 | — | — | 0.030 | 0.114 | 98.1 % | 0.065 | -0.013 | 94.8 % | 0.029 | 0 | 22 |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 3.9 | 797 | 2847 | 0.059 |
| aligner | — | 1559 | 4001 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.049 | 94.2 % | 93.9 % | — | 21.7 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.043 | 100.0 % | 90.7 % | — | 12.7 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.047 | 90.9 % | 97.5 % | — | 15.2 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.047 | 91.5 % | 77.0 % | — | 18.4 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.058 | 97.7 % | 98.9 % | — | 15.8 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.021 | 100.0 % | 100.0 % | — | 13.7 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.020 | 98.9 % | 98.2 % | — | 15.7 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.023 | 100.0 % | 98.2 % | — | 19.5 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.030 | 95.6 % | 98.3 % | — | 14.9 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.029 | 100.0 % | 99.1 % | — | 15.6 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.043 | 100.0 % | 97.8 % | — | 16.9 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.021 | 96.8 % | 98.0 % | — | 21.6 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 97.7 % | 94.6 % | — | 19.0 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.017 | 99.8 % | 95.8 % | — | 19.0 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.030 | 98.6 % | 96.0 % | — | 17.7 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.024 | 99.2 % | 97.6 % | — | 16.3 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.029 | 97.4 % | 91.7 % | — | 11.2 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 96.5 % | — | 16.6 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.039 | 98.7 % | 88.1 % | — | 15.0 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.023 | 100.0 % | 94.1 % | — | 13.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.058 s
- Kinematic_-_Peyote: 0.049 s
- Ridgway_-_Fire_Inside: 0.047 s
- The_Rinn_-_Voices__2017_Version_: 0.047 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.046 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
