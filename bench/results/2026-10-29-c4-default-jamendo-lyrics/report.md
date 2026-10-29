# Banco · c4-default · jamendo · con letra

- Fecha: 2026-10-29T20:06:14+01:00
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
| de | 20 | 0 | — | — | 0.029 | 0.047 | 99.4 % | 99.8 % | 0.071 | 0.026 | 95.9 % | — | 0 | 59 | 0.0 % | 18.8 % |
| en | 20 | 0 | — | — | 0.057 | 0.164 | 97.6 % | 97.9 % | 0.056 | 0.098 | 90.9 % | — | 0 | 60 | 0.1 % | 33.0 % |
| es | 20 | 0 | — | — | 0.028 | 0.095 | 99.5 % | 99.6 % | 0.090 | 0.061 | 95.8 % | — | 0 | 59 | 0.1 % | 18.8 % |
| fr | 19 | 0 | — | — | 0.030 | 0.059 | 98.8 % | 99.1 % | 0.079 | 0.005 | 86.8 % | — | 0 | 60 | 0.0 % | 29.9 % |
| total | 79 | 0 | — | — | 0.035 | 0.093 | 98.8 % | 99.1 % | 0.074 | 0.048 | 92.3 % | — | 0 | 60 | 0.1 % | 25.1 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.9 | 2867 | 2388 | 0.204 |
| aligner | 0.1 | 1559 | 3726 | 0.015 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | — | 0.024 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.2 % | — | 36.3 (caché) |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.044 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 32.5 % | — | 52.9 (caché) |  |
| Avercage_-_Embers | en | 243 | — | 0.143 | 87.0 % | 88.9 % | 85.7 % | manual | 0.0 % | 84.0 % | — | 54.9 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.019 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 29.8 % | — | 45.9 (caché) |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | — | 0.032 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 26.8 % | — | 56.7 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | 0.038 | 99.7 % | 99.7 % | 98.9 % | manual | 0.0 % | 23.5 % | — | 69.5 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | — | 0.039 | 100.0 % | 100.0 % | 86.7 % | manual | 0.0 % | 9.6 % | — | 56.7 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | 0.036 | 99.6 % | 99.6 % | 64.3 % | manual | 0.0 % | 47.2 % | — | 53.4 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | 0.037 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 14.1 % | — | 47.4 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.046 | 97.7 % | 98.9 % | 94.6 % | manual | 0.0 % | 20.4 % | — | 53.6 (caché) |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.025 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 7.7 % | — | 42.8 (caché) |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | — | 0.031 | 96.2 % | 96.2 % | 99.5 % | manual | 0.0 % | 25.0 % | — | 60.8 |  |
| Color_Out_-_Falling_Star | en | 222 | — | 0.154 | 95.3 % | 96.2 % | 94.2 % | manual | 0.0 % | 38.1 % | — | 48.6 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.029 | 99.7 % | 99.7 % | 86.9 % | manual | 0.2 % | 42.9 % | — | 32.2 (caché) |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.068 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 12.1 % | — | 52.7 (caché) |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | — | 0.034 | 95.2 % | 96.8 % | 93.9 % | manual | 0.0 % | 62.3 % | — | 46.7 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | — | 0.032 | 96.4 % | 96.9 % | 76.6 % | manual | 0.0 % | 45.1 % | — | 46.5 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | — | 0.048 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 11.5 % | — | 44.7 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | 0.028 | 100.0 % | 100.0 % | 97.7 % | manual | 0.0 % | 12.2 % | — | 45.7 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.021 | 99.4 % | 99.7 % | 98.0 % | manual | 0.0 % | 13.8 % | — | 60.0 (caché) |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | 0.029 | 96.6 % | 98.0 % | 94.9 % | manual | 0.0 % | 41.3 % | — | 36.1 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | — | 0.030 | 100.0 % | 100.0 % | 91.0 % | manual | 0.2 % | 23.3 % | — | 49.8 |  |
| Drei_Nüsse_-_patrouille | de | 259 | — | 0.026 | 99.8 % | 100.0 % | 98.5 % | manual | 0.0 % | 7.5 % | — | 57.0 |  |
| En_liberté_-_tom.leyak | fr | 234 | — | 0.033 | 100.0 % | 100.0 % | 94.0 % | manual | 0.0 % | 29.4 % | — | 50.9 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 19.5 % | — | 57.5 (caché) |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | 0.049 | 100.0 % | 100.0 % | 99.6 % | manual | 0.4 % | 25.8 % | — | 42.5 |  |
| Fantasma_-_Los_Rombos | es | 166 | — | 0.037 | 97.2 % | 98.6 % | 81.8 % | manual | 0.4 % | 16.0 % | — | 35.9 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | — | 0.031 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 17.8 % | — | 54.9 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | 0.023 | 100.0 % | 100.0 % | 100.0 % | manual | 0.1 % | 2.6 % | — | 53.0 |  |
| Guayeteo_-_JhoyKing | es | 158 | — | 0.027 | 99.3 % | 99.7 % | 84.1 % | manual | 0.0 % | 27.9 % | — | 34.7 |  |
| HILA_-_Give_Me_the_Same | en | 234 | — | 0.061 | 98.0 % | 98.7 % | 92.2 % | manual | 0.0 % | 24.4 % | — | 51.3 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.027 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 34.9 % | — | 46.1 (caché) |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | — | 0.031 | 100.0 % | 100.0 % | 95.5 % | manual | 0.0 % | 12.6 % | — | 55.9 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | — | 0.023 | 100.0 % | 100.0 % | 80.4 % | manual | 0.0 % | 14.4 % | — | 48.5 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | — | 0.039 | 93.9 % | 97.6 % | 100.0 % | manual | 0.0 % | 51.2 % | — | 34.2 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | — | 0.051 | 99.8 % | 99.8 % | 83.1 % | manual | 0.1 % | 11.1 % | — | 43.2 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.016 | 99.8 % | 99.8 % | 95.8 % | manual | 0.0 % | 8.2 % | — | 51.0 (caché) |  |
| Kinematic_-_Peyote | en | 183 | — | 0.052 | 97.1 % | 97.8 % | 93.9 % | manual | 0.7 % | 28.7 % | — | 41.5 (caché) |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | 0.062 | 99.3 % | 99.3 % | 99.7 % | manual | 0.0 % | 13.2 % | — | 48.9 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | 0.028 | 100.0 % | 100.0 % | 100.0 % | manual | 0.1 % | 15.1 % | — | 41.1 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.022 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 14.3 % | — | 40.7 (caché) |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | — | 0.035 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 22.5 % | — | 35.8 |  |
| Les_files_d'attente_-_Law' | fr | 196 | — | 0.031 | 99.1 % | 99.5 % | 66.5 % | manual | 0.0 % | 29.8 % | — | 42.9 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | 0.029 | 99.7 % | 100.0 % | 98.5 % | manual | 0.0 % | 34.2 % | — | 48.1 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | — | 0.056 | 99.5 % | 99.5 % | 96.7 % | manual | 0.0 % | 16.5 % | — | 39.6 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | — | 0.024 | 96.9 % | 99.0 % | 75.3 % | manual | 0.0 % | 50.2 % | — | 34.5 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | — | 0.050 | 99.6 % | 99.6 % | 95.2 % | manual | 0.0 % | 54.9 % | — | 47.9 |  |
| Musik_-_Heiko | de | 295 | — | 0.026 | 100.0 % | 100.0 % | 94.1 % | manual | 0.1 % | 10.5 % | — | 64.5 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 18.3 % | — | 49.5 (caché) |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | — | 0.032 | 99.2 % | 99.2 % | 90.4 % | manual | 0.2 % | 19.3 % | — | 45.4 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | — | 0.030 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 8.5 % | — | 47.1 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.036 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 38.1 % | — | 44.5 (caché) |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | 0.045 | 89.6 % | 90.4 % | 93.3 % | manual | 0.2 % | 38.8 % | — | 44.4 |  |
| Pure_Mids_-_The_Leader | en | 262 | — | 0.071 | 96.3 % | 96.3 % | 71.9 % | manual | 0.8 % | 72.5 % | — | 57.1 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | — | 0.044 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 20.7 % | — | 41.7 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | — | 0.027 | 100.0 % | 100.0 % | 99.8 % | manual | 0.0 % | 13.1 % | — | 53.3 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.049 | 92.7 % | 92.7 % | 77.0 % | manual | 0.0 % | 30.9 % | — | 61.4 (caché) |  |
| Rxbyn_-_Bad_Side | en | 217 | — | 0.057 | 98.8 % | 99.0 % | 95.5 % | manual | 0.0 % | 24.4 % | — | 48.2 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | — | 0.042 | 98.6 % | 99.5 % | 92.6 % | manual | 0.0 % | 35.5 % | — | 46.5 |  |
| Schnodderdodder_-_Abendblau | de | 197 | — | 0.022 | 99.3 % | 100.0 % | 95.9 % | manual | 0.0 % | 16.4 % | — | 43.6 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.031 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 15.2 % | — | 51.0 (caché) |  |
| Sin_miedo_-_Living_Camboya | es | 223 | — | 0.026 | 100.0 % | 100.0 % | 98.8 % | manual | 0.0 % | 13.6 % | — | 49.0 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | — | 0.064 | 98.8 % | 100.0 % | 98.8 % | manual | 0.0 % | 26.4 % | — | 50.3 |  |
| Songwriterz_-_Back_In_Time | en | 209 | — | 0.055 | 97.3 % | 97.3 % | 92.0 % | manual | 0.0 % | 35.3 % | — | 45.8 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | — | 0.023 | 97.4 % | 97.4 % | 88.1 % | manual | 0.1 % | 25.4 % | — | 34.6 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.029 | 98.2 % | 98.4 % | 94.8 % | manual | 0.0 % | 16.3 % | — | 42.7 (caché) |  |
| The.madpix.project_-_One_Way_Street | en | 171 | — | 0.059 | 98.9 % | 98.9 % | 95.1 % | manual | 0.0 % | 25.7 % | — | 37.2 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.052 | 98.9 % | 100.0 % | 93.6 % | manual | 0.0 % | 46.1 % | — | 49.8 (caché) |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | — | 0.044 | 90.2 % | 90.4 % | 79.7 % | manual | 0.1 % | 38.6 % | — | 54.1 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | — | 0.030 | 100.0 % | 100.0 % | 96.1 % | manual | 0.0 % | 4.9 % | — | 67.2 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | — | 0.034 | 100.0 % | 100.0 % | 96.6 % | manual | 0.8 % | 10.5 % | — | 74.3 |  |
| Veränderung_-_doromusis | de | 194 | — | 0.030 | 99.5 % | 99.5 % | 90.5 % | manual | 0.0 % | 22.6 % | — | 42.3 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.054 | 100.0 % | 100.0 % | 89.8 % | manual | 0.0 % | 30.8 % | — | 37.2 (caché) |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | — | 0.027 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 19.7 % | — | 37.3 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | 0.030 | 99.6 % | 100.0 % | 97.0 % | manual | 0.0 % | 17.5 % | — | 35.6 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | 0.029 | 98.9 % | 100.0 % | 97.8 % | manual | 0.0 % | 11.0 % | — | 42.2 |  |
| l'abandon_-_flo | fr | 210 | — | 0.030 | 99.7 % | 100.0 % | 86.2 % | manual | 0.0 % | 19.9 % | — | 46.1 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | — | 0.032 | 99.4 % | 100.0 % | 99.4 % | manual | 0.1 % | 10.1 % | — | 42.1 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | 0.034 | 98.5 % | 99.0 % | 98.1 % | manual | 0.0 % | 14.8 % | — | 39.3 |  |

## Peores casos

Mayor mediana de error de inicio:
- Color_Out_-_Falling_Star: 0.154 s
- Avercage_-_Embers: 0.143 s
- Pure_Mids_-_The_Leader: 0.071 s
- Cortez_-_Feel__Stripped_: 0.068 s
- Slingshot_Miracle_-_Whistler: 0.064 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
