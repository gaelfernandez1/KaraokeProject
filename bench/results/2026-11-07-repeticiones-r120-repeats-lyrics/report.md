# Banco · repeticiones-r120 · repeats · con letra

- Fecha: 2026-11-07T19:42:52+01:00
- Commit: 016d5af-dirty
- Banco 3.0.0, normalización v1
- Referencias: de manual, en manual, es manual, fr manual

## Entorno

| Clave | Valor |
|---|---|
| ctranslate2 | 4.8.5 |
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
| transformers | 5.22.1 |

## Pipeline

c4-default with stanza repeats at a cost of 120 and repeat marks read by the audio (sweep of decision 016)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'repeat_penalty': 120.0}

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| repeats-marked | 44 | 0 | — | — | 0.034 | 0.073 | 98.8 % | 99.0 % | 0.073 | 0.023 | 90.6 % | — | 0 | 66 | 0.1 % | 25.0 % |
| repeats-unmarked | 44 | 0 | — | — | 0.035 | 0.259 | 95.8 % | 96.0 % | 0.075 | 0.097 | 86.8 % | — | 0 | 60 | 0.1 % | 24.3 % |
| total | 88 | 0 | — | — | 0.035 | 0.164 | 97.3 % | 97.5 % | 0.074 | 0.059 | 88.7 % | — | 0 | 60 | 0.1 % | 24.7 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.9 | 2867 | 2388 | 0.205 |
| aligner | 0.1 | 1559 | 3734 | 0.018 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| marked-10._Disparan_-_criatura | es | 160 | — | 0.024 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.2 % | — | 37.5 (caché) |  |
| marked-1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.044 | 100.0 % | 100.0 % | 96.7 % | manual | 0.0 % | 32.6 % | — | 51.7 (caché) |  |
| marked-Besando_Sapos_-_Dream_Tabu | es | 251 | — | 0.032 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 26.8 % | — | 55.7 (caché) |  |
| marked-Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | 0.038 | 99.7 % | 99.7 % | 98.9 % | manual | 0.0 % | 23.5 % | — | 73.9 (caché) |  |
| marked-Burn_Out_Man_-_Abendblau | de | 260 | — | 0.039 | 99.7 % | 99.7 % | 86.7 % | manual | 0.0 % | 9.3 % | — | 61.5 (caché) |  |
| marked-CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | 0.036 | 99.6 % | 99.6 % | 64.3 % | manual | 0.0 % | 47.2 % | — | 65.3 (caché) |  |
| marked-CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | 0.037 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 14.1 % | — | 51.3 (caché) |  |
| marked-Confession_-_Quesabe | fr | 148 | — | 0.029 | 99.7 % | 99.7 % | 86.9 % | manual | 0.2 % | 42.9 % | — | 36.8 (caché) |  |
| marked-Cortez_-_Feel__Stripped_ | en | 241 | — | 0.068 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 12.1 % | — | 61.2 (caché) |  |
| marked-Culture_&_Co._-_cool.cavemen | fr | 212 | — | 0.034 | 95.2 % | 96.8 % | 93.9 % | manual | 0.0 % | 62.3 % | — | 47.0 (caché) |  |
| marked-DON_VALDES_-_Tu_sais_Man | fr | 209 | — | 0.032 | 96.4 % | 96.9 % | 76.6 % | manual | 0.0 % | 45.1 % | — | 46.7 (caché) |  |
| marked-Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | 0.028 | 100.0 % | 100.0 % | 95.5 % | manual | 0.0 % | 11.5 % | — | 49.8 (caché) |  |
| marked-Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | 0.028 | 97.3 % | 97.9 % | 93.6 % | manual | 0.0 % | 39.1 % | — | 45.7 |  |
| marked-Drei_Nüsse_-_patrouille | de | 259 | — | 0.026 | 99.8 % | 100.0 % | 98.5 % | manual | 0.0 % | 7.5 % | — | 65.3 (caché) |  |
| marked-Esencia_-_NandoMalo_ | es | 262 | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 19.5 % | — | 76.9 (caché) |  |
| marked-Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | 0.049 | 100.0 % | 100.0 % | 99.6 % | manual | 0.5 % | 23.1 % | — | 48.4 (caché) |  |
| marked-Fantasma_-_Los_Rombos | es | 166 | — | 0.037 | 97.2 % | 98.6 % | 81.8 % | manual | 0.4 % | 16.0 % | — | 39.4 (caché) |  |
| marked-Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | 0.023 | 100.0 % | 100.0 % | 100.0 % | manual | 0.1 % | 2.6 % | — | 57.1 (caché) |  |
| marked-Guayeteo_-_JhoyKing | es | 158 | — | 0.027 | 99.3 % | 99.7 % | 84.1 % | manual | 0.0 % | 27.9 % | — | 39.6 (caché) |  |
| marked-Intentando_Destacar_-_Sundayers_ | es | 220 | — | 0.023 | 100.0 % | 100.0 % | 80.4 % | manual | 0.0 % | 14.4 % | — | 50.8 (caché) |  |
| marked-Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 99.8 % | 99.8 % | 95.8 % | manual | 0.0 % | 8.2 % | — | 63.7 (caché) |  |
| marked-LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | 0.062 | 99.3 % | 99.3 % | 99.7 % | manual | 0.0 % | 13.2 % | — | 59.8 (caché) |  |
| marked-La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | 0.028 | 100.0 % | 100.0 % | 100.0 % | manual | 0.1 % | 15.1 % | — | 49.9 (caché) |  |
| marked-Les_files_d'attente_-_Law' | fr | 196 | — | 0.031 | 99.1 % | 99.5 % | 66.5 % | manual | 0.0 % | 29.5 % | — | 45.3 (caché) |  |
| marked-Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | 0.029 | 99.7 % | 100.0 % | 96.5 % | manual | 0.0 % | 33.6 % | — | 57.9 (caché) |  |
| marked-Lower_Loveday_-_Is_It_Right_ | en | 180 | — | 0.056 | 99.5 % | 99.5 % | 96.7 % | manual | 0.0 % | 16.5 % | — | 43.8 (caché) |  |
| marked-Mes_Larmes_-_kobzx2z | fr | 159 | — | 0.024 | 94.7 % | 94.7 % | 63.4 % | manual | 0.0 % | 47.7 % | — | 46.0 (caché) |  |
| marked-Moon_I_Mean_-_Wrong_Concept | en | 220 | — | 0.050 | 99.6 % | 99.6 % | 95.2 % | manual | 0.0 % | 54.9 % | — | 52.3 (caché) |  |
| marked-Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 18.3 % | — | 52.0 (caché) |  |
| marked-Palabras_-_Javier_Gomez_Bello | es | 216 | — | 0.030 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 8.5 % | — | 54.2 (caché) |  |
| marked-Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | 0.045 | 90.2 % | 90.2 % | 91.0 % | manual | 0.3 % | 37.7 % | — | 50.6 (caché) |  |
| marked-Pure_Mids_-_The_Leader | en | 262 | — | 0.071 | 96.3 % | 96.3 % | 71.9 % | manual | 0.8 % | 72.5 % | — | 59.2 (caché) |  |
| marked-Quentin_Hannappe_-_Keep_On | en | 190 | — | 0.044 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 20.7 % | — | 47.0 (caché) |  |
| marked-Ridgway_-_Fire_Inside | en | 284 | — | 0.051 | 91.2 % | 91.2 % | 75.0 % | manual | 0.0 % | 29.5 % | — | 73.3 |  |
| marked-Rxbyn_-_Bad_Side | en | 217 | — | 0.057 | 98.8 % | 99.0 % | 95.5 % | manual | 0.0 % | 24.4 % | — | 51.3 (caché) |  |
| marked-Schnodderdodder_-_Abendblau | de | 197 | — | 0.022 | 99.3 % | 100.0 % | 95.9 % | manual | 0.0 % | 16.4 % | — | 49.7 (caché) |  |
| marked-Slingshot_Miracle_-_Whistler | en | 229 | — | 0.064 | 98.8 % | 100.0 % | 98.8 % | manual | 0.0 % | 26.4 % | — | 50.9 (caché) |  |
| marked-Séculaire_feat._Nÿme_-_saru | fr | 159 | — | 0.023 | 98.7 % | 98.7 % | 87.8 % | manual | 0.1 % | 25.2 % | — | 37.0 (caché) |  |
| marked-Vente_-_Fafarulo_Calabaza | es | 336 | — | 0.034 | 100.0 % | 100.0 % | 96.6 % | manual | 0.8 % | 10.5 % | — | 79.9 (caché) |  |
| marked-Wordsmith_-_The_Statement | en | 171 | — | 0.056 | 93.8 % | 93.8 % | 80.6 % | manual | 0.0 % | 28.6 % | — | 60.5 (caché) |  |
| marked-Yuanan_-_Miedo_-_Yuanan | es | 169 | — | 0.027 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 19.7 % | — | 41.5 (caché) |  |
| marked-de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | 0.030 | 99.6 % | 100.0 % | 97.0 % | manual | 0.0 % | 17.5 % | — | 39.2 (caché) |  |
| marked-dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | 0.029 | 98.9 % | 100.0 % | 97.8 % | manual | 0.0 % | 11.0 % | — | 44.2 (caché) |  |
| marked-¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | 0.034 | 98.5 % | 99.0 % | 98.1 % | manual | 0.0 % | 14.8 % | — | 51.3 (caché) |  |
| unmarked-10._Disparan_-_criatura | es | 160 | — | 0.024 | 98.4 % | 98.4 % | 96.9 % | manual | 0.0 % | 22.3 % | — | 34.9 (caché) |  |
| unmarked-1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.044 | 97.7 % | 97.7 % | 95.6 % | manual | 0.0 % | 32.4 % | — | 42.1 (caché) |  |
| unmarked-Besando_Sapos_-_Dream_Tabu | es | 251 | — | 0.033 | 99.1 % | 99.1 % | 98.2 % | manual | 0.0 % | 27.2 % | — | 55.3 (caché) |  |
| unmarked-Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | 0.040 | 94.6 % | 94.6 % | 89.2 % | manual | 0.0 % | 21.9 % | — | 60.5 (caché) |  |
| unmarked-Burn_Out_Man_-_Abendblau | de | 260 | — | 0.039 | 99.7 % | 99.7 % | 86.7 % | manual | 0.0 % | 9.0 % | — | 57.1 (caché) |  |
| unmarked-CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | 0.036 | 93.5 % | 93.5 % | 62.0 % | manual | 0.0 % | 48.5 % | — | 52.3 (caché) |  |
| unmarked-CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | 0.045 | 89.9 % | 89.9 % | 92.2 % | manual | 0.0 % | 12.6 % | — | 47.7 (caché) |  |
| unmarked-Confession_-_Quesabe | fr | 148 | — | 0.029 | 99.7 % | 99.7 % | 86.9 % | manual | 0.2 % | 42.7 % | — | 32.4 (caché) |  |
| unmarked-Cortez_-_Feel__Stripped_ | en | 241 | — | 0.068 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 12.1 % | — | 53.0 (caché) |  |
| unmarked-Culture_&_Co._-_cool.cavemen | fr | 212 | — | 0.034 | 95.2 % | 96.8 % | 93.9 % | manual | 0.0 % | 62.3 % | — | 46.9 (caché) |  |
| unmarked-DON_VALDES_-_Tu_sais_Man | fr | 209 | — | 0.032 | 96.1 % | 96.6 % | 76.0 % | manual | 0.0 % | 45.0 % | — | 46.6 (caché) |  |
| unmarked-Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | 0.028 | 100.0 % | 100.0 % | 95.5 % | manual | 0.0 % | 11.5 % | — | 46.0 (caché) |  |
| unmarked-Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | 0.029 | 96.5 % | 97.2 % | 92.3 % | manual | 0.0 % | 38.9 % | — | 36.3 |  |
| unmarked-Drei_Nüsse_-_patrouille | de | 259 | — | 0.026 | 99.8 % | 100.0 % | 98.5 % | manual | 0.0 % | 7.5 % | — | 57.2 (caché) |  |
| unmarked-Esencia_-_NandoMalo_ | es | 262 | — | 0.024 | 91.2 % | 91.2 % | 88.6 % | manual | 0.0 % | 19.3 % | — | 57.5 (caché) |  |
| unmarked-Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | 0.049 | 100.0 % | 100.0 % | 99.6 % | manual | 0.4 % | 21.7 % | — | 42.5 (caché) |  |
| unmarked-Fantasma_-_Los_Rombos | es | 166 | — | 0.037 | 97.2 % | 98.6 % | 81.8 % | manual | 0.4 % | 16.0 % | — | 36.1 (caché) |  |
| unmarked-Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | 0.023 | 100.0 % | 100.0 % | 100.0 % | manual | 0.1 % | 2.6 % | — | 53.6 (caché) |  |
| unmarked-Guayeteo_-_JhoyKing | es | 158 | — | 0.026 | 98.8 % | 98.8 % | 72.1 % | manual | 0.0 % | 25.3 % | — | 34.8 (caché) |  |
| unmarked-Intentando_Destacar_-_Sundayers_ | es | 220 | — | 0.023 | 100.0 % | 100.0 % | 80.4 % | manual | 0.0 % | 14.4 % | — | 48.8 (caché) |  |
| unmarked-Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 99.2 % | 99.2 % | 94.3 % | manual | 0.0 % | 8.3 % | — | 51.1 (caché) |  |
| unmarked-LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | 0.067 | 88.6 % | 88.6 % | 88.5 % | manual | 0.0 % | 13.7 % | — | 48.9 (caché) |  |
| unmarked-La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | 0.034 | 89.0 % | 89.0 % | 89.3 % | manual | 0.1 % | 9.5 % | — | 41.3 (caché) |  |
| unmarked-Les_files_d'attente_-_Law' | fr | 196 | — | 0.032 | 97.6 % | 98.1 % | 65.2 % | manual | 0.0 % | 28.3 % | — | 43.1 (caché) |  |
| unmarked-Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | 0.029 | 99.7 % | 100.0 % | 96.5 % | manual | 0.0 % | 33.6 % | — | 48.1 (caché) |  |
| unmarked-Lower_Loveday_-_Is_It_Right_ | en | 180 | — | 0.056 | 99.5 % | 99.5 % | 96.7 % | manual | 0.0 % | 16.5 % | — | 39.6 (caché) |  |
| unmarked-Mes_Larmes_-_kobzx2z | fr | 159 | — | 0.030 | 81.0 % | 81.0 % | 59.8 % | manual | 0.0 % | 47.6 % | — | 34.7 (caché) |  |
| unmarked-Moon_I_Mean_-_Wrong_Concept | en | 220 | — | 0.050 | 99.2 % | 99.2 % | 94.5 % | manual | 0.0 % | 55.3 % | — | 48.1 (caché) |  |
| unmarked-Mère_nature_-_Law' | fr | 225 | — | 0.038 | 96.2 % | 96.2 % | 92.9 % | manual | 0.0 % | 17.7 % | — | 49.7 (caché) |  |
| unmarked-Palabras_-_Javier_Gomez_Bello | es | 216 | — | 0.032 | 96.3 % | 96.3 % | 89.6 % | manual | 0.0 % | 7.3 % | — | 47.4 (caché) |  |
| unmarked-Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | 0.053 | 81.4 % | 81.4 % | 76.1 % | manual | 0.7 % | 30.8 % | — | 44.7 (caché) |  |
| unmarked-Pure_Mids_-_The_Leader | en | 262 | — | 0.071 | 96.3 % | 96.3 % | 71.9 % | manual | 0.8 % | 72.5 % | — | 57.4 (caché) |  |
| unmarked-Quentin_Hannappe_-_Keep_On | en | 190 | — | 0.051 | 88.5 % | 88.5 % | 84.6 % | manual | 0.0 % | 18.2 % | — | 41.9 (caché) |  |
| unmarked-Ridgway_-_Fire_Inside | en | 284 | — | 0.052 | 92.6 % | 92.6 % | 71.1 % | manual | 0.0 % | 28.2 % | — | 61.8 |  |
| unmarked-Rxbyn_-_Bad_Side | en | 217 | — | 0.057 | 97.5 % | 97.8 % | 91.8 % | manual | 0.0 % | 25.7 % | — | 48.4 (caché) |  |
| unmarked-Schnodderdodder_-_Abendblau | de | 197 | — | 0.022 | 95.1 % | 95.9 % | 91.8 % | manual | 0.0 % | 15.0 % | — | 44.1 (caché) |  |
| unmarked-Slingshot_Miracle_-_Whistler | en | 229 | — | 0.067 | 94.9 % | 97.5 % | 97.5 % | manual | 0.0 % | 25.0 % | — | 50.6 (caché) |  |
| unmarked-Séculaire_feat._Nÿme_-_saru | fr | 159 | — | 0.023 | 98.3 % | 98.3 % | 87.5 % | manual | 0.1 % | 24.6 % | — | 34.9 (caché) |  |
| unmarked-Vente_-_Fafarulo_Calabaza | es | 336 | — | 0.034 | 99.4 % | 99.4 % | 94.9 % | manual | 0.9 % | 9.9 % | — | 74.9 (caché) |  |
| unmarked-Wordsmith_-_The_Statement | en | 171 | — | 0.063 | 80.6 % | 80.9 % | 66.6 % | manual | 0.0 % | 27.4 % | — | 37.1 (caché) |  |
| unmarked-Yuanan_-_Miedo_-_Yuanan | es | 169 | — | 0.027 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 19.4 % | — | 37.6 (caché) |  |
| unmarked-de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | 0.030 | 99.6 % | 100.0 % | 97.0 % | manual | 0.0 % | 17.5 % | — | 35.9 (caché) |  |
| unmarked-dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | 0.034 | 89.9 % | 90.5 % | 93.4 % | manual | 0.0 % | 9.8 % | — | 42.5 (caché) |  |
| unmarked-¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | 0.048 | 81.9 % | 82.5 % | 81.4 % | manual | 0.0 % | 14.9 % | — | 39.5 (caché) |  |

## Peores casos

Mayor mediana de error de inicio:
- marked-Pure_Mids_-_The_Leader: 0.071 s
- unmarked-Pure_Mids_-_The_Leader: 0.071 s
- marked-Cortez_-_Feel__Stripped_: 0.068 s
- unmarked-Cortez_-_Feel__Stripped_: 0.068 s
- unmarked-LUNABLIND_-_Vision__Radio_Edit_: 0.067 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
