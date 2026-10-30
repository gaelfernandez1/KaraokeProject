# Banco · c4-default · jamendo · sin letra

- Fecha: 2026-10-29T21:03:58+01:00
- Commit: 22522ba-dirty
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
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v11

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 20 | 0 | 14.2 % | 9.0 % | 0.030 | 0.132 | 98.2 % | 98.5 % | 0.073 | 0.110 | 85.4 % | — | 0 | 64 | 0.0 % | 16.7 % |
| en | 20 | 0 | 33.5 % | 27.6 % | 0.058 | 0.759 | 96.5 % | 96.8 % | 0.055 | 0.406 | 70.6 % | — | 0 | 64 | 0.0 % | 27.5 % |
| es | 20 | 0 | 15.7 % | 9.9 % | 0.028 | 0.138 | 98.6 % | 98.7 % | 0.092 | 0.059 | 87.3 % | — | 0 | 64 | 0.0 % | 17.1 % |
| fr | 19 | 0 | 27.5 % | 16.7 % | 0.030 | 0.071 | 98.5 % | 98.7 % | 0.081 | 0.015 | 73.8 % | — | 0 | 65 | 0.0 % | 27.5 % |
| total | 79 | 0 | 23.2 % | 16.0 % | 0.034 | 0.267 | 98.0 % | 98.2 % | 0.075 | 0.144 | 79.0 % | — | 0 | 64 | 0.0 % | 22.1 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.9 | 2867 | 2388 | 0.204 |
| transcriber | 0.1 | 1335 | 2117 | 0.021 |
| segmenter | — | 0 | 94 | 0.000 |
| aligner | 0.1 | 1559 | 3787 | 0.014 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | 43.3 % | 0.026 | 86.4 % | 86.4 % | 56.7 % | manual | 0.0 % | 28.5 % | es | 43.7 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 9.0 % | 0.044 | 97.6 % | 97.6 % | 90.5 % | manual | 0.0 % | 31.9 % | de | 55.8 |  |
| Avercage_-_Embers | en | 243 | 80.5 % | 1.037 | 48.7 % | 48.7 % | 20.6 % | manual | 0.0 % | 82.9 % | en | 56.7 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 9.9 % | 0.019 | 100.0 % | 100.0 % | 91.1 % | manual | 0.0 % | 27.9 % | es | 50.2 |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | 7.9 % | 0.033 | 97.7 % | 97.7 % | 94.7 % | manual | 0.0 % | 27.5 % | es | 59.9 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | 6.8 % | 0.038 | 99.7 % | 99.7 % | 94.1 % | manual | 0.0 % | 22.8 % | de | 68.1 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | 7.5 % | 0.039 | 98.6 % | 99.0 % | 86.7 % | manual | 0.0 % | 10.6 % | de | 62.9 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | 53.3 % | 0.034 | 95.8 % | 95.8 % | 47.7 % | manual | 0.0 % | 40.0 % | fr | 57.0 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | 9.2 % | 0.036 | 98.9 % | 99.5 % | 92.6 % | manual | 0.0 % | 13.8 % | es | 51.3 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 14.0 % | 0.049 | 97.4 % | 98.7 % | 83.7 % | manual | 0.0 % | 12.1 % | de | 56.0 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 10.6 % | 0.025 | 99.5 % | 99.5 % | 89.0 % | manual | 0.0 % | 6.9 % | fr | 45.2 |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | 21.2 % | 0.030 | 95.8 % | 95.8 % | 78.7 % | manual | 0.0 % | 22.9 % | es | 64.2 |  |
| Color_Out_-_Falling_Star | en | 222 | 34.1 % | 0.149 | 96.0 % | 96.6 % | 78.1 % | manual | 0.0 % | 32.5 % | en | 52.2 |  |
| Confession_-_Quesabe | fr | 148 | 40.0 % | 0.030 | 100.0 % | 100.0 % | 59.8 % | manual | 0.0 % | 35.7 % | fr | 35.5 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 9.8 % | 0.069 | 96.9 % | 96.9 % | 89.6 % | manual | 0.0 % | 11.6 % | en | 58.8 |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | 64.2 % | 0.030 | 94.5 % | 96.4 % | 41.7 % | manual | 0.0 % | 60.8 % | fr | 48.8 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | 33.3 % | 0.032 | 94.3 % | 94.9 % | 73.1 % | manual | 0.0 % | 41.5 % | fr | 52.2 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | 2.7 % | 0.048 | 100.0 % | 100.0 % | 98.0 % | manual | 0.0 % | 11.5 % | de | 48.9 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | 7.2 % | 0.027 | 100.0 % | 100.0 % | 93.7 % | manual | 0.0 % | 12.9 % | de | 49.9 |  |
| Der_Musiker_-_d-music | de | 271 | 18.9 % | 0.020 | 99.7 % | 99.7 % | 83.9 % | manual | 0.0 % | 8.6 % | de | 64.5 |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | 40.0 % | 0.033 | 83.7 % | 84.7 % | 62.8 % | manual | 0.0 % | 26.4 % | de | 38.9 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | 24.2 % | 0.030 | 100.0 % | 100.0 % | 89.1 % | manual | 0.0 % | 18.9 % | es | 54.1 |  |
| Drei_Nüsse_-_patrouille | de | 259 | 4.6 % | 0.026 | 99.0 % | 99.2 % | 94.4 % | manual | 0.0 % | 7.5 % | de | 63.6 |  |
| En_liberté_-_tom.leyak | fr | 234 | 20.3 % | 0.033 | 100.0 % | 100.0 % | 85.0 % | manual | 0.0 % | 25.0 % | fr | 57.0 |  |
| Esencia_-_NandoMalo_ | es | 262 | 12.6 % | 0.023 | 99.3 % | 99.3 % | 91.0 % | manual | 0.0 % | 12.4 % | es | 62.8 |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | 39.7 % | 0.049 | 100.0 % | 100.0 % | 96.6 % | manual | 0.0 % | 14.0 % | en | 50.1 |  |
| Fantasma_-_Los_Rombos | es | 166 | 55.0 % | 0.036 | 96.8 % | 96.8 % | 71.6 % | manual | 0.0 % | 0.0 % | es | 37.5 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | 6.7 % | 0.030 | 100.0 % | 100.0 % | 92.6 % | manual | 0.0 % | 16.8 % | de | 58.5 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | 13.0 % | 0.022 | 100.0 % | 100.0 % | 87.7 % | manual | 0.1 % | 3.5 % | de | 57.3 |  |
| Guayeteo_-_JhoyKing | es | 158 | 35.0 % | 0.025 | 99.2 % | 100.0 % | 73.5 % | manual | 0.0 % | 27.2 % | es | 39.9 |  |
| HILA_-_Give_Me_the_Same | en | 234 | 28.2 % | 0.064 | 97.4 % | 97.4 % | 71.1 % | manual | 0.0 % | 25.7 % | en | 55.6 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 16.0 % | 0.030 | 97.8 % | 97.8 % | 84.0 % | manual | 0.0 % | 34.4 % | es | 49.1 |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | 15.2 % | 0.032 | 99.4 % | 99.4 % | 85.4 % | manual | 0.0 % | 11.8 % | de | 60.6 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | 22.3 % | 0.023 | 100.0 % | 100.0 % | 77.2 % | manual | 0.0 % | 14.6 % | es | 52.1 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | 29.3 % | 0.038 | 96.7 % | 100.0 % | 73.2 % | manual | 0.0 % | 52.5 % | de | 36.1 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | 17.0 % | 0.050 | 100.0 % | 100.0 % | 89.4 % | manual | 0.0 % | 10.8 % | en | 60.3 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 34.5 % | 0.018 | 90.7 % | 91.9 % | 63.4 % | manual | 0.0 % | 8.4 % | de | 63.2 |  |
| Kinematic_-_Peyote | en | 183 | 26.4 % | 0.056 | 96.6 % | 97.5 % | 80.3 % | manual | 0.0 % | 30.7 % | en | 42.2 |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | 16.7 % | 0.064 | 100.0 % | 100.0 % | 86.8 % | manual | 0.0 % | 14.2 % | en | 58.4 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | 8.9 % | 0.029 | 98.0 % | 98.0 % | 91.5 % | manual | 0.1 % | 11.5 % | es | 59.7 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 9.9 % | 0.022 | 99.6 % | 99.6 % | 95.3 % | manual | 0.0 % | 13.4 % | fr | 45.2 |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | 25.7 % | 0.035 | 100.0 % | 100.0 % | 76.2 % | manual | 0.0 % | 21.6 % | fr | 39.0 |  |
| Les_files_d'attente_-_Law' | fr | 196 | 41.5 % | 0.034 | 94.8 % | 96.0 % | 54.5 % | manual | 0.0 % | 28.6 % | fr | 46.9 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | 26.0 % | 0.028 | 100.0 % | 100.0 % | 78.1 % | manual | 0.0 % | 32.4 % | fr | 53.6 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | 10.2 % | 0.057 | 100.0 % | 100.0 % | 89.2 % | manual | 0.0 % | 18.9 % | en | 43.3 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | 35.3 % | 0.024 | 97.7 % | 98.6 % | 57.2 % | manual | 0.0 % | 47.6 % | fr | 39.4 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | 69.5 % | 0.088 | 76.8 % | 82.9 % | 30.1 % | manual | 0.0 % | 36.3 % | en | 50.0 |  |
| Musik_-_Heiko | de | 295 | 5.9 % | 0.025 | 100.0 % | 100.0 % | 94.9 % | manual | 0.1 % | 10.1 % | de | 70.3 |  |
| Mère_nature_-_Law' | fr | 225 | 15.4 % | 0.037 | 100.0 % | 100.0 % | 87.8 % | manual | 0.0 % | 19.8 % | fr | 54.3 |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | 20.5 % | 0.033 | 99.1 % | 99.1 % | 77.4 % | manual | 0.2 % | 22.0 % | fr | 49.5 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | 9.0 % | 0.029 | 100.0 % | 100.0 % | 91.5 % | manual | 0.0 % | 6.4 % | es | 51.9 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 15.7 % | 0.037 | 100.0 % | 100.0 % | 84.7 % | manual | 0.0 % | 41.0 % | fr | 49.4 |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | 33.1 % | 0.037 | 100.0 % | 100.0 % | 70.1 % | manual | 0.2 % | 22.8 % | fr | 47.9 |  |
| Pure_Mids_-_The_Leader | en | 262 | 96.6 % | 2.981 | 20.0 % | 20.0 % | 4.4 % | manual | 0.0 % | 42.9 % | en | 57.9 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | 17.9 % | 0.044 | 98.7 % | 98.7 % | 86.9 % | manual | 0.0 % | 20.2 % | en | 44.9 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | 3.9 % | 0.027 | 100.0 % | 100.0 % | 97.2 % | manual | 0.0 % | 12.9 % | es | 61.1 |  |
| Ridgway_-_Fire_Inside | en | 284 | 33.0 % | 0.050 | 93.8 % | 93.8 % | 53.0 % | manual | 0.1 % | 29.4 % | en | 65.4 |  |
| Rxbyn_-_Bad_Side | en | 217 | 17.7 % | 0.056 | 99.0 % | 99.2 % | 88.0 % | manual | 0.0 % | 24.8 % | en | 57.2 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | 16.9 % | 0.042 | 98.9 % | 100.0 % | 79.0 % | manual | 0.0 % | 33.1 % | de | 53.2 |  |
| Schnodderdodder_-_Abendblau | de | 197 | 14.4 % | 0.022 | 100.0 % | 100.0 % | 88.3 % | manual | 0.0 % | 14.1 % | de | 48.8 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 15.2 % | 0.032 | 100.0 % | 100.0 % | 86.1 % | manual | 0.1 % | 11.7 % | de | 54.3 |  |
| Sin_miedo_-_Living_Camboya | es | 223 | 16.3 % | 0.027 | 99.3 % | 99.3 % | 84.2 % | manual | 0.0 % | 14.0 % | es | 53.6 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | 13.5 % | 0.063 | 96.4 % | 98.6 % | 85.8 % | manual | 0.0 % | 29.5 % | en | 54.7 |  |
| Songwriterz_-_Back_In_Time | en | 209 | 25.9 % | 0.062 | 92.2 % | 92.2 % | 70.2 % | manual | 0.1 % | 32.7 % | en | 50.3 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | 23.9 % | 0.023 | 99.2 % | 99.6 % | 76.2 % | manual | 0.1 % | 23.3 % | fr | 39.4 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 8.7 % | 0.028 | 98.1 % | 98.4 % | 92.8 % | manual | 0.0 % | 15.7 % | es | 48.8 |  |
| The.madpix.project_-_One_Way_Street | en | 171 | 29.7 % | 0.063 | 97.0 % | 97.0 % | 73.8 % | manual | 0.1 % | 14.3 % | en | 39.7 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 61.4 % | 0.071 | 80.0 % | 81.2 % | 39.4 % | manual | 0.0 % | 27.0 % | en | 52.0 |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | 53.0 % | 0.042 | 97.9 % | 97.9 % | 57.8 % | manual | 0.0 % | 22.3 % | en | 58.2 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | 10.0 % | 0.030 | 100.0 % | 100.0 % | 90.0 % | manual | 0.0 % | 5.4 % | fr | 73.6 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | 10.1 % | 0.033 | 99.3 % | 99.3 % | 89.9 % | manual | 0.0 % | 11.1 % | es | 82.7 |  |
| Veränderung_-_doromusis | de | 194 | 14.2 % | 0.029 | 98.3 % | 98.3 % | 85.8 % | manual | 0.0 % | 17.2 % | de | 46.2 |  |
| Wordsmith_-_The_Statement | en | 171 | 29.5 % | 0.055 | 97.1 % | 97.1 % | 66.1 % | manual | 0.0 % | 29.1 % | en | 61.4 |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | 25.7 % | 0.027 | 97.6 % | 97.6 % | 78.7 % | manual | 0.0 % | 19.6 % | es | 42.7 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | 22.8 % | 0.029 | 99.1 % | 99.1 % | 80.5 % | manual | 0.0 % | 15.2 % | fr | 39.8 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | 6.6 % | 0.029 | 98.8 % | 100.0 % | 93.4 % | manual | 0.0 % | 10.2 % | de | 45.6 |  |
| l'abandon_-_flo | fr | 210 | 17.8 % | 0.030 | 96.4 % | 97.1 % | 80.4 % | manual | 0.0 % | 18.8 % | fr | 50.9 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | 6.5 % | 0.033 | 98.1 % | 98.7 % | 92.9 % | manual | 0.1 % | 8.2 % | es | 46.0 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | 9.0 % | 0.034 | 97.9 % | 98.4 % | 90.5 % | manual | 0.0 % | 14.3 % | es | 43.3 |  |

## Peores casos

Mayor mediana de error de inicio:
- Pure_Mids_-_The_Leader: 2.981 s
- Avercage_-_Embers: 1.037 s
- Color_Out_-_Falling_Star: 0.149 s
- Moon_I_Mean_-_Wrong_Concept: 0.088 s
- The_Rinn_-_Voices__2017_Version_: 0.071 s

Mayor WER:
- Pure_Mids_-_The_Leader: 96.6 %
- Avercage_-_Embers: 80.5 %
- Moon_I_Mean_-_Wrong_Concept: 69.5 %
- Culture_&_Co._-_cool.cavemen: 64.2 %
- The_Rinn_-_Voices__2017_Version_: 61.4 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
